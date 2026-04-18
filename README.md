# KabuSys

日本株向けの自動売買システム（ライブラリ + 実行スクリプト群）

このリポジトリは、戦略リサーチ／ポートフォリオ構築／発注実行／監視・アラート・キルスイッチ等を含む自動売買基盤（KabuSys）の実装です。  
コードは主に純粋関数（研究・配分・サイズ計算）と実行用コンポーネント（ExecutionEngine、Monitoring）で構成されています。

---

## 主な特徴（機能一覧）

- 環境設定ウィザード（.env 生成 / 更新）
- 起動前設定検証ツール（環境変数・設定ファイルのチェック）
- ExecutionEngine 起動スクリプト
  - 本番 / ペーパートレードの分離（paper_trading モードは MockBroker を使用し、専用 DB に書き込む）
  - 停止フラグ（stop_requested.flag）検知による安全停止
  - プロセス優先度設定
- Monitoring（System / Trade / Risk）コンポーネント
  - システムメトリクス（CPU / メモリ / ディスク）とデータ鮮度の監視
  - リスク監視（ドローダウン、ポジション上限など）
  - KillSwitch による停止フラグ（data/kill.flag）書き込み
  - 監視ループ実行スクリプト（run_monitoring）
- Paper Trading 検証レポート生成ツール
- 研究用モジュール（ファクター計算、特徴探索、将来リターン / IC 計算）
- ニュースの NLP スコアリング（OpenAI を利用した銘柄別センチメントスコア）
- DuckDB / SQLite を使ったデータ参照・永続化（prices_daily, raw_financials, raw_news, ai_scores など）
- 統一的なログ設定（stdout + 日次ローテーションファイル）

---

## セットアップ手順（開発 / 実行前準備）

1. Python 環境
   - Python 3.9+ を推奨
   - 仮想環境を作成してアクティブ化してください（例: venv / poetry / conda）

2. 依存関係をインストール
   - 必須パッケージ（例）
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config ファイル検証用）
   - 例（pip）
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - または手動で .env を作成（ルートに配置）
     - .env.example を参考に必須値を設定してください

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

5. DB の準備
   - DuckDB と SQLite のファイルはデフォルトで `data/` 以下に作成されます
   - 必要に応じて環境変数でパスを変更してください（下記参照）

---

## 主要な環境変数（要 / 推奨 / デフォルト）

必須（少なくともこれらは設定してください）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要なオプション（デフォルトは括弧内）
- KABUSYS_ENV — 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - paper_trading: MockBroker を使用し、本番 DB と分離して data/paper_trading.db に記録
  - live: 本番
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（news NLP / regime_detector が利用）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant / partial / never / reject、デフォルト: instant）

監視 / 実行制御
- MONITOR_POLL_INTERVAL — Monitoring スクリプトのポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 本番で Kill Flag を自動クリアするか（0/1、デフォルト: 0）
- PID_FILE_PATH / KILL_FLAG_PATH — デフォルトは data/execution.pid / data/kill.flag

---

## 使い方（起動例・CLI）

- 環境設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳格モード（警告を FAIL とする）:
    - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在する場合は起動しない
    - 実行中は data/stop_requested.flag の存在を監視し、存在したらエンジンを停止

- 監視ループ（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用してログを残します（環境に依らず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

- ライブラリとしての利用（例）
  - 研究モジュール:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - ポートフォリオ構築:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - AI スコアリング（プログラム内呼び出し）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

---

## 停止・キルフラグの取り扱い

- 外部からの停止要求
  - run_execution / run_monitoring はプロジェクトルート下の data/stop_requested.flag を監視します。このファイルを作成すると起動中のプロセスが検出して終了します（run_execution は起動前にも存在チェック）。
  - path: <project_root>/data/stop_requested.flag

- KillSwitch（自動停止トリガ）
  - 監視コンポーネントは条件を評価して data/kill.flag を書き込みます（KillSwitch）。これにより ExecutionEngine の停止を誘導します。
  - path: <project_root>/data/kill.flag
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（起動時自動クリアは危険）

- PID 管理
  - ExecutionEngine は data/execution.pid を PID ファイルとして使用します（設定による変更可）

---

## ロギング

- logging 設定ユーティリティを共通で使用:
  - stdout（StreamHandler） と 日次ローテーションファイル（logs/<app_name>.log）を設定
  - ログディレクトリ: デフォルト `logs/`（環境変数 LOG_DIR で変更可能）
  - ローテーション保持日数: 30 日

---

## ディレクトリ構成（主要ファイル）

ルート: src/kabusys 以下を想定。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py     — レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py      — システム / データ鮮度監視
    - trade_monitor.py       — 発注・約定監視（ログ整合性等）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — （アラート送信ロジック: LINE など）
  - execution/
    - execution_engine.py    — ExecutionEngine（スレッド起動、セッション管理）
    - broker_factory.py      — ブローカークライアントの生成（本番 / mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・丸め・スケーリング
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — IC / forward returns / 統計サマリー
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - data/ (実行時に利用するファイルがここに置かれる)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - config/ (YAML 設定ファイルを格納する想定)
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml

---

## 注意事項 / 運用上のヒント

- paper_trading モードは本番データベースと完全分離されます。安全に検証できます。
- .env ファイルは機密情報を含むため、絶対にリポジトリにコミットしないでください。
- OpenAI を利用する機能（news_nlp, regime_detector）は API キーが必要です。API 呼び出しはネットワーク障害やレート制限を考慮してリトライ処理が組み込まれていますが、コストとレイテンシを考慮して運用してください。
- 本番運用時は KABUSYS_ENV=live を設定し、KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- ログ・DB のファイルパスは環境変数で上書き可能です。運用環境に合わせて配置してください。
- サードパーティライブラリのバージョン互換に注意してください（duckdb, openai SDK, psutil 等）。

---

README はここまでです。具体的な利用方法や API の詳細（各関数の引数・返り値）はソースの docstring を参照してください。追加で「インストール用 requirements.txt の例」や「デプロイ手順（systemd / Supervisor / Docker）」などが必要であれば教えてください。
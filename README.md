# KabuSys

日本株自動売買プラットフォームのライブラリ / 起動スクリプト群です。  
本リポジトリは取引実行ロジック、監視、ポートフォリオ構築、研究用ファクター計算、AIを使ったニュース/レジーム判定などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したコンポーネント群です。主な責務は次のとおりです。

- ExecutionEngine（発注 / 注文管理 / リスク制御）
- Monitoring（システム稼働・データ鮮度・注文ログの監視、Kill Switch）
- Portfolio construction（候補選定、重み計算、ポジションサイズ計算、セクター制約）
- Research（ファクター計算、将来リターン・IC計算、特徴量解析）
- AI モジュール（ニュースのNLUによる銘柄スコアリング、マクロニュースによる市場レジーム判定）
- 各種ユーティリティ（設定読み込み、ログ設定、プロセス優先度操作 等）
- ツール類（ペーパートレードの検証レポート生成 等）

設計方針として、ルックアヘッドバイアス回避（date.today() を直接参照しない設計）、DB分離（ペーパートレード用 DB を分離）、フェイルセーフ（API失敗時に安全なフォールバック）等を重視しています。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み / config ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）
- 起動スクリプト
  - 監視ループ起動: `kabusys.run_monitoring`
    - MONITOR_POLL_INTERVAL 環境変数で polling 間隔上書き可（デフォルト 60 秒）
    - 監視は常に本番用 sqlite_path を使用
  - 実行エンジン起動: `kabusys.run_execution`
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録
- 監視
  - system_monitor: CPU/メモリ/ディスク/プロセス生存確認、データ鮮度チェック
  - trade_monitor: 発注ログ・滞留注文・約定異常チェック（コード内に実装有）
  - risk_monitor: ドローダウン監視、ポジション数上限監視（kill flag 書込みトリガー）
  - kill_switch: 条件を満たすと `data/kill.flag` を書き込み ExecutionEngine を停止
- ポートフォリオ構築
  - 候補選定（スコア降順）、等重配分 / スコア加重、セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、リスクベース、利用可能現金に対するスケーリング）
- 研究（research）
  - momentum / volatility / value ファクター計算（DuckDB を使用）
  - 将来リターン、IC（Spearman rank）、統計サマリー
- AI
  - news_nlp: OpenAI チャットモデルを用いたニュースセンチメントスコアリング（ai_scores テーブルへ書込）
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して Pass/Fail レポートを出力

---

## セットアップ手順（開発環境想定）

※ 実行する環境に合わせて Python 仮想環境を作成してください。

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd repo

2. Python 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 下記は主な依存想定（requirements.txt がない場合の例）
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で有ると便利）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. 環境変数設定（.env の準備）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（プロジェクトルート）
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - AI 機能を使う場合: OPENAI_API_KEY（モジュールは環境変数から読み込み）
     - 主要なキー一覧（例）
       - KABUSYS_ENV=development|paper_trading|live
       - JQUANTS_REFRESH_TOKEN=...
       - KABU_API_PASSWORD=...
       - KABU_API_BASE_URL=http://localhost:18080/kabusapi
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
       - LOG_LEVEL=INFO
       - KILL_FLAG_CLEAR_ON_START=0
   - `.env` 自動読み込みはデフォルトで有効。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. 設定検証（必須変数・パス等のチェック）
   - python -m kabusys.validate_config
   - 重大なエラーがあれば exit(1)。--strict を付けると警告も fail 扱いになります。

6. DB 初期化
   - 監視用 SQLite は起動時にテーブルが自動作成されます（monitoring_db.init_monitoring_db）。
   - DuckDB などの分析 DB は必要テーブル（prices_daily 等）を準備してください（データ供給パイプラインが別途必要）。

---

## 実行方法（使い方）

- 実行前準備
  - 必要な環境変数（上記）を設定
  - `.env` を用意している場合は `python -m kabusys.config_setup` の後 `python -m kabusys.validate_config` を実行して確認

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 説明:
    - プロセス優先度を "high" に設定（可能な場合）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（例: MONITOR_POLL_INTERVAL=30）
    - 監視ループはプロジェクトの data/stop_requested.flag を検知すると終了します
    - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用する点に注意

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper 用 DB（Settings.paper_sqlite_path、デフォルト data/paper_trading.db）が用いられる
    - 実行中は `data/execution.pid` に PID を書き込む等の管理を行う
    - 起動時に data/stop_requested.flag が既に存在すれば起動しません
    - 停止は data/stop_requested.flag を作るか kill.flag を作成（KillSwitch により）して行います

- Kill Switch / 停止フラグ
  - 監視コンポーネントが条件を満たすと `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送れます
  - 手動で停止する場合はプロジェクトの `data/stop_requested.flag` を作成することで監視・実行スクリプトが検知して終了します

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）
  - 出力: 稼働率、注文成功率、送信率、P95 レイテンシ等の指標と PASS/FAIL 判定

- AI 関連（ニュース NLU / レジーム判定）
  - 環境変数 OPENAI_API_KEY を設定してください
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を受け取り処理します
  - API の呼び出し時にレートリミットや5xxに対するバックオフ・リトライロジックが組み込まれています

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行設定
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL
  - KILL_FLAG_CLEAR_ON_START — 起動時に Kill Flag を自動クリアするか（0/1）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
  - PID_FILE_PATH / KILL_FLAG_PATH — デフォルトは data 内に保存
- AI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使用する場合に必要）
- Paper trading 挙動
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト instant）

---

## ログ

- ログ出力は `kabusys.utils.logging_setup.setup_logging` で統一されています
- デフォルトは stdout と `logs/<app_name>.log`（日次ローテーション、30日保持）
- ログディレクトリは環境変数 `LOG_DIR` またはデフォルト `logs/`
- ログレベルは CLI / 環境変数 `LOG_LEVEL` / デフォルト INFO の順に解決されます

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読込 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - trade_monitor.py       — 注文ログ・滞留注文チェック（実装あり）
    - kill_switch.py         — Kill Switch 実装（kill.flag 書き込み等）
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - alert_manager.py       — （アラート送信管理 — 実装参照）
  - execution/               — ExecutionEngine / order_manager / risk_manager 等（実装参照）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算・スケーリング
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py            — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + LLM センチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

プロジェクトルートには `config/` ディレクトリ（system_config.yaml 等）を想定しています。`validate_config` はこれらのファイル存在や YAML パースをチェックします（PyYAML が利用可能な場合）。

---

## 注意事項 / 運用上のポイント

- KABUSYS_ENV によって動作モードが変わります。`live` は実際に発注が行われるため取り扱いに注意してください（validate_config は live 時に警告を出します）。
- 監視は `settings.sqlite_path` を常に使用します（run_monitoring は環境にかかわらず本番 sqlite_path を見ます）。
- run_execution は `paper_trading` モードでは Paper 専用 DB を使用して本番 DB と完全分離します。
- Kill Switch（`data/kill.flag`）は重大なリスクが検出された場合に Execution を停止するために使用されます。運用ルールを明確にしてください。
- AI 機能は OpenAI API を使用します。API キー管理、コスト、レート制限（429）の取り扱いに注意してください。
- DuckDB / prices_daily / raw_financials 等のデータ準備は別途データパイプラインが必要です（このリポジトリ内にパイプライン全体の実装がある場合はそちらを参照）。

---

## 付録：よく使うコマンド例

- .env 対話式作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコアリング（ライブラリ呼び出し例）:
  - Python から呼ぶ: from kabusys.ai import score_news; score_news(conn, date(2026,4,1), api_key="...")

---

問題点の報告・改善提案や、追加のドキュメント（各モジュールの API 仕様や DB スキーマ、運用手順）を作成することも推奨します。必要であれば各モジュールの詳細なドキュメント（関数引数・戻り値、例外動作等）を別途作成します。
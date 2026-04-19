# KabuSys

日本株向けの自動売買システム（ライブラリ兼ランタイムスクリプト群）。  
本リポジトリは取引実行エンジン・監視・ポートフォリオ構築・リサーチ・AI（ニュースセンチメント／レジーム判定）などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を提供します。

- 発注・約定・リスク管理を行う ExecutionEngine（本番 / ペーパートレード切替対応）
- システム稼働・データ鮮度・注文状況を監視する Monitoring (kill switch を含む)
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング、セクター制約）
- リサーチ用ファクター計算・特徴量探索（DuckDB を利用）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（ニュース NLP・レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード / 検証など）
- ペーパートレード結果検証レポート生成ツール

設計方針の一例:
- 本番 DB とペーパートレード DB は分離（ペーパートレード時は data/paper_trading.db を使用）
- DuckDB を分析用途のローカル DB として採用
- LLM 呼び出しは失敗時にフォールバックし、フェイルセーフ設計
- .env を用いた設定管理（自動ロード機能あり）

---

## 主な機能一覧

- 実行（Execution）
  - Broker クライアント抽象化（本番 / Mock）
  - OrderManager / RiskManager / Reconciler による発注フロー
  - PID ファイル・停止フラグによるプロセス制御

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/Disk・データ鮮度・プロセス存在を監視
  - TradeMonitor: 注文の滞留・約定異常などの検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限の監視とアラート記録
  - KillSwitch: 条件を満たすと data/kill.flag を書き込み Execution を停止
  - MonitoringEngine: 各 monitor のポーリング統合と通知連携

- ポートフォリオ構築
  - 候補選定（スコアによるソート）
  - 等比率 / スコア重み付け
  - セクターキャップの適用
  - リスクベースの株数決定・単元株丸め・aggregate cap のスケーリング

- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリー

- AI（OpenAI 経由）
  - ニュース記事のセンチメントスコアリング（ai_scores テーブルへ書込み）
  - マクロニュース + ETF MA による市場レジーム判定（market_regime テーブルへ書込）
  - バッチ処理、リトライ、レスポンス検証を実装

- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ログ設定ユーティリティ（Stream と 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

- ツール
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）

---

## 前提（依存）

最低限必要なパッケージ（代表例）:
- Python 3.8+（コードの型ヒントや f-string を利用しています）
- duckdb
- psutil
- openai (OpenAI SDK)
- PyYAML（config ファイル検証を行う場合）
- （sqlite3 は標準ライブラリ）

※ 実際の requirements.txt はプロジェクトに応じて用意してください。上記は主要な外部依存です。

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai pyyaml

   （実運用向けには各パッケージのバージョン固定を推奨）

4. 環境変数設定
   - プロジェクトルートに .env を作成するか、環境変数を直接設定します。
   - 対話形式で .env を作成するには:
     - python -m kabusys.config_setup
   - 作成後は設定検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

5. データディレクトリ・ログディレクトリ
   - デフォルトでは data/ と logs/ を使用します。必要であれば .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR を上書きしてください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（paper_trading 時に使用）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- PAPER_FILL_MODE — ペーパートレードでの約定挙動（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — 本番で誤って Kill Flag をクリアしないよう注意（0 推奨）
- MONITOR_POLL_INTERVAL — SystemMonitor のポーリング間隔（秒、デフォルト 60）

.env の自動読み込み:
- プロジェクトルートを .git または pyproject.toml から検出し、自動で .env/.env.local を読み込みます。
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（実行方法）

各種エントリポイントはモジュール経由で起動できます。

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution Engine（実行エンジン）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存します（paper_trading の場合は MockBrokerClient を使用してペーパートレード DB を利用）

- Monitoring（SystemMonitor の単独ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定可能（デフォルト 60）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- プログラムから API を呼ぶ（例）
  - DuckDB 接続を開いてリサーチ / AI 関数を呼び出す:
    - from kabusys.research import calc_momentum
    - conn = duckdb.connect("data/kabusys.duckdb")
    - res = calc_momentum(conn, target_date)

- AI 系機能（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  # api_key が None の場合 OPENAI_API_KEY 環境変数を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- run_execution は PID ファイル / stop flag を用いた停止制御を行います（data/execution.pid, data/stop_requested.flag 等）。
- run_monitoring は停止フラグ data/stop_requested.flag を検知したらループを終了します。

---

## よく使うファイル・フラグ

- data/kill.flag — Kill Switch が発動した旨を記したフラグ。ExecutionEngine はこれを検知して停止します。
- data/stop_requested.flag — 手動停止指示用フラグ（run_* スクリプトが監視）
- data/execution.pid — ExecutionEngine の PID ファイル
- logs/<app_name>.log — 日次ローテートされるログファイル

---

## ディレクトリ構成

（src 配下をルートに置く構成を想定）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / .env 自動読み込みロジック
  - config_setup.py        — 対話式 .env ウィザード
  - validate_config.py     — 起動前設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - utils/
    - logging_setup.py     — ログ設定ユーティリティ
    - process_priority.py  — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py     — SQLite スキーマ / DB 操作
    - system_monitor.py    — システム監視
    - trade_monitor.py     — 注文監視（実装ファイルあり）
    - risk_monitor.py      — ドローダウン / ポジション監視
    - kill_switch.py       — Kill Switch
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py     — アラート送信（実装ファイルあり）
  - execution/
    - execution_engine.py  — ExecutionEngine 本体（実装ファイルあり）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py          — ニュースセンチメント
    - regime_detector.py   — 市場レジーム判定
    - __init__.py

- config/                  — YAML 設定テンプレート（system_config.yaml 等）
- data/                    — SQLite / flag / pid 等のデータファイル置き場（実行時に作成）
- logs/                    — ログ出力ディレクトリ（デフォルト）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを強く推奨します（自動クリアは危険）。
- OpenAI API キーなどのシークレットは .env を Git にコミットしないでください。
- ペーパートレード用 DB は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。
- run_execution は停止フラグ / PID ファイルに依存するため、手動でのファイル操作には注意してください。
- monitoring はデフォルトで本番 sqlite_path を使用します（監視ログは環境にかかわらず同じ DB に書きます）。

---

## 参考コマンドまとめ

- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

必要であれば、README に含める「requirements.txt の推奨内容」「systemd / supervisor 用のサービス定義例」「運用フロー（起動手順・障害時対応）」などを追記できます。どの情報を優先して追加しますか？
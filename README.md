# KabuSys

日本株向け自動売買システムのリポジトリ（読み取り専用のドキュメント）。  
この README はコードベースから抽出した主要な機能・セットアップ方法・使い方を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネントを備えたモジュール群です。主な目的は以下です。

- マーケットデータを使ったファクター計算・リサーチ
- ポートフォリオ構築（シグナル → 銘柄選定 → 重み付け → 株数決定）
- 発注実行エンジン（本番 / ペーパートレード対応）
- 監視（システム状態・注文・リスク監視）と Kill Switch
- ニュース NLP によるセンチメントスコアリング / レジーム判定（OpenAI を利用）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証、検証レポート出力）

設計上の注意点：
- 研究モジュール（research）は本番 API を呼ばないよう作られている（DuckDB による解析のみ）。
- `paper_trading` モードでは MockBroker を使い、発注ログは専用 SQLite（data/paper_trading.db）へ保存して本番 DB と完全分離される。
- 実行スクリプトはプロセス優先度を高く設定し、ロギング／PID管理／停止フラグに対応している。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を読み込み）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行エンジン
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）と pid ファイル管理

- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine
  - 独立起動スクリプト: python -m kabusys.run_monitoring
  - 監視ログの永続化（SQLite、初期化用関数あり）

- ポートフォリオ構築（純粋関数）
  - 銘柄選定 / スコア重み付け / 等分配（portfolio.portfolio_builder）
  - セクター制限・レジーム乗数（portfolio.risk_adjustment）
  - 株数決定・単元丸め・投下資金スケーリング（portfolio.position_sizing）

- リサーチ
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン / IC 計算 / 統計サマリー（feature_exploration）

- AI（OpenAI）
  - ニュース記事を LLM でスコアリング（kabusys.ai.news_nlp.score_news）
  - マクロニュース + ETF MA 乖離から市場レジーム判定（kabusys.ai.regime_detector.score_regime）
  - API 呼び出しは冗長系（リトライ / バックオフ）とレスポンス検証を実装

- ツール
  - Paper Trading 検証レポート生成スクリプト:
    python -m kabusys.tools.paper_verification_report

- ユーティリティ
  - 統一ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要条件 / 推奨環境

- Python 3.10 以上（typing の union 型 | を使用）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 構文検証を行う場合）
- 仮想環境を作成して依存をインストールすることを推奨します。

例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml

（requirements.txt はリポジトリに含まれていないため、必要なパッケージを手動でインストールしてください）

---

## セットアップ手順（基本）

1. リポジトリをクローンしてワークディレクトリへ移動

2. .env を作成
   - 対話式で初期作成する:
     python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を置く。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（例とデフォルト）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパー時の DB デフォルト: data/paper_trading.db
     - OPENAI_API_KEY — AI 機能を使う場合に必須
     - LOG_LEVEL — デフォルト: INFO
     - PAPER_FILL_MODE — (instant|partial|never|reject)（ペーパートレードの成行応答動作）
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

3. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     python -m kabusys.validate_config --strict

4. DB/ログディレクトリの確認
   - デフォルトで SQLite / DuckDB は `data/` 配下、ログは `logs/` 配下に出力されます。必要に応じて環境変数でパスを変更してください。

5. 必要ライブラリ（OpenAI など）のインストール

---

## 使い方（実行例）

- 監視ループを起動（常駐的に実行）
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可（デフォルト 60）
  - python -m kabusys.run_monitoring

  例:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  備考:
  - 監視は常に本番 sqlite_path を使うように設計されています（KABUSYS_ENV に依らず）。
  - 停止は `data/stop_requested.flag` を作成すると検知して終了します。

- Execution エンジンを起動（発注エンジン）
  - python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db`（または PAPER_TRADING_SQLITE_PATH）へ記録します。これにより本番 DB と完全分離されます。
  - 起動時に `data/stop_requested.flag` があると起動を中止します。
  - 実行中に stop flag を作成すると Engine に停止指示が送られます。
  - PID ファイルはデフォルトで `data/execution.pid` に書かれます（Settings.pid_file_path で変更可）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit 1

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD
    --to   YYYY-MM-DD
    --db PATH（--db > PAPER_TRADING_SQLITE_PATH > デフォルト）

- AI 機能（プログラムから呼び出す例）
  - DuckDB 接続を渡して呼び出します（OpenAI API キーが必要）:
    from openai import OpenAI
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

  - 同様に regime 判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,1), api_key="...")

  - 注意: API キーは environment 変数 `OPENAI_API_KEY` または関数引数で指定可能。API 呼び出しはリトライやレスポンス検証を行います。

---

## 重要なファイル / フラグ

- data/stop_requested.flag — 実行スクリプト（run_monitoring / run_execution）が存在する場合、作成で停止を検知
- data/kill.flag — Kill Switch（監視による強制停止）発動時に作成される。ExecutionEngine 起動時に自動消去する設定あり（KILL_FLAG_CLEAR_ON_START）。
- data/execution.pid — Execution エンジンの PID ファイル（Settings.pid_file_path）
- logs/<app>.log — 日次ローテーションで出力されるログファイル（デフォルト logs/）
- DB:
  - DuckDB: data/kabusys.duckdb（分析用）
  - Monitoring SQLite: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db（paper_trading モード時）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数/Settings 管理（.env 自動ロード）
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — Monitoring 起動スクリプト
- run_execution.py         — Execution 起動スクリプト

サブパッケージ（主要ファイル）
- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（MA + マクロ NLP）
- monitoring/
  - monitoring_db.py       — SQLite 永続層（テーブル作成・読み書き）
  - system_monitor.py
  - risk_monitor.py
  - trade_monitor.py       — （注文監視、コードベースにあり）
  - monitoring_engine.py
  - alert_manager.py       —（アラート送信管理、実装あり）
  - kill_switch.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py       — 統一ログ設定（stdout + 日次ローテーション）
  - process_priority.py    — プロセス優先度 / CPU affinity
- execution/
  - broker_factory.py      — BrokerClientFactory（Mock/実ブローカー分岐）
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

（上は主要ファイルの抜粋です。完全な一覧はリポジトリの src/kabusys 以下を参照してください）

---

## 設定例（最小 .env）

以下は最小限の .env の例（秘密情報は適切に設定すること）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

OPENAI_API_KEY=sk-...   # AI 機能を使う場合

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨（誤って Kill Switch をクリアしない）。
- .env は絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- データベース / ログディレクトリのバックアップと権限管理に注意してください。
- OpenAI を利用する機能は API レートやコストに注意して運用してください。API キーは安全に管理すること。
- run_execution/run_monitoring はプロダクションではプロセスマネージャ（systemd, supervisord, docker など）で起動・監視してください。
- 監視はデフォルトで monitoring DB に結果を残します。DB サイズ管理（古いログのローテーション等）を検討してください。

---

## 参照・次のステップ

- 設定ウィザードで .env を作成（python -m kabusys.config_setup）
- validate_config で設定チェック（python -m kabusys.validate_config）
- DuckDB / SQLite の初期データ投入や prices_daily / raw_news テーブルの準備は運用環境に応じて行ってください（外部データ取得パイプラインは別途用意する想定）
- AI 機能を利用する場合は OpenAI API キーと利用ポリシーの確認を行ってください

---

必要であれば、この README をベースに「運用ガイド」「デプロイ手順」「systemd ユニット例」「Dockerfile 例」などを追加で作成します。どのドキュメントが必要か教えてください。
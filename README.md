KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視ツール群をまとめた Python コードベースです。  
主に以下の役割を持つコンポーネントを含みます:

- ExecutionEngine: 発注ロジック・リスク管理・注文状態管理（本番 / ペーパーあり）
- Monitoring: システム状態・注文監視・Kill Switch 等の定期監視
- Research: ファクター計算・特徴量解析
- AI モジュール: ニュースを LLM（OpenAI）でスコアリングしてシグナルに活用
- ユーティリティ: 環境設定ウィザード、設定検証、ペーパートレード検証レポート

主な機能
--------
- ExecutionEngine の起動/停止制御（本番 / ペーパー切替対応）
- 監視ループ（CPU/メモリ/Disk/プロセス正常性、データ鮮度、注文滞留など）
- Kill Switch：閾値超過時に data/kill.flag を書き込んで Engine を停止
- Paper Trading 用に本番 DB と分離された SQLite に記録するモード
- DuckDB を使った時系列データ処理（ファクター計算 / 研究用）
- OpenAI を使ったニュース NLP スコアリング（AI センチメント）
- 簡易 CLI ツール: .env ウィザード、設定検証、paper trading 検証レポート生成
- ログの統一管理（コンソール + 日次ローテートファイル）

動作前提 / 必要パッケージ
-----------------------
- Python 3.10+（PEP 604 の型記法などを使用）
- 推奨パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML をパースする場合に必要）
- 標準ライブラリ: sqlite3, logging, threading など

（プロジェクトに requirements.txt がある場合はそれを使ってください）

セットアップ手順
----------------

1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. .env を作成（ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話形式で J-Quants トークン、kabu API パスワード、DBパス、環境（development / paper_trading / live）などを設定します。
   - 自動ロード:
     - .env および .env.local をプロジェクトルートから自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告も含めて厳密にチェックするには --strict を付けます:
     - python -m kabusys.validate_config --strict

5. 必要なディレクトリの作成
   - data/ （SQLite / PID / フラグファイル保存）
   - logs/ （ログ出力）
   ほとんどは起動時に自動作成されますが、権限等で失敗することがあるため事前作成を推奨します。

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI 利用時に必須（AI モジュール）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite パス（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH など（Settings 参照）

使い方（コマンド例）
-------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録されます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag があると起動せず終了します。
    - 停止は data/stop_requested.flag を作成するか、Kill Switch により data/kill.flag が作成されると Engine 停止処理が行われます。
    - 実行中はデフォルトでプロセス優先度を "high" に設定します（psutil の権限に依存）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒、デフォルト 60）。
  - Monitoring は常に本番 sqlite_path を使用（環境に依らず監視 DB を使用）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先して使用）

- AI モジュール（プログラムから呼び出す）
  - 例: news NLP スコアリング
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  ※ conn は duckdb connection
  - OpenAI API キーは OPENAI_API_KEY 環境変数または api_key 引数で指定します。
  - モデルは gpt-4o-mini を想定しており、レスポンスのリトライや整形ロジックが組み込まれています。

停止 / Kill Switch
-----------------
- 手動でプロセスを止める:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検出して終了します。
- システム監視から停止させる（自動）:
  - RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止を促します。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定している場合、起動時に kill.flag を自動でクリアする設定があります（本番では 0 を推奨）。

ログ
----
- デフォルト: logs/<app_name>.log に日次ローテートで出力（30日保持）
- コンソールは stdout に出力されます（cron/task からのログ一本化に配慮）
- LOG_DIR / LOG_LEVEL でカスタマイズ可能
- ログディレクトリ作成に失敗した場合はファイルハンドラを使わずコンソールのみで継続します（警告出力）

ディレクトリ構成（抜粋）
-----------------------
（プロジェクトルートの src/kabusys 配下を抜粋した例）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理、.env 自動ロード
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP スコアリングロジック
    - regime_detector.py      — 市場レジーム判定（MA + LLM 合成）
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite による監視ログ永続化
    - system_monitor.py       — システム / データ鮮度監視
    - trade_monitor.py        — 注文状態監視（※実装ファイルあり）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — LINE 等への通知管理（※実装ファイルあり）
  - execution/
    - execution_engine.py     — Execution エンジン本体（※実装ファイルあり）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
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
  - data/                      — データディレクトリ（通常 .gitignore）
    - monitoring.db (デフォルト SQLite)
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - stop_requested.flag
    - kill.flag
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — psutil を使った優先度 / affinity 設定

注意点 / 運用上の留意事項
-----------------------
- KABUSYS_ENV が live の場合は本番用の設定になり、LINE 通知などの設定漏れが危険です。validate_config で検証してください。
- .env は決して Git にコミットしないでください（README や .env.example を参照）。
- OpenAI を使う機能は API コストやレイテンシ、リトライポリシーを考慮して運用してください。API キーは安全に保管してください。
- DuckDB / SQLite ファイルは定期バックアップを推奨します。
- psutil によるプロセス優先度変更や CPU affinity の設定は環境（OS・権限）によって失敗することがあります。失敗時はログに警告が出ますが起動は継続されます。

トラブルシューティング
---------------------
- ログが出力されない / ログファイルが作成されない:
  - 権限や LOG_DIR のパスを確認してください。許可がない場合はコンソール出力のみになります。
- DB ファイルが見つからない:
  - 環境変数（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を確認。config_setup で指定できます。
- OpenAI API 関連で失敗が多い:
  - OPENAI_API_KEY の有効性、ネットワーク、レート制限を確認。モジュールは 429 / 一部ネットワークエラーに対して指数バックオフでリトライします。

さらに読む（ドキュメント）
-----------------------
- 各モジュールに docstring と注釈が多く書かれているため、詳細な実装仕様は該当ファイルを参照してください（例: portfolio/*.py、research/*.py、ai/*.py）。
- 設定の雛形や追加の設定生成スクリプトがある場合は project root の README や scripts ディレクトリを参照してください。

以上が主要な README 内容です。必要であれば、README に追記する具体的な環境変数一覧（すべて）やコマンドのサンプル、運用手順書（デプロイ / systemd / cron / docker）等も作成します。どの項目を詳しく追加しますか？
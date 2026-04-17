# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ（モジュール群）。  
本リポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要な依存パッケージ
- セットアップ手順
- 使い方（主要スクリプト / CLI）
- 環境変数 / .env の管理
- DB / ファイルパス（デフォルト）
- 停止フラグと Kill Switch の挙動
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買システムのコアロジック群を提供する Python パッケージです。
- 発注エンジン、発注管理、リスク管理、監視（システム・注文・リスク）、ポートフォリオ構築、リサーチ（ファクター計算、特徴量解析）、およびニュースを使った AI スコアリング（OpenAI）などを含みます。
- 実行環境は development / paper_trading / live を想定しており、paper_trading モードでは本番 DB と分離されたモックブローカーを使用します。

機能一覧
- ExecutionEngine 起動 / 発注処理（run_execution.py）
  - 環境により MockBroker（paper_trading）または本番ブローカーを選択
  - リスク管理（RiskManager）、注文管理（OrderManager）、Reconciler 組込
- 監視サービス（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を周期的に実行しログ保存・アラート評価
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能
- 設定ウィザード（config_setup.py）
  - 対話式で .env を生成 / 更新
- 設定検証ツール（validate_config.py）
  - .env / config/*.yaml 等を起動前にチェック
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率、注文成功率、レイテンシ等を算出してレポート出力
- ポートフォリオ構築（portfolio/*）
  - 候補選定、重み付け、セクター制限、ポジションサイズ計算など純粋関数群
- リサーチ（research/*）
  - DuckDB 上の prices_daily / raw_financials を用いたファクター計算・特徴量解析
- AI モジュール（ai/*）
  - news_nlp: OpenAI を使ったニュースセンチメントスコア計算、ai_scores への書込み
  - regime_detector: ETF（1321）MA とマクロニュースで市場レジーム判定
- ユーティリティ
  - process_priority でプロセス優先度・CPU affinity 設定
  - monitoring_db: SQLite 監視ログの永続化層
  - 各種 DB 初期化 / マイグレーション処理

必要な依存パッケージ（例）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- requests (AlertManager の LINE 通知)
- PyYAML（config の厳密検証を行う場合）
- sqlite3（標準ライブラリ）

pip 例:
pip install duckdb psutil openai requests pyyaml

セットアップ手順（ローカル）
1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）
   - pip install -r requirements.txt あるいは上記パッケージを個別にインストール
3. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - または .env.example を参考に手動作成
4. 設定の検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いにできます
5. 必要なディレクトリ（例: data/）が自動作成されますが、権限等を確認してください

使い方（主要スクリプト / CLI）
- 環境設定ウィザード
  - python -m kabusys.config_setup
    - .env の初期作成・更新を対話的に支援します

- 設定検証
  - python -m kabusys.validate_config
    - 起動前に必須環境変数や config/*.yaml の存在/パースチェックを行います
    - --strict を付けると警告があると exit(1) します

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
    - KABUSYS_ENV が paper_trading の場合はペーパートレード専用 DB（data/paper_trading.db）を使用し、MockBrokerClient を利用します
    - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可）
    - 起動前に data/stop_requested.flag が存在する場合は起動をスキップします
    - 停止は kill.flag の作成（KillSwitch）や data/stop_requested.flag の作成で行えます（下記参照）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
    - SystemMonitor / TradeMonitor / RiskMonitor を定期的に実行して monitoring 用 SQLite に記録します
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可（デフォルト 60 秒）
    - 監視は本番 sqlite_path を常に参照（KABUSYS_ENV に依存せず）
    - 監視ループを停止するにはプロジェクトルート/data/stop_requested.flag を作成

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）

- ライブラリ呼び出し（AI、リサーチ等）
  - AI ニューススコアリング:
    from openai import OpenAI  # or use environment OPENAI_API_KEY
    import duckdb
    from kabusys.ai import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date, api_key="sk-...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=...)

  - リサーチ関数（例）:
    from kabusys.research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    calc_momentum(conn, date(2026, 4, 1))

主な環境変数（最小セット）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY — AI 機能を使う場合に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知（任意）
- LOG_LEVEL — デフォルト INFO
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）

.env の自動読み込み
- Settings モジュールはプロジェクトルート (.git または pyproject.toml があるディレクトリ) の .env / .env.local を自動で読み込みます（既存 OS 環境変数は保護されます）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

DB / ファイルパス（デフォルト）
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- PID / フラグ:
  - data/execution.pid (ExecutionEngine の PID ファイル)
  - data/kill.flag    (Kill Switch: ExecutionEngine 停止シグナル)
  - data/stop_requested.flag (監視・エンジンの手動停止トリガ)

停止フラグ / Kill Switch の挙動
- Kill Switch:
  - RiskMonitor 等が深刻なリスク（ドローダウン、ポジション上限超過）を検出した場合、data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります。KillSwitch は冪等に動作します（存在する場合は再書き込みを行いません）。
  - Settings.kill_flag_clear_on_start が "1" の場合、ExecutionEngine の起動時に自動的に kill.flag をクリアする設定があります（本番では 0 推奨）。
- 手動停止:
  - 監視ループや ExecutionEngine を停止したい場合、プロジェクトルートの data/stop_requested.flag を作成すると run_monitoring および run_execution がループ検出して安全終了します。
- PID ステール検出:
  - SystemMonitor は PID ファイルを検証し、存在するがプロセスが無い場合は stale PID として削除しログ／リスクイベントを残します。

Directory（主要ファイルのみ）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/                — 発注エンジン関連（Engine, OrderManager, BrokerFactory など）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py

開発・運用の注意点
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup.py にも注意書きがあります）。
- paper_trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を使う機能は API コスト・レート制限に留意してください。モジュール内で基本的なリトライ・バックオフを実装していますが、運用時は鍵の管理・呼び出し頻度に注意が必要です。
- Process priority や CPU affinity は psutil の許可や OS に依存します。権限不足で警告が出ることがありますがフォールバックします。
- DuckDB / SQLite のバージョン差異により executemany の空リスト等で制約があるため、モジュール側で互換性対策が施されています。

サンプル・最小 .env（例）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

トラブルシューティング / デバッグ
- 設定検証ツールでまず必須環境変数やパスをチェックしてください。
- ログレベルを DEBUG に設定すると詳細ログが得られます（LOG_LEVEL 環境変数）。
- run_execution 起動後、data/execution.pid の内容を確認して該当 PID が存在するか psutil 等でチェックできます。
- run_monitoring は監視用 DB に system_status / trade_logs / risk_logs / positions / dashboard テーブルを作成します（init_monitoring_db）。

ライセンス / 貢献
- （この README にはソースライセンス情報を含めていません。実プロジェクトでは LICENSE ファイルを置いてください。）

以上が本コードベースの README です。追加で「各モジュールの詳細な API 仕様」や「設定のチューニング例」「運用手順（デプロイ・監視）」などが必要であれば、目的に合わせて追記いたします。
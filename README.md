KabuSys
======

日本株向け自動売買システムのライブラリ/ランタイム群（抜粋）。
このリポジトリはトレーディングエンジン（ExecutionEngine）、監視コンポーネント、リサーチ/ファクター計算、AI ニューススコアリングなどの主要機能を持ちます。本 README はコードベースに含まれる主要スクリプト・ユーティリティの使い方とセットアップ手順をまとめたものです。

要点
- .env（環境変数）による設定管理（対話式ウィザードあり）
- ExecutionEngine は環境により実口座 / ペーパートレードを切替可能
- Monitoring はプロセス監視・データ鮮度・リスク監視・Kill Switch まで包含
- DuckDB / SQLite を使用したデータ保存・分析・監視ログ
- OpenAI を使ったニュース NLP / レジーム判定機能（API キーが必要）

機能一覧
- Execution
  - 実注文（live）／モック（paper_trading）切替
  - リスク管理（利用率・最大ポジション等）
  - 発注・オーダー管理・照合（Reconciler）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン／ポジション上限監視
  - KillSwitch: 閾値超過で停止フラグ（data/kill.flag）を生成
  - MonitoringEngine: 各モニタを束ねるポーリングループ
- Research / Portfolio
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 特徴量探索（IC 計算、将来リターン）
  - ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- AI
  - ニュース NLP による銘柄別センチメントスコアの生成（OpenAI）
  - マクロニュースと ETF 指標を組み合わせた市場レジーム判定（OpenAI）
- ツール
  - Paper Trading 検証レポート生成スクリプト
- 設定管理
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- ロギング
  - 統一的なログ設定ユーティリティ（stdout + 日次ローテートファイル）

前提（推奨）
- Python 3.9+
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定 YAML 検証用、必須ではない）
- OS: Linux / macOS / Windows（process priority の一部機能は OS 依存）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン・移動
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 代表的なパッケージ:
     - pip install duckdb psutil openai PyYAML
   - 実運用では requirements.txt を用意している場合はそれを使ってください。

4. .env の初期作成（対話式）
   - python -m kabusys.config_setup
     - ウィザードで J-Quants トークンや kabuAPI パスワード、DB パス等を設定します。
   - 自動ロードについて:
     - パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします。
     - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 運用切替
  - KABUSYS_ENV: execution 環境（development / paper_trading / live） デフォルト: development
    - paper_trading: MockBrokerClient を使い paper_trading.db に記録（本番 DB と分離）
- データベース
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- ログ
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...） デフォルト: INFO
  - LOG_DIR: ログファイルディレクトリ（デフォルト: logs）
- 監視・停止制御
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時 kill.flag を自動クリアするか（0/1、デフォルト 0）
  - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）

起動・使い方（代表コマンド）
- 環境作成 / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録します。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
    - 停止は data/stop_requested.flag を作成するか、プロセスに SIGINT（Ctrl+C）を送ります。
    - PID ファイル: data/execution.pid（設定により変更可）
    - DB: settings.paper_sqlite_path（paper） / settings.sqlite_path（live/dev）

- Monitoring（常駐監視）を起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
    - 監視は常に本番の sqlite_path を使用（環境に依存しない設計）
    - 停止は data/stop_requested.flag を作成するか、Ctrl+C

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY の設定が必要（引数で上書き可能）

ファイルベースの制御 / フラグ
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が存在を検知するとループを終了します（外部からの停止指示用）。
- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine に停止シグナルを送る（監視側が作成）。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアされる（本番では 0 推奨）。

ロギング
- setup_logging(app_name="...") により stdout と logs/<app_name>.log（日次ローテート、30日分保存）に出力されます。
- LOG_DIR / LOG_LEVEL で挙動を変更可能。

注意点 / 運用上の留意点
- .env を Git にコミットしないこと（config_setup でも注意書きあり）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨。
- OpenAI ランタイムは API レートや課金に注意して運用すること。
- process priority, CPU affinity 設定は psutil を使っているため権限や OS に依存することがあります（失敗時は警告ログでスキップ）。

ディレクトリ構成（コードベースの主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings 辞書
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視ログ）
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py       — （コード抜粋には実装の一部がある想定）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信の抽象化想定）
  - execution/
    - execution_engine.py    — ExecutionEngine（起動・セッション管理）
    - broker_factory.py      — BrokerClientFactory（Mock / 実装切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - data/                    — 実行時に作成されることが多い（DB / flag / pid 等）
  - logs/                    — ログ出力先（デフォルト）

（注）上記はリポジトリ内の抜粋に基づく主要ファイルリストです。実際の完全なツリーはプロジェクトの全ファイルを参照してください。

トラブルシューティング
- PyYAML が未インストールの場合、validate_config の YAML 検証はスキップされます（警告）。
- OpenAI 関連は API キーが未設定だと例外を投げる関数があります。事前に OPENAI_API_KEY を設定してください。
- DuckDB / SQLite のパスの親ディレクトリが存在しない場合は自動作成されますが、権限エラー等が出る場合はログや標準エラーを確認してください。

貢献・拡張
- 新しいブローカーや戦略を追加する場合は execution.* および portfolio.* を拡張してください。
- monitoring/alert_manager は通知チャネル（LINE 等）を実装するための拡張ポイントです。
- 設定スキーマやデフォルト値は config.py / config/*.yaml で管理してください。

ライセンスやその他（省略）
- 本 README はコードのスニペットに基づく概要説明です。実運用では必ずソースコードとプロジェクトのドキュメント、運用手順書を参照してください。

以上。必要であれば README の英語版や各モジュールの詳細ドキュメント（API リファレンス、構成ファイルの説明、運用手順）も作成します。どのセクションを優先しますか？
KabuSys
=======

日本株向け自動売買システムのコアライブラリ群および起動スクリプト群です。  
このリポジトリには、注文実行エンジン、監視（モニタリング）機能、ポートフォリオ構築・サイズ決定ロジック、リサーチ／ファクター計算、AI（ニュース NLP / レジーム判定）連携などの主要コンポーネントが含まれます。

主な目的
- 自動発注エンジン（ExecutionEngine）とそれを監視する仕組み
- Paper Trading（ペーパートレード）用の分離された DB & モックブローカー
- 日次のファクター計算・リサーチユーティリティ（DuckDB ベース）
- ニュースを LLM（OpenAI）でスコアリングし AI スコアを DB に保存
- 監視・アラート・キルスイッチによる安全停止

主な機能一覧
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（本番 / paper_trading 対応）
  - run_monitoring.py — SystemMonitor ポーリングループを起動（監視ログ保存）
- 設定関連
  - config_setup.py — .env 作成ウィザード（対話式）
  - validate_config.py — .env / config/*.yaml の事前検証 CLI
- モニタリング
  - SystemMonitor, RiskMonitor, TradeMonitor（監視エンジンにより束ねる）
  - MonitoringDB — SQLite に監視ログを永続化
  - KillSwitch — data/kill.flag による実行停止シグナル
- Execution（発注・リスク管理）
  - BrokerClientFactory（本番 or MockBroker の切替）
  - ExecutionEngine / OrderManager / RiskManager / Reconciler（発注ワークフロー）
- ポートフォリオ構築
  - 銘柄選定・重み付け（等金額・スコア重み）
  - セクター上限の適用、レジーム乗数
  - ポジションサイズ計算（リスクベース・等配分）
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, summary）
- AI（OpenAI）
  - news_nlp: raw_news を LLM でスコアリングし ai_scores テーブルへ書込
  - regime_detector: ETF + マクロニュースで日次レジーム判定（DuckDB へ書込）
- ツール
  - paper_verification_report — Paper Trading の検証レポート生成

前提 / 必要環境
- Python 3.10+
- 主な依存（抜粋）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- SQLite（組込）
- （任意）J-Quants / kabuステーションの API 設定（本番運用時）

セットアップ手順（簡易）
1. リポジトリを取得し、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

   ※ 実プロジェクトでは requirements.txt または poetry/poetry.lock に従ってください。

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でルートに .env を作成（.env.example を参考に）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)

5. データディレクトリの準備
   - デフォルトでは data/ 配下に DB 等を作成します。必要に応じて環境変数でパスを変更してください。

主要な環境変数（抜粋）
- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境指定
  - KABUSYS_ENV — development | paper_trading | live （デフォルト: development）
    - paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録されます
- DB / ログ
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログ出力レベル（デフォルト: INFO）
  - LOG_DIR — ログ保存先（デフォルト: logs/）
- Paper Trading の挙動
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）
- 監視関連
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - PID_FILE_PATH — 実行エンジンの PID ファイル（default: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（default: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（"1"で有効、デフォルト: "0"）
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）

起動・使い方（主な例）
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 or paper_trading を .env で切替）
  - python -m kabusys.run_execution
  - ※ 起動時に data/stop_requested.flag が存在する場合は起動せず終了
  - 実行中に data/stop_requested.flag または data/kill.flag を作成すると停止処理が走ります
  - 実行はデーモン化（nohup / systemd 等）して運用することを推奨

- Monitoring を起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を参照してログを残します
  - polling 間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）
  - 監視ループはプロセス優先度を高く設定し、stop_requested.flag を検出すると終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / レジーム判定（ライブラリ呼び出し例）
  - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=...)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

- ライブラリとしての利用例
  - ポートフォリオ構築:
    - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns

停止・セーフティ機構
- データ/フラグファイル
  - data/stop_requested.flag — run_* スクリプトが検出すると安全に終了します
  - data/kill.flag — KillSwitch が生成すると ExecutionEngine に停止シグナルを送るために使用
  - data/execution.pid — ExecutionEngine の PID ファイル（起動スクリプトが書込）

ログ
- 共通のログセットアップ関数 setup_logging により stdout と logs/<app_name>.log（日時ローテート）へ出力します
- LOG_DIR / LOG_LEVEL 環境変数で制御可能

監視データベース（MonitoringDB）
- SQLite を使用し以下のテーブルを作成・管理します（冪等）
  - system_status, trade_logs, positions, risk_logs, dashboard
- run_monitoring / MonitoringEngine / SystemMonitor / RiskMonitor 等がこれらへ書き込みます

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 作成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py などの監視関連ファイル)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - （その他: execution/、data/ などのモジュールが想定されます）

設計上の注意
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離された専用 SQLite を使用する設計です（安全のため）。
- LLM（OpenAI）連携は API 失敗時にフォールバック（スコア 0 や処理スキップ）する設計で、フェイルセーフを重視しています。
- 各ユーティリティは副作用が少ない純粋関数（portfolio 等）と、DB 書き込みを行う層（monitoring_db 等）で責務を分離しています。
- 設定ファイル（config/*.yaml）や .env の整合性は validate_config.py で事前検証可能です。

トラブルシューティング（よくある事項）
- .env が読み込まれない場合:
  - config.py は自動でプロジェクトルート（.git または pyproject.toml を基準）から .env を読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログファイルが作成されない場合:
  - LOG_DIR の作成に失敗するとコンソール出力のみで継続します。パーミッションやディスク容量を確認してください。
- OpenAI 関連で KeyError / ValueError が出る場合:
  - OPENAI_API_KEY を .env または引数で渡してください。テスト時は API 呼び出し関数をモックできます。

最後に
- 本 README はコードベースに含まれる主要機能の概要と基本操作方法をまとめたものです。実運用前に必ず python -m kabusys.validate_config で設定検証を行い、Paper Trading モードでの十分な検証を行ってください。

必要であれば、systemd unit の例や詳細なデプロイ手順、より詳しい API / モジュール別ドキュメントを追加します。どの情報を優先して追加したいか教えてください。
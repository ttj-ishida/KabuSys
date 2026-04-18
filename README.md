# KabuSys

日本株向けの自動売買／リサーチ基盤ライブラリ。  
ExecutionEngine（発注実行）、Monitoring（監視）、Research（ファクター・特徴量計算）、Portfolio（銘柄選定・サイズ決定）、AI モジュール（ニュース NLP / レジーム判定）などの機能を含むモジュール群です。

以下はこのリポジトリに含まれる主要機能・セットアップ・使い方・ディレクトリ構成の概要です。

---

プロジェクト概要
- 日本株自動売買システムに必要なコンポーネント群をモジュール化したライブラリ。
- 発注実行（実口座／ペーパー取引分離）、実行監視・アラート、リサーチ（ファクター計算・特徴量探索）、ポートフォリオ構築、ニュースセンチメント評価（OpenAI を利用）等を提供。
- ローカル実行時に .env で環境変数を管理する設計。SQLite（監視ログ等）や DuckDB（分析用）を使用。

主な機能一覧
- Execution
  - ExecutionEngine を起動して注文実行処理を行う（run_execution.py）。
  - Paper trading モードでは MockBroker を使用して data/paper_trading.db に分離して記録。
  - リスク管理（RiskManager）、Order Manager、Reconciler 等を統合。
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視・ログ記録（run_monitoring.py）。
  - kill.flag による外部停止（Kill Switch）や停止フラグ stop_requested.flag の検出。
  - MonitoringDB（SQLite）へ system_status、trade_logs、risk_logs、dashboard、positions を永続化。
- Research
  - ファクター計算（momentum / volatility / value 等）: DuckDB を用いた純粋関数実装。
  - 特徴量探索（将来リターン計算、IC、統計要約等）。
- Portfolio
  - 候補選定（スコア順）、等分配/スコア加重、セクターキャップ適用、ポジションサイズ計算（lot 単位丸め・資金配分上限・risk_based など）。
- AI
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini 等）で銘柄ごとのセンチメントを算出し ai_scores に書き込む。
  - regime_detector: ETF（1321）MA200 乖離 + マクロニュースセンチメントを合成して daily market_regime を算出・保存。
  - API の呼び出しはリトライ・バックオフ・バリデーションを実装。
- CLI / ユーティリティ
  - .env 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper trading レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - 推奨パッケージ（ソースから参照）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt）
4. 環境変数 (.env) を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を直接作成する（下記「主な環境変数」参照）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。
6. 必要フォルダ作成（ログ・データ）
   - data/ （SQLite DB 等がここに生成されます）
   - logs/ （ログファイル）
   - 実行スクリプトが自動で作成することもありますが、権限等に注意してください。

主な環境変数（Settings で使用されるもの）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / オプション
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: 分析用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading モード）
  - OPENAI_API_KEY: OpenAI API キー（AI 関連機能）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
  - PID_FILE_PATH / KILL_FLAG_PATH 等（デフォルトは data/ 以下）
- 監視用に使える
  - MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0）

簡単な .env の例（参考）
- .env に以下のようなキーを含めます（値は実際のものに置き換えてください）
  - KABUSYS_ENV=development
  - JQUANTS_REFRESH_TOKEN=your_jquants_token
  - KABU_API_PASSWORD=your_kabu_password
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - LOG_LEVEL=INFO
  - OPENAI_API_KEY=sk-...

使い方（主なコマンド）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine を起動（実行エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH にデータを記録
  - 実行中に data/stop_requested.flag が作成されると終了
- Monitoring（ポーリング監視）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 停止フラグ data/stop_requested.flag や監視用 kill.flag を用いて外部停止・キル判定
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 日付範囲指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db でデータベースパスを指定可能（デフォルト: data/paper_trading.db or 環境変数）
- AI / Research 呼び出し（ライブラリ関数として使用）
  - kabusys.ai.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
  - kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等

運用上のポイント
- Logging
  - kabusys.utils.logging_setup.setup_logging を各起動スクリプトで使用。logs/<app_name>.log に日次ローテーションで出力。
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び出して優先度を上げます（許可がない場合は警告でスキップ）。
- Kill Switch / Stop フラグ
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine 側で停止を検出します。
  - Stop フラグ（data/stop_requested.flag）は run_execution/run_monitoring の外部停止に使用。
- Paper trading
  - KABUSYS_ENV=paper_trading の際は本番 DB と完全分離し、MockBrokerClient を使って発注・約定ロジックをシミュレート。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル・インデックスを作成し、既存列の追加（簡易マイグレーション）も行います。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数/設定読み込みロジック
  - config_setup.py          -- .env 対話ウィザード CLI
  - validate_config.py       -- 起動前設定検証 CLI
  - run_execution.py         -- ExecutionEngine 起動スクリプト
  - run_monitoring.py       -- SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        -- （trade 監視関連）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        -- （アラート送信ロジック）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                    -- 実行時に使用する SQLite / pid / flag 等（.gitignore 推奨）
  - logs/                    -- ログ出力（デフォルト）

補足（実装上の注意）
- DuckDB は分析用（prices_daily / raw_financials / raw_news 等を想定）で、多くの research / ai 機能は DuckDB 接続を期待します。
- OpenAI API を使う処理は API キーに依存します。テスト時は内部の API 呼び出しヘルパーをモックしてテストする想定です（score_news/_call_openai_api 等）。
- .env は機密情報を含むため Git にコミットしないでください（config_setup.py のヘッダにも明記）。

ライセンス・バージョン
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

---

問題・追加希望・ドキュメント追記等があれば教えてください。README の内容をプロジェクト方針に合わせて調整します。
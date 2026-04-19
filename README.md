# KabuSys

日本株自動売買システム（ライブラリ）  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI 補助（ニュース NLP / レジーム検出）・リサーチ用ユーティリティを含む自動売買基盤の一部実装を含みます。

注意: README はソースコード（src/kabusys 以下）をベースに作成しています。実運用環境では .env の適切な設定や本番 API キーの管理に注意してください。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（コマンド例）
- 環境変数一覧（主要）
- ファイル / ディレクトリ構成

---

プロジェクト概要
- バックテストや運用に必要なモジュール群を提供する Python パッケージ。
- コンポーネント:
  - ExecutionEngine（発注・リスク管理・注文管理）
  - Monitoring（システム監視、リスク監視、アラート、Kill Switch）
  - Portfolio（候補選定・重み計算・ポジションサイズ計算・リスク調整）
  - Research（ファクター計算・特徴量探索・IC 計算）
  - AI モジュール（ニュースセンチメントの LLM スコアリング、レジーム判定）
  - ユーティリティ（ログ設定、プロセス優先度、設定読み込みウィザードなど）
- 永続化:
  - SQLite（監視ログ / 発注履歴等）
  - DuckDB（分析 / リサーチ用）

---

主な機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）により .env を対話的に生成
- 設定検証 CLI（python -m kabusys.validate_config）で .env と config/*.yaml の検証
- ExecutionEngine を起動する run_execution.py（本番/ペーパートレード切替対応）
- Monitoring 用のポーリングループ run_monitoring.py（プロセス監視・データ鮮度・Kill Switch）
- Portfolio 構築ユーティリティ:
  - 候補選定（select_candidates）
  - 等分・スコア重み配分（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ、レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- Research ツール:
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（OpenAI）連携:
  - ニュース記事の銘柄別センチメントスコアリング（kabusys.ai.news_nlp.score_news）
  - マクロニュース + ETF MA でレジーム判定（kabusys.ai.regime_detector.score_regime）
  - 接続は環境変数 OPENAI_API_KEY を利用
- ツール:
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

セットアップ手順（ローカル開発）
要求 Python バージョン: 3.10 以上（型注釈で | 演算子を使用）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb psutil openai

   追加（任意・機能により必要）:
   pip install pyyaml  # validate_config の YAML 検証を行う場合

   ※ requirements.txt がある場合はそちらを利用してください:
   pip install -r requirements.txt

4. .env の作成（対話式推奨）
   python -m kabusys.config_setup

   これによりプロジェクトルートに .env が作成されます。
   手動で作る場合は .env.example を参考にしてください（存在する場合）。

5. 設定検証（必須項目やパスを確認）
   python -m kabusys.validate_config
   本番前に --strict を付けて警告も失敗扱いにできます:
   python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要に応じて）
   mkdir -p data logs

---

基本的な使い方（コマンド例）

- 監視ループを起動（ポーリング）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に production (settings.sqlite_path) の sqlite を使用する点に注意

- ExecutionEngine（発注エンジン）を起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、デフォルトで data/paper_trading.db を使用します（本番 DB と分離）
  - 起動中は data/execution.pid が書かれ、data/stop_requested.flag や data/kill.flag により停止・制御されます

- .env を対話的に作成 / 更新
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポートを生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または DB パス指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI スコア / レジーム判定（ライブラリ関数）
  - ニューススコア: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  これらは DuckDB 接続（duckdb.connect(...））を渡して利用します。API キーは引数か環境変数 OPENAI_API_KEY を使用します。

停止・Kill Switch
- シンプルな停止フロー:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループはそれを検知して終了／停止します（stop_requested.flag は run_* が参照するファイル）。
  - data/kill.flag は KillSwitch によって書かれることで ExecutionEngine 停止要因となります。
- 実行時の Kill Flag のクリア設定:
  - KILL_FLAG_CLEAR_ON_START 環境変数 (0/1)。本番では 0 を推奨。

---

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須): kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト development
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を消すか（"1" でクリア）

自動 .env ロード
- デフォルトでプロジェクトルートの .env を自動ロードします（CWD に依存せず package の位置から探索）。
- 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

ディレクトリ構成（主要ファイル抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数読み込み・Settings
    - config_setup.py           # .env 対話ウィザード
    - validate_config.py        # 設定検証 CLI
    - run_execution.py          # ExecutionEngine 起動スクリプト
    - run_monitoring.py         # Monitoring 起動スクリプト
    - utils/
      - logging_setup.py        # ログセッティングユーティリティ
      - process_priority.py     # 優先度 / affinity 設定
    - monitoring/
      - monitoring_db.py        # SQLite テーブル初期化・永続化レイヤー
      - system_monitor.py
      - trade_monitor.py        # (ソース参照)
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py        # (実装参照)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
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
    - monitoring/                # （上で列挙）
    - tools/
      - paper_verification_report.py
    - data/                      # デフォルトのデータ/DB 保管先（リポジトリには含めない）
- data/                         # 実行時に生成されることが多い（monitoring.db, paper_trading.db, kill.flag, execution.pid 等）
- logs/                         # ログ出力先（デフォルト）

（上記はソース内に存在するモジュールを抜粋しています。実際のファイル構成はリポジトリのルートをご確認ください）

---

運用上の注意
- 本番（KABUSYS_ENV=live）では特に LINE 通知や kill フラグの扱い、DB パス・バックアップ、API キー管理に注意してください。
- OpenAI API 呼び出しはコストやレート制限の影響を受けるため、キー管理やレート制御を適切に設定してください。
- monitoring は本番 sqlite_path を参照します（監視ログは本番 DB に記録されます）。ペーパートレード実行時は paper 用 DB が別途使われます。
- ログディレクトリの作成に失敗した場合はファイルログをスキップして標準出力のみになります。ログディレクトリ（デフォルト logs/）のパーミッションを確認してください。

---

開発に関するヒント
- DuckDB を使った分析 / research 関数は、DuckDB に prices_daily / raw_financials / raw_news 等のテーブルをロードして動作します。テーブルスキーマはソースのクエリを参照してください。
- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env 自動ロードをスキップできます。
- AI モジュールの外部 API 呼び出しは _call_openai_api を patch することでユニットテストでモック化できます（ソース内にその旨の注記あり）。

---

サポート / コントリビュート
- バグ報告 / 機能要望は issue を作成してください。
- コントリビュート時はテストを追加し、既存の CLI（config_setup / validate_config）を用いて設定を検証してから PR を送ってください。

---

この README はソースコードのコメント・ドキュメントに基づき作成しています。実際の運用や導入時はプロジェクトのドキュメント（例: PortfolioConstruction.md / StrategyModel.md 等）や config/*.yaml を参照してください。
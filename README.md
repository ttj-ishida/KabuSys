KabuSys — 日本株自動売買システム (README)
====================================

概要
----
KabuSys は日本株向けの自動売買システムの骨格を提供する Python パッケージです。  
主な機能は以下の通りです：

- 発注エンジン（ExecutionEngine）と監視（Monitoring）を分離して実行
- Paper Trading（モックブローカー）対応（本番 DB と分離）
- システム監視 / リスク監視 / トレード監視と Kill Switch（停止フラグ）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算（DuckDB を用いた日次ファクター等）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- ユーティリティ（設定ウィザード、設定検証、ペーパートレード検証レポート等）

主な機能一覧
--------------
- 実行関連
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV によって paper_trading モードあり）
- 監視関連
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを収集
  - monitoring_engine.py: 各 Monitor を束ねて動かすエンジン（テスト / 本番ループ）
  - monitoring_db.py: SQLite を用いた監視データの永続化層
  - risk_monitor.py / trade_monitor.py / system_monitor.py: 個別監視コンポーネント
  - kill_switch.py: リスク発生時に data/kill.flag を書き込む Kill Switch
- 設定管理 / ユーティリティ
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の検査ツール
  - utils/logging_setup.py: ログ設定ユーティリティ（コンソール + 日次ローテーション）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
- ポートフォリオ / リサーチ
  - portfolio/*: 候補選定、重み算出、ポジションサイズ計算、セクター制約、レジーム倍率
  - research/*: DuckDB を使ったファクター計算・特徴量解析
- AI 関連
  - ai/news_nlp.py: OpenAI でニュースセンチメントを算出して ai_scores に格納
  - ai/regime_detector.py: マクロ記事 + ETF MA で市場レジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading DB から検証レポートを生成

セットアップ手順
----------------
前提：
- Python 3.9+ を推奨（ソースは型ヒント等を使用）
- SQLite（標準ライブラリ）、DuckDB、psutil、openai などのパッケージを使用

1. リポジトリをクローン
   - git clone <repo-url>
   - ソースは src/kabusys 以下に配置されています。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   例（必要なパッケージを明示的にインストール）:
   - pip install duckdb psutil openai
   - 任意: PyYAML (validate_config の YAML 検証に使用)
   - 必要に応じて他のライブラリを追加してください

   （パッケージ一覧が requirements.txt にない場合は上記を目安にしてください）

4. 初期設定ファイル (.env) を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参照）。.env は決して Git にコミットしないでください。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます:
     - python -m kabusys.validate_config --strict

6. data/ と logs/ ディレクトリが必要になることがあります。起動時に自動作成されますが、権限問題がある場合は事前に作成してください。

主要な環境変数（主なもの）
-------------------------
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading: 発注は MockBrokerClient を使い、data/paper_trading.db に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（ai.news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading モード用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH 等は Settings から設定可能（デフォルト data/ 以下）

使い方（起動・ツール）
--------------------

設定ウィザード
- python -m kabusys.config_setup
  - 対話形式で .env を作成・更新します。

設定検証
- python -m kabusys.validate_config
  - 環境変数や config/*.yaml の存在・基本検証を行います。

ExecutionEngine（実行エンジン）起動
- python -m kabusys.run_execution
  - KABUSYS_ENV により動作が変わります:
    - paper_trading: MockBrokerClient を使用し、paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録
    - live / development: sqlite_path を使用
  - 起動時に data/stop_requested.flag が存在すると起動しません
  - 実行中はデータベース接続や PID ファイル（data/execution.pid）を扱います

Monitoring（監視）起動
- python -m kabusys.run_monitoring
  - SystemMonitor を定期ポーリングして監視ログ（SQLite）へ保存します
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を利用します（監視データは共有される想定）

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで DB を指定できます

AI 関連（ニュース NLP / レジーム検出）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡してニュースのセンチメントを ai_scores テーブルへ書き込み
  - OPENAI_API_KEY が必要（引数 api_key で指定可能）
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF MA とマクロ記事を組み合わせて market_regime テーブルに書き込む
  - API 呼び出しの失敗はフェイルセーフで処理されます（デフォルトでは macro_sentiment=0.0）

ライブラリ的な利用
- パッケージとして import して利用可能:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  - from kabusys.ai import score_news

注意点 / トラブルシューティング
--------------------------------
- .env は必ず設定してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など必須）。
- OpenAI を使う機能は OPENAI_API_KEY が必要です。キーが未設定だと ValueError が発生します。
- validate_config は PyYAML 未インストール時に YAML の検査をスキップします（警告）。YAML 検証を行う場合は PyYAML をインストールしてください。
- run_monitoring は監視用 DB（SQLite）を使用します。Monitoring は KABUSYS_ENV にかかわらず sqlite_path を参照します（意図的設計）。
- process priority や CPU affinity の設定は権限や OS に依存します。設定に失敗しても警告ログが出て続行します。
- ログファイル出力先はデフォルト logs/。ディレクトリ作成に失敗するとコンソール出力のみになります。

ディレクトリ構成（抜粋）
----------------------
以下はコードベース（src/kabusys）の主要ファイル・ディレクトリ構成の抜粋です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py  (実装がある想定)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - data/            (ランタイムで使用する data/*.db, *.flag, *.pid を想定)
    - logs/            (ログ出力先：デフォルト)

付録: よく使うコマンド例
-----------------------
- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視起動（ポーリング間隔を 30 秒に設定）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスや貢献方法を記載してください）

以上。必要であれば README にサンプル .env のテンプレート、requirements.txt、起動例の systemd/cron サンプルやデバッグ方法（ロギングの詳細な読み方）などを追記できます。どの情報を追加したいか教えてください。
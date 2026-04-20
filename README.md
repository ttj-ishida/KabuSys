README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究基盤を想定した Python パッケージです。
モジュール構成は以下を含みます（抜粋）:

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・約定管理
- 監視サブシステム（Monitoring）: システム状態・注文・リスク監視と Kill Switch
- ポートフォリオ構築ロジック: 候補選定、重み計算、ポジションサイズ算出
- 研究用モジュール: ファクター計算、特徴量探索
- AI ユースケース: ニュース NLP によるセンチメント評価、レジーム判定
- 運用ツール: .env ウィザード、設定検証、ペーパートレード検証レポート生成

設計上のポイント:
- .env と環境変数で設定管理（自動ロード機能あり）
- Paper Trading 環境は本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用 DB、SQLite を監視 / ログ用 DB に利用
- OpenAI を用いた NLP 処理を一部で実装（API キー必須）

主な機能一覧
---------------
- 環境セットアップウィザード: kabusys.config_setup (対話式 .env 生成)
- 設定検証 CLI: kabusys.validate_config（.env や config/*.yaml の基本チェック）
- 実行エンジン起動: kabusys.run_execution（KABUSYS_ENV により paper/live 振る舞い）
- 監視ループ起動: kabusys.run_monitoring（System / Trade / Risk を定期チェック）
- ペーパートレード検証レポート: kabusys.tools.paper_verification_report
- ポートフォリオ構築: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- 研究用ファクター計算: calc_momentum, calc_volatility, calc_value
- AI ベース処理: news_nlp.score_news（OpenAI を用いたニューススコアリング）、regime_detector.score_regime
- ログ設定ユーティリティ、プロセス優先度設定ユーティリティ等の補助

前提 / 必要環境
----------------
- Python 3.10 以上（型注釈に | 記法を使用）
- 必須外部ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML: config/*.yaml の構文検証に使用
- SQLite は標準ライブラリで利用
- システムでプロセス優先度や CPU affinity を変更する場合は適切な権限が必要

セットアップ手順
----------------
1. リポジトリをクローンしてプロジェクトルートへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai
   - （YAML 検証を使うなら）pip install pyyaml

   参考（requirements.txt を用意する場合）:
   - duckdb
   - psutil
   - openai
   - pyyaml (任意)

4. Python パッケージとしてローカルインストール（開発モード推奨）
   - pip install -e .

5. .env を生成 / 設定
   - python -m kabusys.config_setup
     - 対話式に各種環境変数を作成します（.env に保存）
   - 既存の .env を手動で用意する場合は .env.example を参考にしてください

6. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

使い方（主要コマンド）
--------------------

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
    - 実行中に同ファイルが作成されるとエンジンに停止シグナルを送ります。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を参照（KABUSYS_ENV に依存しない）
  - data/stop_requested.flag を配置すると監視ループを終了します

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 処理（ニュース NLP / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime はライブラリ関数として呼び出します
  - 実行時に OPENAI_API_KEY 環境変数を設定するか、関数引数でキーを渡してください

主要な環境変数（抜粋）
-----------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI 利用時に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視・制御用）

注意点・運用メモ
-----------------
- .env は決してリポジトリにコミットしないでください（config_setup でも注記あり）。
- 自動環境読み込み:
  - プロジェクトルートが .git または pyproject.toml で検出される場合、起動時に .env および .env.local を自動ロードします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効にできます（テスト用途）。
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力（デフォルト logs/）
  - setup_logging() により stdout 出力も行います
- プロセス優先度の設定は psutil を使い OS に依存します。権限が足りないと警告を出してスキップします。
- Kill Switch:
  - 監視側が問題を検出すると data/kill.flag を書き込み、Execution を安全に停止させる仕組みがあります。
  - kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）で指定。Execution 側は起動時にクリアオプションを持ちます。

ディレクトリ構成（主要ファイル）
------------------------------
プロジェクト内の主要な構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数読み込み・Settings クラス
    - config_setup.py           # .env ウィザード
    - validate_config.py        # 設定検証 CLI
    - run_execution.py          # ExecutionEngine 起動スクリプト
    - run_monitoring.py         # Monitoring ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py         # （略: trade 関連監視）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py         # （アラート送信ロジック）
    - execution/                 # Execution 関連（BrokerFactory 等）
      - order_manager.py
      - execution_engine.py
      - broker_factory.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

サンプル .env の最小例
----------------------
以下は .env に設定すべき最低限のキー例（実運用ではより多くの値が必要）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

よくある質問（FAQ）
-------------------
Q: Paper Trading と Live の DB は分離されていますか？
A: はい。KABUSYS_ENV=paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。Monitoring は常に sqlite_path（監視用 DB）を使用します。

Q: ログはどこに出力されますか？
A: デフォルトは logs/<app_name>.log。コンソール（stdout）にも出力されます。ログディレクトリは環境変数 LOG_DIR で上書き可能です。

Q: OpenAI のキーがないと何が動きますか？
A: Execution の基本的な発注・監視・ポートフォリオ計算・研究用 SQL は問題なく動きます。news_nlp / regime_detector の AI 機能のみ OpenAI API キーが必要です（未設定時は明示的なエラーやフェイルセーフ挙動があります）。

補足
----
この README はコードベースから読み取れる設計意図・操作方法をまとめたものです。実際の運用では config/*.yaml（存在する場合）や README の補足ドキュメント、運用マニュアルを参照してください。必要であれば、本 README をベースに導入手順や運用手順のテンプレートをさらに詳しく作成できます。
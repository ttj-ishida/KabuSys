README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究フレームワークです。  
本リポジトリには実行エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ファクター計算や特徴量探索などのリサーチ機能、ニュース NLP を利用した AI スコアリング、ポートフォリオ構築ユーティリティなどが含まれます。モジュール設計は CLI スクリプトとライブラリ関数で分離されており、ペーパートレード（テスト）環境と本番環境を切り替えて運用できます。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution）  
  - KABUSYS_ENV により paper_trading（MockBroker）と live を切り替え
  - paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）へ記録して本番 DB と分離
  - PID ファイル管理・停止フラグ検知対応
- Monitoring 起動スクリプト（run_monitoring）  
  - システムリソース・データ鮮度・注文状況・リスクを定期ポーリングして SQLite に保存
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - kill.flag による ExecutionEngine 停止（Kill Switch）実装
- 設定支援・検証ツール  
  - 対話式 .env 作成ウィザード（config_setup）  
  - 起動前設定検証 CLI（validate_config）: 必須環境変数・YAML 設定・パスなどをチェック
- Paper Trading 検証レポート（tools/paper_verification_report）  
  - ペーパートレード DB から稼働率・注文成功率・レイテンシなどの指標を算出して PASS/FAIL を判定
- ポートフォリオ構築ユーティリティ（portfolio）  
  - 候補選定、等配分 / スコア加重、リスク調整（セクターキャップ、レジーム乗数）、株数決定（単元丸め）等
- リサーチ（research）  
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン・IC（Information Coefficient）・統計サマリー
- AI 支援モジュール（ai）  
  - ニュース NLU による銘柄単位センチメントスコア生成（OpenAI 使用） — kabusys.ai.score_news
  - マクロニュース + ETF MA200 による市場レジーム判定 — kabusys.ai.regime_detector.score_regime
- 汎用ユーティリティ（utils）  
  - ロギング統一設定（ファイルローテーション含む）setup_logging
  - プロセス優先度 / CPU affinity 操作ユーティリティ

セットアップ
----------
1. Python 環境（推奨: 3.10+）を用意します。

2. 必要パッケージをインストールします（プロジェクトに requirements.txt がない場合は下記を参考に個別インストールしてください）。例:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で YAML チェックを行いたい場合）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. プロジェクトルートに .env を作成します（対話式ウィザード推奨）:
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで入力すると .env が生成されます。生成後、設定内容を検証します:
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も FAIL 扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```

4. ログディレクトリやデータディレクトリの作成（通常は自動作成されますが確認してください）:
   - デフォルト DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/<app_name>.log

環境変数の主な一覧
------------------
- 必須（起動前に設定する必要あり）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 推奨 / 任意
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）
  - OPENAI_API_KEY（AI 関連機能利用時）
  - MONITOR_POLL_INTERVAL（run_monitoring ポーリング間隔秒）
  - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア）

使い方（主要スクリプト）
----------------------

- ExecutionEngine（エンジン起動）
  - 標準実行:
    ```
    python -m kabusys.run_execution
    ```
  - 概要:
    - KABUSYS_ENV が paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動を行いません。
    - 実行中は data/execution.pid を作成します。停止は stop flag（data/stop_requested.flag）で行います。

- Monitoring（監視ループ起動）
  - 標準実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - オプション（環境変数）:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）、デフォルト 60
  - 概要:
    - システムリソース、データ鮮度、注文ログ等を監視し SQLite（settings.sqlite_path）へ永続化します。
    - stop_requested.flag を検知するとループを終了します。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスを明示する場合:
    ```
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- AI 関連（ライブラリ関数）
  - ニュース NLP（銘柄別センチメント）:
    - 呼び出し例（DuckDB 接続を渡す）:
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key="...")

    - 必要: OPENAI_API_KEY または api_key を引数で渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, target_date, api_key="...")

- ライブラリ / リサーチ関数の利用例
  - ポートフォリオ構築:
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - ファクター計算:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    calc_momentum(duckdb_conn, date(2026, 4, 1))

監視・停止フロー（Kill Switch）
------------------------------
- KillSwitch は RiskMonitor の結果（ドローダウンやポジション上限）に応じて data/kill.flag を書き込みます。
- ExecutionEngine は起動時に kill.flag を参照し、必要なら自動クリア（KILL_FLAG_CLEAR_ON_START=1）設定に基づき処理します。
- 実行を強制停止させたい場合は data/kill.flag を作成するか、data/stop_requested.flag を置くことでモニタ／エンジンが停止します。

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。
- デフォルト出力:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log を日次でローテーション（30日保持）
- 環境変数 LOG_DIR / LOG_LEVEL で上書き可能

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイル・モジュールの抜粋（実際のツリー）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照実装あり)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/                # Execution 関連コンポーネント（broker, engine, order_manager 等）
  - data/                     # 実行時に生成されるデータファイル（DB, pid, flag 等）

注意事項 / 運用上のヒント
------------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダーにも注意書きがあります）。
- KABUSYS_ENV を live に設定する際は十分な確認を行ってください（validate_config が警告を出します）。
- OpenAI を用いる機能は API キーが必須です。API 呼び出しはレート制限やエラーを考慮したリトライ実装が入っていますが、コスト管理に注意してください。
- Monitoring は監視 DB（SQLite）に書き込みます。監視 DB は run_monitoring から初期化されます（init_monitoring_db）。
- run_execution と run_monitoring は stop_requested.flag や stop flag を検知して安全に停止します。CI / 自動化の際はこれらのフラグファイルを活用してください。
- Paper Trading と本番 DB は物理的に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。

ライセンス / バージョン
-----------------------
パッケージバージョンは kabusys.__version__ で管理されています（例: 0.1.0）。

---

追加情報や運用フローのテンプレート（systemd サービス定義例や Docker 化）を希望する場合は、利用環境（Linux ディストリビューション、systemd/cron/コンテナなど）を教えてください。それに合わせた起動/監視定義や dockerfile の雛形を作成します。
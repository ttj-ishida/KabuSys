# KabuSys — 日本株自動売買システム (README)

概要
----
KabuSys は日本株の自動売買に必要なコンポーネント群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助など）をまとめたリポジトリです。  
本リポジトリはプロダクション運用を念頭に設計されており、以下の特徴を持ちます。

- 実際の発注を行う ExecutionEngine（本番）と、完全に分離された Paper Trading（ペーパートレード）モードをサポート
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- DuckDB を用いたリサーチ／特徴量計算
- OpenAI を利用したニュース NLP / レジーム判定（オプション）
- 設定ウィザードと起動前の検証ツール

主な機能
--------
- 実行エンジン起動スクリプト: run_execution.py（ExecutionEngine を起動）
- 監視ループ起動スクリプト: run_monitoring.py（SystemMonitor を周期実行）
- 設定ウィザード: config_setup.py（.env の対話的生成）
- 設定検証: validate_config.py（.env と config/*.yaml の検証）
- Paper Trading 検証レポート: tools/paper_verification_report.py
- ポートフォリオ構築: select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes 等
- リサーチ: ファクター計算（momentum/value/volatility）、IC 等
- AI モジュール: ニュース NLP（score_news）・レジーム判定（score_regime）
- 監視永続化: SQLite ベースの monitoring_db（system_status / trade_logs / risk_logs / positions / dashboard）

セットアップ手順
----------------
1. Python 環境
   - 推奨: Python 3.9+（実装で typing / pathlib 等を利用）
   - 仮想環境を作成しておくことを推奨:
     ```
     python -m venv .venv
     source .venv/bin/activate  # Linux/macOS
     .venv\Scripts\activate     # Windows
     ```

2. 必要パッケージのインストール（例）
   - 最低限の依存:
     ```
     pip install duckdb psutil openai
     ```
   - YAML の検証を行いたい場合:
     ```
     pip install PyYAML
     ```
   - （将来的に requirements.txt を用意している場合はそちらを利用）

3. .env の作成（対話式）
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定を検証:
     ```
     python -m kabusys.validate_config
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - それ以外に OPENAI_API_KEY（AI 機能利用時）など

4. データディレクトリの準備
   - デフォルトの DB / フラグファイルなどは project_root/data に置かれます。必要に応じて作成・パーミッションを確認してください。
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

重要な環境変数（主なもの）
------------------------
- KABUSYS_ENV: execution モード ("development" / "paper_trading" / "live")（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）  
  ※ Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード ("instant" | "partial" | "never" | "reject")
- LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR")
- MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効、推奨は 0）

起動・使い方
------------

- .env を生成・編集したら必ず設定検証を行ってください。
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine（トレード実行）を起動:
  - 通常:
    ```
    python -m kabusys.run_execution
    ```
  - Paper Trading を使う場合:
    - KABUSYS_ENV を paper_trading に設定（.env で設定）
    - run_execution は paper_trading 時に MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。

- Monitoring（監視ループ）を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - run_monitoring は Monitoring 用 DB に常に本番 sqlite_path を使います（環境に依らず）。

- 停止制御（Kill / Stop）
  - ExecutionEngine 停止トリガーは data/kill.flag（KillSwitch）に書き込むことによって発動します。
  - run_execution/run_monitoring は data/stop_requested.flag の存在で優雅に終了します。
  - PID ファイル: data/execution.pid（ExecutionEngine が起動中は PID を書き込みます）

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で別の DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可。

- AI モジュール（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要:
    ```
    export OPENAI_API_KEY=sk-...
    ```
  - DuckDB 接続を渡して関数を呼び出します（例）:
    ```py
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - 同様に regime_detector.score_regime を利用します。

- リサーチ / ポートフォリオ関数利用例
  - DuckDB 接続を作成し、kabusys.research.calc_momentum 等の関数を呼ぶことでファクター計算が可能。

ログ
----
- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution"|"monitoring")
- デフォルトログディレクトリ: logs/
- ログファイル: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30日保持）
- LOG_DIR 環境変数でログ出力先を変更できます。

ディレクトリ構成（主要ファイル）
------------------------------
プロジェクトの主要なソースは src/kabusys 配下にあります。主なファイル/ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数／設定読み込みロジック
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (存在する想定の実装)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在する想定の実装)
  - utils/
    - logging_setup.py
    - process_priority.py

設計メモ / 運用上の注意
-----------------------
- Monitoring は常に本番の monitoring.db を使います（KABUSYS_ENV に関係なく sqlite_path を使用）。Paper Trading ログは paper_sqlite_path に分離されます。
- run_execution は起動時に data/stop_requested.flag がある場合は起動を中止します。停止は stop_requested.flag の作成または ExecutionEngine 側の Kill Switch によって行えます。
- AI 機能を有効にする際は OpenAI のレート制限やエラーハンドリングを考慮してください（モジュール内で指数バックオフ処理あり）。
- production 運用時は KABUSYS_ENV=live、LOG_LEVEL=INFO/ERROR、KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- .env は絶対に Git にコミットしないでください（API キーやパスワードを含むため）。

トラブルシューティング
---------------------
- ログディレクトリ作成に失敗した場合、コンソール出力のみで動作を継続します。パーミッションを確認してください。
- データベースのスキーマ拡張（例: monitoring_db のマイグレーション処理）は起動時に行われますが、バックアップを取った上で運用してください。
- validate_config でエラーが出た場合は指示に従い .env や config/*.yaml を修正してください。

貢献 / 開発
------------
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できます（テストなどで便利）。
- モジュール単位でのユニットテストやドキュメント化を推奨します（特に取引ロジック・リスク管理周り）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

以上。運用や導入にあたって不明点があれば、どの部分を詳しく知りたいか教えてください。例えば ExecutionEngine の起動フロー、Monitoring のアラート設定、AI モジュールのテスト方法など、具体的な使い方を補足できます。
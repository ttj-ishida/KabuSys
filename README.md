KabuSys — 日本株自動売買システム（ドキュメント）
====================================

概要
----
KabuSys は日本株向けの自動売買 / 研究用ライブラリ群と起動スクリプトを含むプロジェクトです。  
主に以下を提供します。

- ExecutionEngine（発注・リスク管理・注文管理）の起動スクリプト
- Monitoring（システム監視・リスク監視・Kill Switch）の起動スクリプトと永続化（SQLite）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI 補助（ニュース NLP による銘柄センチメント、レジーム判定）
- Paper Trading 用レポート生成ツール
- .env 対話式ウィザード / 設定検証ツール

特徴（主な機能）
----------------
- ExecutionEngine と Monitoring の分離起動（run_execution / run_monitoring）
  - KABUSYS_ENV による動作モード切替（development / paper_trading / live）
  - paper_trading モードでは MockBrokerClient を使用し、paper 専用 DB に記録
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
  - CPU / メモリ / ディスク / プロセス稼働監視、注文滞留・約定異常、ドローダウン監視など
  - 異常時に data/kill.flag を作成して ExecutionEngine を安全停止可能
- MonitoringDB：SQLite による監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - 起動時に必要なテーブルを冪等で作成・マイグレーション
- 研究モジュール（duckdb 経由で大量時系列データを処理）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン、IC、統計サマリ
- AI 機能（OpenAI 利用）
  - ニュースの銘柄別センチメントを LLM で推定して ai_scores に保存
  - マクロニュース + ETF MA200 乖離を使った市場レジーム判定
  - 再試行・バッチ・出力検証など堅牢設計
- ユーティリティ
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

セットアップ（ローカル開発向け）
----------------------------
前提: Python 3.10+ を想定

1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（主要な依存）
   - pip install duckdb psutil openai
   - （オプション）検証で YAML を使う場合: pip install PyYAML

   ※ requirements.txt がない場合は上記を手動で追加してください。

3. プロジェクトルートに移動
   - README と同階層に src/ がある構成を前提とします。パッケージを直接使う場合は PYTHONPATH を設定するか、pip install -e . を行ってください。

4. 初回設定（.env）  
   対話式ウィザードで .env を作成します:
   - python -m kabusys.config_setup
   例: KABUSYS_ENV=development（ローカルテスト） / paper_trading / live

5. 設定検証（必須環境変数や config/*.yaml の存在チェック）
   - python -m kabusys.validate_config
   - 警告を厳密に FAIL として扱う場合は --strict を付ける

主要な環境変数（よく使うもの）
--------------------------------
（.env に設定する想定。config_setup が対話で作成します）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: Monitoring SQLite path（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading モード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/… デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア, 0=しない。production は 0 推奨）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env 読み込み
- config.py はプロジェクトルート（.git または pyproject.toml の存在を基準）を探索し、.env/.env.local を自動で読み込みます。
- テストなど自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（起動・ツール）
----------------------

1. Monitoring の起動
   - 簡単起動: python -m kabusys.run_monitoring
   - 補足:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（例: MONITOR_POLL_INTERVAL=30）
     - run_monitoring は常に本番用 sqlite_path を使用（監視 DB は環境に依存しない）
     - 停止: プロジェクトルート/data/stop_requested.flag が存在するとループを抜けます

2. ExecutionEngine の起動
   - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番と分離）
     - 実行中は data/execution.pid に PID が書かれます
     - 停止: data/stop_requested.flag を作成するとエンジン停止を試みます

3. .env 対話式ウィザード
   - python -m kabusys.config_setup
   - 既存 .env を読み込み、Enter で既存値を採用できます

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

6. AI / 研究機能の利用（プログラムからの呼び出し）
   - ニュース NLP（スコア保存）:
     - from kabusys.ai import score_news
     - score_news(duckdb_conn, target_date, api_key=None)
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key=None)
   - 研究モジュール（ファクター等）:
     - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

ログと永続化
-------------
- ログはデフォルト logs/ ディレクトリに出力され、日次ローテーション（30世代保持）されます。ログファイル名はアプリ名（例: execution.log, monitoring.log）。
- 監視データは SQLite（monitoring.db や paper_trading.db）に保存されます。
- 分析用 DB は DuckDB（kabusys.duckdb）を使用します。

停止・Kill 機構
----------------
- stop_requested.flag（プロジェクト root/data/stop_requested.flag）
  - run_monitoring / run_execution はこのファイルの存在を監視し、検出時に自らを停止します（オフラインでの安全停止）。
- kill.flag（data/kill.flag）
  - KillSwitch（リスク監視）により条件を満たした場合に作成され、ExecutionEngine の停止トリガーとして機能します。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動でクリアされます（本番では 0 推奨）。

データベース（Migration）
------------------------
- monitoring_db.init_monitoring_db(conn) は起動時に必要テーブルを作成し、既存 DB に対する軽微なマイグレーション（カラム追加など）も行います（冪等実行）。

開発者向けノート / 注意点
------------------------
- 実際の取引を行う live 環境では設定（LINE 通知、KILL_FLAG 設定、パスワード等）を十分に確認してください。validate_config は live モード時に追加警告を出します。
- OpenAI を使う処理は API キーが必須です。API 呼び出しはリトライやフェイルセーフを備えていますが、キーの漏洩に注意してください。
- 価格や出来高など欠損データ（0 や None）に対してはフォールバックが限定的な部分があります（コメントに TODO あり）。データ整合性は事前に確認してください。
- config.py はプロジェクトルートの検出に __file__ の親を走査します。パッケージ化・配置後の動作に注意してください。

ディレクトリ構成（概略）
-----------------------
以下は主要ファイルのツリー（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - run_monitoring.py           -- Monitoring の起動スクリプト
  - run_execution.py            -- ExecutionEngine の起動スクリプト
  - config.py                   -- 環境変数 / Settings 管理（自動 .env 読込含む）
  - config_setup.py             -- .env 対話式ウィザード
  - validate_config.py          -- 設定検証 CLI
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (実装ファイルがある想定)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装ファイルがある想定)
  - execution/                   -- Execution（order manager / engine / broker factory 等）
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

付録: よく使うコマンド例
-----------------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- Monitoring 起動（ポーリング30秒）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動（ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

おわりに
--------
この README はソースコードの設計意図と主要な使い方をまとめたものです。各モジュール（特に execution/*、monitoring/*、ai/*）には実装上の詳細コメントがありますので、開発や運用にあたっては該当ファイルの docstring・コメントも参照してください。必要があればこの README に追記します。
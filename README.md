KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム健全性、注文状況、リスク（ドローダウン・ポジション数）を監視してアラート／Kill Switch を制御
- Research：DuckDB を用いたファクタ計算・特徴量解析モジュール
- AI：OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントやレジーム判定
- Portfolio：候補選定・重み計算・ポジションサイズ算出等の純関数群
- ユーティリティ群：ログ設定、プロセス優先度設定、設定ファイルウィザード、設定検証ツール 等

主な機能
--------
- 実運用向け ExecutionEngine（KABUSYS_ENV による動作モード切替）
  - development / paper_trading / live をサポート
  - paper_trading モードでは MockBrokerClient を使用し、本番 DB と完全に分離された data/paper_trading.db に記録
- 監視（Monitoring）
  - CPU / メモリ / ディスク使用率、Execution プロセス死活、データ鮮度を監視
  - 滞留注文・約定異常・ドローダウンなどの検出、Kill Switch（data/kill.flag）による自動停止
- AI モジュール
  - ニュースを集約して LLM（OpenAI）で銘柄ごとのセンチメントを算出して ai_scores に格納
  - マクロセンチメント + ETF MA 乖離で市場レジーム判定
- Research モジュール
  - DuckDB 上の歴史価格データからモメンタム / ボラティリティ / バリュー等のファクターを計算
  - 将来リターン・IC（Information Coefficient）計算等の分析ユーティリティ
- ツール
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）
- 設定管理
  - config_setup.py の対話ウィザードで .env を生成
  - validate_config.py で起動前に設定チェック（--strict オプションあり）

前提（Prerequisites）
--------------------
- Python 3.10+
- SQLite3（標準ライブラリ）
- 必要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- 推奨: 仮想環境（venv / poetry / pipenv 等）

簡単なセットアップ手順
--------------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係をインストール（requirements.txt がある場合はそれを利用）
   - 例（個別インストール）:
     - pip install duckdb psutil openai PyYAML

4. .env を作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザード終了後、.env が作成されます

   重要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABUSYS_ENV: 実行モード（development / paper_trading / live）デフォルト: development
   - DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading モード）
   - OPENAI_API_KEY: OpenAI を使う場合に必要
   - LOG_LEVEL / LOG_DIR: ロギング設定
   - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアする場合 1 を設定（本番では 0 推奨）
   - PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）

   例（.env 抜粋）
   JQUANTS_REFRESH_TOKEN=your_jquants_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   OPENAI_API_KEY=sk-...

5. 設定検証（任意／推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. （初回）DB は各起動スクリプトが自動で初期化します（monitoring のテーブル作成等）。

使い方（起動・実行）
-------------------

起動スクリプト
- ExecutionEngine を起動（本番/ペーパー/開発いずれもこれで起動）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に従います。
    - paper_trading の場合、MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に発注ログを記録します。
  - process priority を高優先で設定し、実行中は data/execution.pid に PID を書きます。
  - data/stop_requested.flag が存在する場合は起動・ループ中に検知して安全に停止します。

- Monitoring を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - 監視は常に production 相当の sqlite_path（Settings.sqlite_path）を使います
  - 停止は data/stop_requested.flag を作成するか Ctrl+C

停止／Kill Switch
- Kill Switch（自動停止）:
  - リスク条件（ドローダウン、ポジション上限等）に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - KillSwitch のパスは Settings.kill_flag_path で変更可能。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では推奨しません）。
- 強制終了フラグ（手動停止）:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了します。

ツール
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ライブラリ API（簡易）
- AI スコアリング（プログラム呼び出し例）
  - from kabusys.ai.news_nlp import score_news
  - duckdb 接続を作成し、score_news(conn, target_date, api_key=None) を呼ぶ（api_key が None の場合 OPENAI_API_KEY を参照）
- Research / Factor
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  - DuckDB 接続を渡して関数を呼ぶ（prices_daily / raw_financials テーブルが前提）

ロギング
- 共通ログ設定用ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
- デフォルトログ出力: stdout + 日次ローテートファイル logs/<app_name>.log（デフォルト 30 日保持）
- LOG_DIR 環境変数でログディレクトリを変更可能

設定ファイルの自動ロード
- プロジェクトルート（.git または pyproject.toml が存在する場所）を基準に .env/.env.local を自動読み込みします。
- 読み込み順: OS 環境 > .env.local > .env
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ディレクトリ構成（主要ファイル）
--------------------------------
以下はソースツリー（src/kabusys）を抜粋したものです。実際はプロジェクトルートに src/ があり、パッケージはそこに配置されています。

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数 / Settings 管理（.env 自動読み込み含む）
    - config_setup.py                # .env 対話ウィザード
    - validate_config.py             # 設定検証 CLI
    - run_execution.py               # ExecutionEngine 起動スクリプト
    - run_monitoring.py              # Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py # Paper Trading 検証レポート
    - utils/
      - logging_setup.py             # ログ設定ユーティリティ
      - process_priority.py          # プロセス優先度 / CPU affinity
    - execution/                      # Execution エンジン周辺（broker_factory 等）
      - (order_manager, repos, risk_manager, execution_engine 等)
    - monitoring/
      - monitoring_db.py             # monitoring DB ラッパー（SQLite）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - data/                            # 実行時生成: DB ファイル、flag、pid 等を格納する想定
      - monitoring.db (default)
      - paper_trading.db (paper モード)
      - kill.flag
      - stop_requested.flag
      - execution.pid
    - logs/                            # ログディレクトリ（自動生成推奨）

開発・運用時の注意
------------------
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 等の通知先や各種閾値を慎重に確認してください（validate_config は live 時に注意喚起を出します）。
- .env は決して Git にコミットしないでください（config_setup のヘッダにも警告があります）。
- DB マイグレーションやスキーマ変更は monitoring_db.init_monitoring_db などで冪等的に取り扱われるよう配慮されていますが、運用時はバックアップを推奨します。
- OpenAI 等外部 API を利用する処理はフェイルセーフ設計（エラー時にスコアをフォールバックする／処理をスキップする）になっていますが、API キー管理とレート制限に注意してください。

付録: よく使うコマンド一覧
------------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Python REPL からのモジュール実行例:
  - >>> from kabusys.ai.news_nlp import score_news
  - >>> # duckdb 接続を作って score_news(conn, date, api_key) を呼ぶ

---

この README はコードベースの主要な使い方・構成を説明するための概要です。より詳細な設計方針・アルゴリズムの説明は各モジュール内の docstring / コメントを参照してください。必要であれば、起動シーケンスや設定の例を追記した詳細ガイドを作成します。
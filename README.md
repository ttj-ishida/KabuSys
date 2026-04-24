README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主な目的は戦略の信号生成 → ポートフォリオ構築 → 注文発行 → 監視・リスク管理 を自動化することです。  
このリポジトリには、データ処理（DuckDB）、Execution エンジン（発注）、Monitoring（監視・Kill Switch）、研究用ユーティリティ、OpenAI を用いたニュース NLP などの機能が含まれます。

主な機能
--------
- ExecutionEngine（実行エンジン）
  - 本番/ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象（Mock/実ブローカー切替）
  - リスク管理（ポジション上限、ドローダウン等）
- Monitoring（監視）
  - システムリソース監視（CPU/MEM/DISK）
  - データ鮮度チェック（株価データの最新日）
  - 注文・約定ログ監視、滞留注文検出
  - Kill Switch（フラグファイルによる安全停止）
- ポートフォリオ構築（選定・重み付け・株数計算）
  - 等分配/スコア加重/リスクベース配分
  - セクター上限・レジームに応じた乗数
- 研究・分析（DuckDBベース）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン・IC 計算、統計サマリー
- AI 統合（OpenAI）
  - ニュースのセンチメントスコアリング（news_nlp）
  - 市場レジーム判定（regime_detector）
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト

前提・依存関係
--------------
主な Python ライブラリ（インストールが必要）
- python >=3.9（型注釈に Union|などを使用）
- duckdb
- psutil
- openai（AI 関連機能使用時）
- PyYAML（config YAML 検証時に推奨だが必須ではない）

pip install の例:
  pip install duckdb psutil openai pyyaml

重要ファイル/ディレクトリ（ランタイムで自動作成されることが多い）
- data/ : SQLite / PID / フラグファイルなど
  - data/kabusys.duckdb（DuckDB データベース、デフォルト）
  - data/monitoring.db（監視用 SQLite、デフォルト）
  - data/paper_trading.db（ペーパートレード用 SQLite、paper_trading 時）
  - data/kill.flag（Kill Switch）
  - data/execution.pid（ExecutionEngine 用 PID）
- logs/ : ログファイル（logs/<app_name>.log）

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant/partial/never/reject）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 利用時）
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリア（0/1）

セットアップ手順
---------------
1. リポジトリをクローンし Python 環境を用意
   - 推奨: venv や poetry を使用
2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
3. .env を作成
   - 対話式ウィザードで初期化:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を手動作成
   - 自動ロード: プロジェクトルートに .env / .env.local があれば自動で環境変数を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による無効化可）
4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 厳密モード（警告を FAIL にする）:
     python -m kabusys.validate_config --strict
5. データベース初期化は各スクリプトが必要に応じて実行します（monitoring は init_monitoring_db を呼ぶため基本的に自動で作成されます）

使い方（主要コマンド）
--------------------
- ExecutionEngine を起動（本番/ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - ペーパートレード時（KABUSYS_ENV=paper_trading）は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動せずに終了します。
  - ExecutionEngine は data/execution.pid に PID を書きます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - Monitoring は環境（KABUSYS_ENV）に関係なく settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
  - 停止は data/stop_requested.flag を作成するか Ctrl+C（KeyboardInterrupt）。

- 設定ウィザード（.env を対話で作成/更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルトの DB は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

- AI/ニューススコアリング（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY が設定されている必要あり。失敗時はフェイルセーフ（スコアなし等）で継続。

運用上の注意
-------------
- ペーパートレードモードは本番 DB と完全分離される（paper_sqlite_path を使用）。
- Monitoring は常に production sqlite_path を使用する点に注意。
- Kill Switch（data/kill.flag）を書き込むと ExecutionEngine は安全に停止します。KillSwitch は監視・リスク条件により自動で作成されます。
- ログ:
  - setup_logging により stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
  - LOG_DIR 環境変数でログディレクトリを変更可能。
- OpenAI を利用する機能は API の利用上限・エラーに対するリトライ実装を含みますが、API キー/課金設定は運用者の責任で管理してください。

ディレクトリ構成（抜粋）
----------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - data/                    — データ関連モジュール（DuckDB / パイプライン等）
  - execution/               — Execution エンジン周り（broker_factory, execution_engine 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

主なソースの役割（短縮）
-----------------------
- config.py: 環境変数の読み込み・検証・Settings クラス
- run_execution.py: エンジン起動、ブローカ生成、スレッド管理、DB接続
- run_monitoring.py: SystemMonitor をポーリングして監視処理を実行
- monitoring_db.py / MonitoringDB: 監視ログの永続化 API
- portfolio/*: ポートフォリオ構築とポジションサイズ計算の純粋関数群
- research/*: DuckDB を使ったファクター計算・解析
- ai/*: OpenAI を使ったニュースセンチメント・レジーム判定
- utils/*: ロギング設定、プロセス優先度設定など運用ユーティリティ

開発者向けメモ
---------------
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を検出して .env / .env.local を自動読み込みします。
  - OS 環境変数が優先され、.env.local は .env の上書きに使えます。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は必要なテーブルといくつかの簡易マイグレーション（カラム追加）を行います（冪等）。
- テスト時:
  - OpenAI 呼び出しは _call_openai_api をモック可能（unittest.mock.patch）に設計されています。

ライセンス・貢献
----------------
- 本 README にはライセンス情報は含まれていません。実際の配布時には LICENSE ファイルを追加してください。  
- バグ報告・機能提案は Issue を通じてお願いします。

以上。初期セットアップについて不明点があれば、動かしたいコンポーネント（Execution / Monitoring / AI / PaperReport など）を指定していただければ、より具体的な手順を示します。
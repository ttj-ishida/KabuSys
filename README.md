KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株自動売買・バックテスト・リサーチを想定した小〜中規模のシステム群です。  
主な目的は以下です。
- 注文実行エンジン（ExecutionEngine）による発注／リスク管理（本番／ペーパートレード対応）
- システム監視（Monitoring）・リスク検知・Kill Switch
- ファクター計算・リサーチ用ユーティリティ（DuckDB ベース）
- ニュース NLP / レジーム判定（OpenAI API 利用）
- ペーパートレード検証レポート生成ツール 等

設計の特徴:
- 設定は .env により管理（config_setup による対話式作成を推奨）
- paper_trading 環境では本番 DB と完全分離（別 SQLite を使用）
- DuckDB を分析用に利用、SQLite を監視／ログ用に利用
- OpenAI を用いた NLP モジュールは APIキーで動作（任意）

主な機能一覧
---------------
- Execution
  - 実際のブローカーまたは MockBrokerClient（KABUSYS_ENV=paper_trading）でのセッション実行
  - 注文管理、リスクマネジメント、再調整（reconciler）等
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - system_status / trade_logs / risk_logs / dashboard テーブルによる永続化
  - Kill Switch（条件を満たすと data/kill.flag を作成してエンジン停止を促す）
- Portfolio モジュール
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ・レジーム乗数
- Research
  - ファクター計算（momentum, volatility, value など）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - news_nlp: raw_news を OpenAI でセンチメント評価し ai_scores に書き込み
  - regime_detector: ETF ma200 乖離 + マクロニュースで市場レジーム判定
- ツール
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）
- 設定・検証
  - 対話式 .env 作成（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）

システム要件（想定）
-------------------
- Python 3.10+
- 依存パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite（標準ライブラリで利用可能）

セットアップ手順
----------------
1. リポジトリをクローン:
   - git clone <repo-url>
2. 仮想環境を作成して有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合の例）:
   - pip install duckdb psutil openai
   - （開発用）pip install PyYAML
4. 対話式に .env を作成:
   - python -m kabusys.config_setup
   - ウィザードで J-Quants / kabuAPI / DB パス 等を対話的に設定します
5. 設定を検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる
6. データディレクトリなどを準備（必要に応じて）:
   - デフォルトの DB / ログパス: data/monitoring.db, data/kabusys.duckdb, logs/

主な環境変数とデフォルト
-----------------------
（.env に記載または環境に設定）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用 DB
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG/INFO/...) — デフォルト: INFO
- LOG_DIR (デフォルト: logs/)
- OPENAI_API_KEY — AI モジュールを使う場合に必要
- PAPER_FILL_MODE (instant | partial | never | reject) — ペーパートレードの約定挙動
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（主要コマンド）
---------------------
- 対話式設定 (.env 作成)
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動（バックグラウンドで pid ファイルを作成）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます
  - エンジン停止は data/stop_requested.flag（または Kill Switch により data/kill.flag）で制御
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒）
  - 監視は常に production（設定にかかわらず sqlite_path を使用）を前提に動作
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - --from / --to で期間を指定、--db で DB パスを指定可能
- AI 系（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY を環境変数または明示的な api_key 引数で指定

監視・停止フローの注意点
------------------------
- Kill Switch:
  - RiskMonitor が条件を満たすと KillSwitch が data/kill.flag を作成します。
  - ExecutionEngine は起動時に kill.flag の存在をチェックし、存在する場合は起動を中止します。
  - Kill flag は clear() で削除可。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアされます（本番では 0 推奨）。
- stop_requested.flag:
  - run_execution/run_monitoring は data/stop_requested.flag の存在をチェックしてループを終了します（外部からの停止指示に利用）。
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力されます（LOG_DIR で変更可能）。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定読み込みロジック
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

modules/
- execution/                — ExecutionEngine, OrderManager, BrokerFactory 等（発注ロジック）
- monitoring/
  - monitoring_db.py        — SQLite テーブル初期化・永続化層
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

（ファイルは src/kabusys 以下に配置。README のコード参照は上記のスクリプトで説明した挙動に基づきます）

開発・デバッグのヒント
---------------------
- config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードします。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring の DB 初期化は init_monitoring_db() で冪等に行われます。既存スキーマに対する簡易マイグレーション（カラム追加）を含みます。
- OpenAI 呼び出し部はリトライや JSON バリデーションを備えていますが、API の仕様変更やレスポンスの揺らぎには注意してください。
- psutil を使ってプロセス優先度や CPU affinity を設定するため、権限不足で警告になる場合があります（問題なければ実行継続します）。

ライセンス・貢献
----------------
- 本リポジトリに付与されているライセンスファイルを参照してください（ここに明記がない場合はリポジトリの LICENSE を確認してください）。
- バグ報告・プルリクは歓迎します。まず Issues で相談してください。

以上がこのリポジトリの概要・セットアップ・基本的な使い方です。追加で「各モジュールの API ドキュメント」や「実運用時のデプロイ手順（systemd / supervisor など）」のテンプレートが必要であれば作成します。どの部分を詳しく知りたいか教えてください。
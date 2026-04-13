KabuSys — 日本株自動売買システム
==============================

この README はリポジトリに含まれる主要モジュールと実行・設定方法をまとめたドキュメントです。コードベースは、自動売買の実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）など複数コンポーネントで構成されています。

要約（Project overview）
------------------
KabuSys は日本株自動売買のためのモジュール群です。主な役割は次の通りです。
- 注文管理・ブローカー連携（ExecutionEngine、OrderManager、OrderRepository 等）
- 取引監視・システム監視（MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制限など）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- AI サービス（ニュースを LLM でスコア化する news_nlp、マーケットレジーム判定）
- 運用ツール（paper trading レポート、Streamlit ダッシュボード等）

主な特徴（Features）
------------------
- 実行・監視を分離：Execution と Monitoring は別 DB を使って分離可能（paper_trading モードでは完全に別 DB に記録）。
- 冪等・耐障害設計：監視 DB 初期化は冪等、Execution の再同期（Reconciler）機能あり。
- AI を組み込んだ情報収集：OpenAI（gpt-4o-mini）でニュースセンチメントやマクロセンチメントを算出。部分失敗時も安全に処理継続。
- portfolio モジュールは純粋関数群（副作用なし）でユニットテストしやすい設計。
- Streamlit による監視ダッシュボード、紙トレード検証用レポート生成スクリプトなど運用用ツールを提供。
- OS 間互換のプロセス優先度設定・CPU affinity ユーティリティ（psutil ベース）。

セットアップ手順（Setup）
------------------
前提
- Python 3.10 以上（型注釈に PEP 604 の | を使用しているため）
- SQLite（組み込み）／DuckDB（duckdb Python パッケージ）を使用
- ネットワークアクセス：ブローカー API、OpenAI、LINE（通知）を利用する場合はそれぞれのネットワークアクセスと API キーが必要

依存パッケージ（代表例）
- duckdb
- psutil
- requests
- openai
- streamlit
- （必要に応じて）pytest などのテストツール

例: pip でインストール
- 仮想環境を作成して有効化後:
  - pip install duckdb psutil requests openai streamlit

設定（環境変数）
- 設定は主に環境変数またはプロジェクトルートの .env / .env.local から読み込みます。
- 自動ロードは Settings モジュールで行われ、OS 環境変数が優先されます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（デフォルト・意味）
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject、デフォルト "instant"）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill フラグファイル（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知使用時に設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔秒（デフォルト: 60）

（.env の例）
例として .env に次を置けます（実運用では secrets 管理を推奨）:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=paper_trading
PAPER_FILL_MODE=instant
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb

使い方（Usage）
------------------

1. 監視ループ起動（Monitoring）
- スクリプト: src/kabusys/run_monitoring.py
- 実行例:
  - python -m kabusys.run_monitoring
- 環境変数:
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。例: MONITOR_POLL_INTERVAL=30
- 注意:
  - Monitoring は KABUSYS_ENV に関係なくデフォルトの sqlite_path（SQLITE_PATH）を使用します（監視データは本番 DB を参照）。

2. 実行エンジン起動（Execution）
- スクリプト: src/kabusys/run_execution.py
- 実行例:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。paper_trading と本番 DB は分離されます。
- 注意:
  - 起動時にプロセス優先度を high に設定します（psutil によって可能な限り適用）。

3. Paper Trading 検証レポート生成
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- 出力: 標準出力に期間ごとの稼働率、注文成功率、レイテンシなどのサマリを出力し、PASS/FAIL を判定します。

4. Streamlit 監視ダッシュボード
- ファイル: src/kabusys/monitoring/streamlit_dashboard.py
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 注意: MonitoringEngine が監視 DB を生成していない場合は read-only オープンに失敗します（起動前に監視プロセスを開始してください）。

5. AI 機能（ニューススコア、レジーム判定）
- programmatic API:
  - kabusys.ai.score_news(conn, target_date, api_key=None) — raw_news から銘柄別センチメントを ai_scores テーブルへ書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — マクロセンチメントと ETF ma200 を合成して market_regime に書き込む
- 必要: OpenAI API キー（引数あるいは環境変数 OPENAI_API_KEY）

主要モジュールの説明
------------------
- kabusys.config
  - Settings クラス: 環境変数読み込み・バリデーション・デフォルト管理。プロジェクトルートの .env / .env.local を自動ロード（必要に応じて無効化可能）。
- kabusys.execution
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler: 注文作成・送信・同期・起動時のリコンシリエーションなどを実装。
- kabusys.monitoring
  - MonitoringDB: SQLite による監視ログ永続化（テーブル初期化・マイグレーション対応）。
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / AlertManager / KillSwitch: システム状態監視、注文滞留・約定異常検出、リスク監視、アラート通知（LINE）、Kill フラグの生成など。
  - streamlit_dashboard: 監視情報の可視化。
- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment: 候補選定、重み付け、ポジションサイズ算出、セクターキャップ、レジーム乗数などの純粋関数群。
- kabusys.research
  - factor_research, feature_exploration: モメンタム/ボラティリティ/バリューファクター、将来リターン、IC、統計サマリなど（DuckDB を利用）。
- kabusys.ai
  - news_nlp: ニュース記事を OpenAI でスコア化するロジック。バッチ処理・再試行・レスポンス検証・書き込みを実装。
  - regime_detector: ETF MA とマクロセンチメントを合成して日次レジーム判定を行う。
- kabusys.utils
  - process_priority: OS 間の差を吸収したプロセス優先度と CPU affinity 設定。

ディレクトリ構成（Directory structure）
------------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 execution 関連ファイル: broker_factory, execution_engine, order_repository, order_record, etc.)
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
    - data/
      - pipeline.py (参照元あり)
    - utils/
      - __init__.py
      - process_priority.py

運用上の注意（Notes / Best practices）
------------------
- Paper trading と live は DB を分離するため、誤って本番資金に注文を出さないよう環境変数 KABUSYS_ENV を正しく設定してください。
- OpenAI を利用する機能は、API 失敗時にフォールバックを行う実装ですが、API キー漏洩に注意してください。
- kill.flag（デフォルト data/kill.flag）を作成すると ExecutionEngine 停止のためのシグナルになります。Monitoring 側から自動で書き込まれる場合があります。起動オプションにより起動時にクリアする挙動（KILL_FLAG_CLEAR_ON_START）を設定できます。
- ログレベルは LOG_LEVEL 環境変数で変更できます。運用時に DEBUG を常に有効にしないことを推奨します。

よくあるコマンド例
------------------
- 監視ループを 30 秒間隔で起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution を paper_trading で起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper トレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ライセンス・貢献
------------------
この README に含まれるコードの利用ルールやライセンスは本リポジトリの LICENSE を参照してください。バグ報告・改善提案は issue / PR を送ってください。

問い合わせ
------------------
実行方法や設定で不明点があれば具体的な環境（OS、Python バージョン、.env の主要設定）と共に質問してください。必要に応じて、主要なログ出力やエラートレースを添付してください。

以上です。必要があれば、README にサンプル .env.example（完全版）や requirements.txt の候補、起動スクリプトの systemd ユニット例なども追加します。どれを追加しますか？
KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視ユーティリティ群を提供する小規模なプロジェクトです。本リポジトリには以下の機能が含まれます（概略）:

- 発注・注文管理 (ExecutionEngine, OrderManager, Reconciler)
- リスク管理・監視 (RiskMonitor, TradeMonitor, SystemMonitor, MonitoringEngine)
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- リサーチ機能（ファクター計算、特徴量探索）
- AI を使ったニュースセンチメント / レジーム判定（OpenAI を利用）
- Paper Trading 用の検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

主な設計方針:
- データ処理は DuckDB / SQLite を想定（ローカル DB による計算・永続化）
- 実口座と Paper Trading は DB 分離（paper_trading モードは data/paper_trading.db を使用）
- LLM 呼び出しはフェイルセーフ（API エラー時はデフォルト値で継続）
- ルックアヘッドバイアスに配慮（target_date を引数で与える設計）

機能一覧
--------
主な機能（モジュール別）:

- execution
  - OrderManager: 注文作成・送信の上位 API
  - Reconciler: 再起動時のブローカー照合・ポジション差分チェック
  - BrokerFactory: live / paper_trading 切替
- monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常検知
  - RiskMonitor: ドローダウン・ポジション数監視
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル
  - AlertManager: LINE push によるアラート送信（オプション）
  - MonitoringEngine: 上記を束ねるポーリングエンジン
  - streamlit_dashboard: 監視データ可視化用 UI
- portfolio
  - 銘柄選定、等重/スコア重み配分、リスク調整、ポジションサイズ算出
- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算、統計サマリー
- ai
  - news_nlp: ニュースを LLM（OpenAI）でスコアリングして ai_scores に保存
  - regime_detector: MA200 とマクロニュースで市場レジーム判定
- tools
  - paper_verification_report: Paper Trading DB の検証レポートを生成

セットアップ手順
----------------

前提
- Python 3.10 以上（PEP 604 の型表記（X | Y）などを使用）
- システムに DuckDB、psutil 等のネイティブ依存が入る場合あり

推奨手順（ローカル）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトで requirements.txt を用意している場合は pip install -r requirements.txt を利用）

3. プロジェクトルートに .env / .env.local を配置して環境変数を設定（自動ロード機能あり）
   - デフォルトでは .env をプロジェクトルートから読み込みます（.git または pyproject.toml をルート判定）
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主要な環境変数（抜粋）
- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
  - paper_trading 時は MockBrokerClient を使用し DB を data/paper_trading.db に分離
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- OPENAI_API_KEY: OpenAI API キー（ai 機能を使う場合必須）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行プロセスの PID / kill flag ファイルパス
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

例 (.env)
    KABUSYS_ENV=paper_trading
    OPENAI_API_KEY=sk-...
    SQLITE_PATH=data/monitoring.db
    DUCKDB_PATH=data/kabusys.duckdb
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    LOG_LEVEL=INFO

使い方
------

コマンドライン実行（モジュールとして）

- 監視ループ (SystemMonitor を単独で動かす簡易スクリプト)
  - python -m kabusys.run_monitoring
  - 環境変数: MONITOR_POLL_INTERVAL（秒。デフォルト 60）
  - 起動時にプロセス優先度を High に設定し、監視データを sqlite に書き込む

- 実行エンジン (ExecutionEngine 起動)
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると mock ブローカーを使用し data/paper_trading.db に記録
  - 起動時に process priority 設定・DB 初期化・依存コンポーネントを組み立てて run_session を呼ぶ

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを上書き可能（PAPER_TRADING_SQLITE_PATH 環境変数も使用可）
  - 出力は標準出力に整形されたレポートを出力。稼働率・注文成功率・レイテンシ等を評価

- Streamlit ダッシュボード (監視 UI)
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を開き、Dashboard / Positions / Orders / System 情報を表示

- AI（ニュース / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼ぶ
  - 事前に OPENAI_API_KEY を設定すること
  - OpenAI API の呼び出しは外部通信になるためレート制限・課金に注意

運用上のポイント
- PID / Kill flag:
  - ExecutionEngine は起動時に pid ファイル（Settings.pid_file_path）を書き、KillSwitch は kill.flag を filesystem に書くことで停止要求を伝えます
  - Settings.kill_flag_clear_on_start を使って起動時に既存の kill.flag を削除する設定があります
- 監視 DB:
  - monitoring_db.init_monitoring_db() で必要なテーブルを作成します（冪等）
  - 主要テーブル: system_status, trade_logs, positions, risk_logs, dashboard
- Paper Trading:
  - 本番 DB と完全分離されるため、紙上での検証に安全（KABUSYS_ENV=paper_trading を使用）

ディレクトリ構成
----------------

以下は主要ファイル・モジュールの構成（src/kabusys 以下の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - run_monitoring.py            — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite 永続化層（テーブル作成・読み書き API）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository, order_record など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (想定されるデータディレクトリ)
    - kabusys.duckdb (DuckDB ファイル)
    - monitoring.db / paper_trading.db (SQLite)

README 補足 / Tips
------------------
- 開発時は KABUSYS_ENV=development を使い、環境変数は .env.local に置くと便利です。
- AI 機能は OpenAI の API キーが必要です。テスト時はモック (_call_openai_api を unittest.mock.patch) して単体テストを行う設計になっています。
- process priority / CPU affinity の設定はプラットフォーム依存です。権限がない場合は警告でスキップされます。
- DuckDB / SQLite への書き込みはスキーマの互換性を保つためマイグレーション的なチェック（カラム追加）を行っています。

ライセンス / 貢献
-----------------
（この README にはライセンス情報を含めていません。適宜 LICENSE を追加してください。）

最後に
------
本 README はコードベースの主要な使い方・構成をまとめたものです。実際の運用やデプロイ時はログ設定、バックアップ、モニタリングのしきい値、安全停止手順（kill.flag）等を十分に設計してください。質問や補足があれば教えてください。
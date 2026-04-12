README
======

概要
----
KabuSys は日本株の自動売買を想定した小型の取引自動化フレームワークです。売買実行（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、研究（ファクター計算 / 特徴量探索）、AI を使ったニュースセンチメント／市場レジーム判定などのコンポーネントを備えています。設計上、実行ロジックはブローカー抽象化層を通じて分離され、Paper Trading モードでは本番 DB と完全に分離された SQLite を使って安全に検証できます。

主な特徴
--------
- ExecutionEngine（発注・リスク管理・リコンシリエーション）
  - ブローカー・クライアント抽象化（実ブローカー / モックを切替）
  - 再起動時の注文突合（Reconciler）
  - RiskManager による各種制約（ポジション上限・ドローダウン等）
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態、データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション数監視と kill.flag 発行
  - AlertManager: LINE へのプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（簡易 UI）
- Portfolio construction
  - 候補選定・等配分／スコア加重配分・リスクベースのポジションサイジング
  - セクター集中制限・レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・統計サマリ
- AI（OpenAI 経由）
  - ニュースセンチメント（銘柄別 ai_scores 生成）
  - 市場レジーム判定（ETF ma200 とマクロセンチメントの合成）
- ツール
  - Paper Trading の検証レポート出力スクリプト
  - 各種ユーティリティ（プロセス優先度設定等）
- 設定管理
  - .env / 環境変数から設定を読み込み（自動読み込みを無効化可）

前提条件
--------
- Python 3.9+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- SQLite（標準で Python に内包）

インストール（ローカル開発向け）
-------------------------------
1. リポジトリをクローンして、プロジェクトルートに移動します。
2. 仮想環境を作成・有効化し、依存関係をインストールします（例）:

   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb psutil requests openai streamlit

3. 環境変数は .env / .env.local / OS 環境変数から読み込みます（自動でプロジェクトルートの .env を探します）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN：J-Quants API 用（必須）
- KABU_API_PASSWORD：kabuステーション API のパスワード（必須）
- OPENAI_API_KEY：OpenAI API キー（AI 機能利用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID：LINE 通知用（任意）
- KABUSYS_ENV：動作モード。development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
  - live: 本番運用モード
- PAPER_FILL_MODE（paper_trading 時の約定挙動）: instant | partial | never | reject（デフォルト: instant）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- DUCKDB_PATH（リサーチ用 DuckDB、デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH（ExecutionEngine の PID ファイル、デフォルト: data/execution.pid）
- KILL_FLAG_PATH（kill flag、デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト: 60）

セットアップ（初期 DB 作成等）
----------------------------
- 監視 DB（SQLite）や DuckDB は起動スクリプト側で必要なテーブルを自動作成 / マイグレーションします（init_monitoring_db）。
- デフォルトの DB パスは data/ 以下にあるため、権限がない場合は適宜パスを変更してください。

使い方（実行方法）
-----------------

1) 監視ループを起動（Monitoring）
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
- 実行:

  python -m kabusys.run_monitoring

  (補足) KABUSYS_ENV に依らず monitoring は本番 sqlite_path（SQLITE_PATH）を使います。

2) ExecutionEngine を起動（発注実行）
- paper_trading モードを使う場合は KABUSYS_ENV=paper_trading を設定してください（この場合は MockBrokerClient を使用し、paper_trading 用の DB に記録されます）。
- 実行:

  # 本番 / dev（実際のブローカークライアントを使用）
  python -m kabusys.run_execution

  # Paper Trading
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  (補足) ExecutionEngine 起動時に PID ファイルを作成し、kill.flag による停止シグナルを監視します。Settings.kill_flag_clear_on_start を設定すると起動時に flag をクリアできます。

3) Paper Trading 検証レポート（コマンドライン）
- usage:

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- デフォルト DB パス: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

4) Streamlit 監視ダッシュボード
- 実行:

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ダッシュボードは読み取り専用で監視 DB を表示します。MonitoringEngine を先に起動してデータを生成してください。

5) AI 機能（プログラムから）
- ニュースセンチメント:

  from kabusys.ai.news_nlp import score_news
  # duckdb_conn は duckdb.connect(...) で取得
  score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")

- 市場レジーム判定:

  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")

注意点 / オペレーション情報
----------------------------
- Settings は起動時に .env / .env.local を自動ロードします（OS 環境変数が優先）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Process priority: 起動スクリプトは set_process_priority("high") を呼び出してプロセス優先度を上げようとします（psutil を使用）。アクセス権限がない場合は警告ログになりスキップされます。
- kill.flag: KillSwitch はリスク条件を満たした場合に data/kill.flag を作成し、ExecutionEngine の停止を促します。既存の flag があれば上書きしません。
- Paper Trading モードでは紙上の約定挙動（PAPER_FILL_MODE）を制御できます（instant/partial/never/reject）。
- DuckDB を用いたリサーチ用クエリは prices_daily / raw_financials / raw_news 等のテーブルを想定しています。これらは別途 ETL で準備してください。

ディレクトリ構成
---------------
以下は主要モジュールとファイルの一覧（抜粋）と簡単な説明です。

- src/kabusys/
  - __init__.py
    - パッケージメタ情報（バージョン等）
  - config.py
    - 環境変数 / .env の読み込み、Settings クラスによる設定管理
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker 使用）
  - utils/
    - process_priority.py
      - psutil を使ったプロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py
      - SQLite ベースの監視テーブル定義と MonitoringDB クラス（読み書き）
    - system_monitor.py
      - CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py
      - 注文滞留・約定価格異常検出
    - risk_monitor.py
      - ドローダウン・ポジション上限等の監視とダッシュボード更新
    - kill_switch.py
      - flag ファイルを書いて ExecutionEngine 停止を指示
    - alert_manager.py
      - LINE へのプッシュ通知（クールダウン管理）
    - monitoring_engine.py
      - 各モニターをまとめてポーリングするエンジン
    - streamlit_dashboard.py
      - Streamlit を使った簡易監視ダッシュボード
  - execution/
    - order_manager.py
      - 発注の作成 / 送信 / 同期などのロジック（OrderManager）
    - reconciler.py
      - 起動時の注文・ポジション再突合（Reconciler）
    - （その他ブローカー関連、order_repository 等は本リポジトリに含まれる想定）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・配分計算（等配分 / スコア配分）
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
    - position_sizing.py
      - 実際の株数計算・単元丸め・資金割当
  - research/
    - factor_research.py
      - Momentum / Volatility / Value ファクター計算（DuckDB を利用）
    - feature_exploration.py
      - 将来リターン計算・IC・統計サマリー
  - ai/
    - news_nlp.py
      - raw_news を用いた銘柄別ニュースセンチメント生成（OpenAI）
    - regime_detector.py
      - マクロニュース + ETF MA200 を合成して市場レジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py
      - Paper Trading DB から検証レポートを生成する CLI スクリプト

ライセンス / 貢献
-----------------
- （ここにライセンス情報と貢献方法を記載してください。リポジトリ固有のポリシーに従ってください）

補足（トラブルシュート）
-----------------------
- DB が開けない / テーブルがない:
  - run_monitoring / run_execution の起動で init_monitoring_db が自動実行されます。手動で DB を作る必要は原則ありませんが、権限やパスを確認してください。
- OpenAI 関連でエラーが多い場合:
  - API キーの有効性、レート制限、ネットワークを確認してください。news_nlp/regime_detector はリトライとフォールバック（失敗時の安全値）を持ちますが、キー未設定だと例外になります。

以上。必要であれば README にサンプル .env.example、より詳細な起動フロー図、API ドキュメント（OrderRequest / BrokerAPIProtocol 等）の追加を行えます。どの項目を拡張しますか？
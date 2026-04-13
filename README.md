KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買／研究／監視を目的とした小規模なシステム群です。  
このリポジトリには、実行エンジン、監視エンジン、ポートフォリオ構築ロジック、ファクター計算、LLM を用いたニュースセンチメント／レジーム判定、検証ツール類が含まれます。  
設計方針として「本番データと検証（Paper Trading）を分離」「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的に制御／フェイルセーフ化」を重視しています。

主な機能
--------
- 実行エンジン起動スクリプト（run_execution）  
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）へ記録して本番と分離。
  - OrderManager / RiskManager / Reconciler による注文管理・再同期機能を備える。
- 監視（Monitoring）  
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine によるポーリング監視。
  - システム状態・滞留注文・約定異常・ドローダウン等の検出とログ保存（SQLite）。
  - LINE Push によるアラート送信（AlertManager）。
  - kill.flag による ExecutionEngine 停止シグナル生成（KillSwitch）。
  - Streamlit ダッシュボードで監視情報可視化（streamlit_dashboard.py）。
- 研究（Research）  
  - ファクター計算（モメンタム / ボラティリティ / バリュー） — DuckDB を利用し prices_daily, raw_financials などから計算。
  - 将来リターン・IC（Information Coefficient）計算、特徴量サマリー。
- ポートフォリオ構築（Portfolio）  
  - シグナル選別、等配分／スコア加重配分、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ計算（単元株丸め）等の純粋関数群。
- AI（OpenAI）連携  
  - news_nlp: ニュース記事を LLM（gpt-4o-mini）でスコアリングして ai_scores に書き込み。
  - regime_detector: ETF の MA200 乖離とマクロニュースの LLM 評価を合成して当日の市場レジーム判定。
  - API 呼び出しはリトライ・バックオフ・バリデーション等のフェイルセーフ実装あり。
- 検証ツール  
  - paper_verification_report: Paper Trading DB を読み取り稼働率／注文成功率／レイテンシ等を集計して検証レポートを生成。

セットアップ
----------
前提（例）
- Python 3.9+（プロジェクトで厳密な指定がある場合はそちらに従ってください）

1. リポジトリをクローンし仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストール（requirements.txt がある場合はそれを使用）
   例（プロジェクトに合わせて調整してください）:
   - pip install duckdb psutil requests openai streamlit

3. データディレクトリを作成
   - mkdir -p data

4. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
       - paper_trading: 実行エンジンは MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込みます。
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...  # news_nlp / regime_detector を使う場合必須
     - LINE_CHANNEL_ACCESS_TOKEN=... （LINE 通知を有効にする場合）
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db  # 監視ログ DB（monitoring は環境に関係なくこのパスを使用）
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - MONITOR_POLL_INTERVAL=60  # run_monitoring のポーリング間隔（秒）
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag

5. （初回）DB はスクリプト起動時に必要テーブルが自動作成されます（init_monitoring_db を利用）。

使い方（主要スクリプト）
---------------------
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 補足: KABUSYS_ENV=paper_trading のときは paper_trading 用 DB に記録し本番 DB と分離します。

- 監視ループ起動（SystemMonitor の単独起動）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は monitoring DB（settings.sqlite_path）を利用します（KABUSYS_ENV に依らず本番 sqlite_path を使用）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用モードで SQLite DB を開き、Overview / Positions / Orders / System タブで確認できます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB は --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）で指定。

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  # api_key を渡すか環境変数 OPENAI_API_KEY を設定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意事項 / 動作ポリシー
---------------------
- .env の自動ロード
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env, .env.local を自動読み込みします。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading 分離
  - paper_trading モードは実際のブローカーに注文を送らない（MockBrokerClient）ことを前提にしており、データは data/paper_trading.db に分離されます。
- OpenAI の呼び出し
  - news_nlp と regime_detector は OpenAI（gpt-4o-mini）を利用します。API キーが未設定だとエラーまたはフォールバック（多くはスコア 0.0）となります。大量呼び出しではレート制限や料金に注意してください。
- プロセス優先度 / CPU affinity
  - 起動スクリプトは set_process_priority("high") を呼び出します。プラットフォームにより設定できない場合は警告を出してスキップします。
- kill.flag / PID ファイル
  - ExecutionEngine の PID ファイルを用いて監視側がプロセス生存を確認します。KillSwitch は data/kill.flag ファイルを書き込むことで ExecutionEngine に停止を促します。起動時にフラグをクリアする設定も可能です。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ初期化
- config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite スキーマ定義・永続化 API（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 制御
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・投下資金制限
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- execution/
  - order_manager.py — 注文作成・送信ロジック
  - reconciler.py — 起動時の再同期ロジック
  - （ブローカーインタフェース等は関連ファイルに実装）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート出力ツール
- utils/
  - process_priority.py — プラットフォーム差分を吸収したプロセス優先度設定ユーティリティ

追加の補足
--------
- DB マイグレーション / スキーマ
  - monitoring_db.init_monitoring_db() は起動時にテーブルと必要なカラムを冪等的に作成／追加します。
- ロギング
  - 各スクリプトは logging.basicConfig(level=logging.INFO) で基本ログを出力します。LOG_LEVEL 環境変数は Settings.log_level で取得できます。
- テストと CI
  - 各モジュールは純粋関数化が進められているためユニットテストを書きやすい設計です。OpenAI 呼び出しなど外部依存は差し替え可能（モック可能）に実装されています。

ライセンス / 貢献
-----------------
- 本 README はコードベースの説明を目的としています。実際の運用・商用利用の際はライセンス条項、API 利用規約、金融法規制に注意してください。

必要であれば以下も作成できます:
- .env.example のテンプレート
- requirements.txt（依存ピン留め）
- 実行フロー図 / シーケンス図
- より詳しい運用手順（デプロイ / systemd / コンテナ化 など）

質問や補足したい箇所があれば教えてください。README の調整や追加セクション（例: 環境変数の詳細テーブルやデプロイ手順）も作成します。
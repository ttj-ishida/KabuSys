# KabuSys

日本株向けの自動売買 / 研究・監視基盤の軽量実装です。本リポジトリは以下の主要機能群を含みます: 発注実行エンジン、監視（Monitoring）サブシステム、ポートフォリオ構築ユーティリティ、リサーチ（ファクター計算・特徴量解析）、AI を使ったニュースセンチメント評価など。

バージョン: 0.1.0

---

プロジェクトの目的・想定用途
- 日本株の自動売買システム（Kabuステーション等のブローカー API と連携）を模した構成を提供
- Paper Trading（本番環境と分離した模擬発注）をサポート
- DuckDB を用いた時系列データ処理（ファクター計算等）
- 監視コンポーネントにより稼働状態・注文の異常・リスクを検出し LINE で通知可能
- OpenAI を使ったニュース NLP によるセンチメント集計、レジーム判定などの補助機能

含まれる主なモジュール（機能一覧）
- execution: 発注周りのロジック（OrderManager, ExecutionEngine, Reconciler 等）
- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor（システム状態・注文滞留・ドローダウン等の監視）
  - MonitoringDB（SQLite 経由の永続化）
  - AlertManager（LINE Push 通知）
  - KillSwitch（flag ファイルによる停止トリガー）
  - streamlit_dashboard（監視ダッシュボード）
- portfolio: 候補選定、重み計算、ポジションサイジング、セクター制約・レジーム調整
- research: ファクター計算（momentum/value/volatility）、将来リターン・IC 計算等
- ai:
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのスコアを ai_scores に格納
  - regime_detector: 市場レジーム判定（ETF MA + マクロセンチメント合成）
- tools:
  - paper_verification_report: Paper Trading の検証レポート生成スクリプト

重要な挙動（運用上のポイント）
- Settings は .env / .env.local / OS 環境変数からロード（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）
  - paper_trading の場合、発注は MockBrokerClient を使い、Paper Trading 用 DB（デフォルト data/paper_trading.db）に記録され、本番 DB と完全に分離されます
- 監視（Monitoring）は環境に依らず本番 sqlite_path を使用して永続化します
- 実行スクリプトは起動時にプロセス優先度を「high」に設定しようとします（プラットフォーム制約あり）
- Kill / Stop フラグ:
  - data/kill.flag: ExecutionEngine に停止を促すための flag（KillSwitch により生成）
  - data/stop_requested.flag: run_monitoring / run_execution が監視している停止フラグ（存在するとループを終了）

セットアップ手順（概略）
1. リポジトリをクローン
   - git clone ...

2. Python 環境作成
   - Python 3.10+ を推奨
   - 仮想環境作成・有効化例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit
   - （requirements.txt がある場合は pip install -r requirements.txt を使用）

4. 環境変数の設定
   - プロジェクトルートに .env を作成するか、OS 環境変数で設定してください。
   - 主要な環境変数:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - JQUANTS_REFRESH_TOKEN — 必須（Settings.jquants_refresh_token）
     - KABU_API_PASSWORD — 必須（kabu ステーション API 用）
     - OPENAI_API_KEY — AI 機能を使う場合に必要
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート送信に使用（未設定でも動作するが通知はスキップ）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring が参照。デフォルト 60）

5. データディレクトリ作成
   - data/ 以下に DB や pid / flag ファイルが作られます。必要に応じて書き込み権限を確認してください。

使い方（主要スクリプト）
- 監視ループを起動（production 用の monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更できます（秒）
  - 停止するには data/stop_requested.flag を作成するか Ctrl+C

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB に記録されます
  - data/stop_requested.flag を作成するとエンジンが停止します
  - 実行中は data/execution.pid に PID を書きます

- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既存の monitoring.db を読み取り専用で開きます（モニタリングが先に起動している必要があります）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH も使用可）

- AI 機能（ニューススコアリング / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出す形で使用
  - OPENAI_API_KEY が必要。API 呼び出しはリトライ・フェイルセーフ処理済み

設定の注意点
- 自動で .env をロードします（プロジェクトルートの検出: .git または pyproject.toml を基準）
  - テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- Settings クラスで各種の妥当性チェック・デフォルトが実装されています（PAPER_FILL_MODE の検証、KABUSYS_ENV の許容値など）
- 監視 DB（SQLite）は init_monitoring_db によってテーブル作成／マイグレーションが行われます。初回起動時に自動で準備されます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env ロード機構含む）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - execution/
    - broker_api.py, broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, order_record.py, ...（発注関連）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py, trade_monitor.py, risk_monitor.py
    - monitoring_engine.py, kill_switch.py, alert_manager.py, streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - ai/
    - news_nlp.py, regime_detector.py
  - data/（実行時に生成される。DB や pid/flag ファイルを格納）
    - data/monitoring.db（デフォルト） / data/paper_trading.db / data/kabusys.duckdb
    - data/execution.pid, data/kill.flag, data/stop_requested.flag

設計・実装上のポイント（簡潔）
- 多くのモジュールは「副作用を持たない純粋関数」や「DB 接続を受け取る設計」を採用しており、テスト容易性を考慮
- AI（OpenAI）呼び出しは冪等性とリトライ、レスポンス検証を重視して実装
- Monitoring 系は監視結果を監視 DB に永続化し、AlertManager 経由で LINE に通知可能
- Paper Trading は本番 DB と分離し、テスト検証を容易にする

よくある運用上の操作
- 監視停止（Graceful）
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して終了します
- 強制停止（Kill Switch）
  - KillSwitch が条件を満たした場合、data/kill.flag を作成して ExecutionEngine に停止指示を送ります
- PID 管理
  - run_execution は data/execution.pid を作成します。SystemMonitor はこの PID の生存確認を行い stale PID を検出するとファイルを削除しアラート記録します

トラブルシューティング（短く）
- DB ファイルがない / 開けない:
  - monitoring 用ダッシュボードやツールからは DB が存在し読み取り可能である必要があります。パスや権限を確認してください。
- OpenAI 呼び出し関連エラー:
  - OPENAI_API_KEY の設定確認、API 利用制限（429）、ネットワーク、モデル名の互換性に注意。実装はリトライするが限界あり。
- process priority / cpu affinity が設定できない:
  - プラットフォームや権限によっては設定に失敗して警告ログが出ますが、処理自体は継続します。

ライセンス・コントリビュート
- 本 README では記載していません。リポジトリの LICENSE を確認してください。

この README はコードベースの要点をまとめたものです。具体的な API 仕様や下位モジュールの詳細（OrderRepository のスキーマ、ExecutionEngine の設定項目、Broker API の実装など）は各ファイル内の docstring / コメントを参照してください。必要であれば各モジュールごとの詳細なドキュメントや運用手順書を追って作成できます。
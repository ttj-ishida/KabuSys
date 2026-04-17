KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤ライブラリです。  
主な機能は以下のとおりです。

- 注文送信・注文管理・再同期（ExecutionEngine / OrderManager / Reconciler）
- 監視・アラート・キルスイッチ（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ）
- リサーチ（ファクター計算、将来リターン、IC 計算など）
- ニュース NLP（OpenAI を用いた銘柄センチメント評価）とレジーム判定
- Paper Trading 検証レポート生成、Streamlit ダッシュボード

特徴
----
- 環境変数ベースの設定（.env / .env.local サポート）。Settings クラスで整合性チェックを実施
- Paper Trading と Live を明確に分離（Paper は専用 SQLite DB を使用）
- DuckDB を利用した時系列データ処理（prices_daily / raw_financials 等）
- LINE を使った一方向アラート送信（AlertManager）
- OpenAI（gpt-4o-mini など）を用いたニュース分析 / レジーム判定（APIキー必要）
- 監視は SQLite（monitoring.db）へ永続化。Streamlit でダッシュボード可視化

セットアップ
----------
前提
- Python 3.8+ 相当（実際の動作要件はプロジェクト側で確認してください）
- SQLite は標準ライブラリで利用可
- 以下のパッケージをインストールしてください（例）

pip install duckdb psutil requests openai streamlit

（実際は requirements.txt がある場合はそれを使用してください）

環境変数（主なもの）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルトは development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE アラート用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant / partial / never / reject、デフォルト instant）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等の監視系パス/挙動
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

.env 自動読み込み
- プロジェクトルート（.git または pyproject.toml）を探索し、.env / .env.local を自動で読み込みます。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

初期化
- monitoring DB のテーブルは run_monitoring.py / run_execution.py 内で init_monitoring_db により冪等に作成されます。

使い方
------

1) 監視ループの起動（Monitoring）
- 監視プロセスは SystemMonitor・TradeMonitor・RiskMonitor を組み合わせ、定期的に状態を記録・アラート発行します。

実行例:
python -m kabusys.run_monitoring

挙動:
- プロセス優先度を "high" に設定し、SQLite（settings.sqlite_path）と DuckDB（settings.duckdb_path）に接続します。
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（デフォルト 60 秒）。
- 停止はプロジェクトルート/data/stop_requested.flag 存在で行います（ファイルを作れば安全に停止）。

2) ExecutionEngine の起動（発注エンジン）
- 実際の発注処理と関連コンポーネント（BrokerClient / OrderManager / RiskManager / Reconciler）を起動します。

実行例:
python -m kabusys.run_execution

挙動:
- KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH の DB（デフォルト data/paper_trading.db）に完全分離して記録します。
- 停止は data/stop_requested.flag を作成するか、監視から kill.flag が書かれた場合に停止されます。
- 実行中の PID は data/execution.pid に書き込まれます。

3) Streamlit ダッシュボード
- 監視用 SQLite を read-only で参照してダッシュボードを表示します。

起動例:
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート
- paper_trading DB（data/paper_trading.db）を解析して稼働率・注文成功率・レイテンシ等を出力します。

実行例:
python -m kabusys.tools.paper_verification_report
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
オプション --db で DB パスを指定可能。

5) AI 関連
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key) — raw_news を読んで OpenAI に問い合わせ、ai_scores テーブルへ書き込みます。api_key は OPENAI_API_KEY の代替指定可（未設定時は例外）。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key) — レジーム判定を行い market_regime テーブルへ書き込みます。APIキー必須。

停止／キル
- run_monitoring.py / run_execution.py はプロジェクトルート/data/stop_requested.flag の存在をチェックして安全に終了します（手動で作成）。
- Monitoring 側の KillSwitch は data/kill.flag を書き込み、重要な条件（ドローダウン超過等）で ExecutionEngine 停止をトリガーします。
- kill.flag を起動時にクリアする設定 KILL_FLAG_CLEAR_ON_START=1 があります（Settings により制御）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス：環境変数取得・検証・デフォルト
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker）
- ai/
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に書込む
  - regime_detector.py: MA とマクロセンチメントを合成して market_regime を書込む
- monitoring/
  - monitoring_db.py: SQLite のスキーマ作成・永続化 API（MonitoringDB）
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py: 注文滞留・約定異常価格監視
  - risk_monitor.py: ドローダウン・ポジション数監視（KillSwitch トリガーと連携）
  - kill_switch.py: kill.flag の書き出しロジック
  - alert_manager.py: LINE へのプッシュ通知ラッパ
  - monitoring_engine.py: 各 Monitor を束ねてループ実行
  - streamlit_dashboard.py: Streamlit ダッシュボード（UI）
- execution/
  - order_manager.py: 注文作成・状態遷移の外向け API
  - reconciler.py: 起動時の再同期 / ポジション差分検出
  - （その他 BrokerFactory / ExecutionEngine などが存在）
- portfolio/
  - portfolio_builder.py: 候補選定・等重/スコア重み
  - position_sizing.py: 銘柄ごとの株数算出（lot 単位, 集計制約処理含む）
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- research/
  - factor_research.py: Momentum/Volatility/Value 等ファクター計算（DuckDB SQL）
  - feature_exploration.py: 将来リターン・IC・統計要約
- tools/
  - paper_verification_report.py: Paper Trading の検証レポート CLI
- utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

設計上の注意点 / 備考
-------------------
- Monitoring の DB（monitoring.db）と Execution の DB（paper_trading.db / production DB）は用途に応じて分離されています。Monitoring は環境にかかわらず Settings.sqlite_path（通常 data/monitoring.db）を使用します。
- Paper Trading（KABUSYS_ENV=paper_trading）では発注は MockBroker を経由し、本番ブローカーへは送信されません。Paper 用の DB は PAPER_TRADING_SQLITE_PATH に記録されます。
- OpenAI を利用する機能は API キーが必要です。score_news / score_regime は API キー未設定時に ValueError を送出します（設計上明示的な失敗）。一部の内部呼び出しは API エラー時にフェイルセーフ（0.0 やスキップ）で継続する挙動です。
- process priority / CPU affinity の設定は psutil を使います。アクセス権限により設定が失敗した場合は警告ログを出してスキップします。
- .env のフォーマットは標準的な KEY=VALUE に加え、export KEY=val、クォート文字、行末コメントの一部サポートがあります。自動ロードはプロジェクトルートが検出できる場合に行われます。

よく使うコマンド例
-----------------
- 監視を開始:
  python -m kabusys.run_monitoring

- エンジンを開始 (Paper Trading):
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

設定サンプル (.env)
-------------------
例（プロジェクトルート/.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxxx
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
LINE_USER_ID=your_line_user_id
MONITOR_POLL_INTERVAL=60

ライセンス / 貢献
-----------------
（このリポジトリにライセンス情報や貢献ガイドがあればここに追記してください）

その他
-----
- 詳細な設計方針やアルゴリズム（PortfolioConstruction.md, StrategyModel.md 等）はコード内 docstring やコメントに記載されています。必要に応じて参照してください。  
- 実運用前に Paper Trading で十分な検証を行ってください（特にリスク管理・KillSwitch 周り）。
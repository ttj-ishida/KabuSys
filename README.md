KabuSys — 日本株自動売買システム (README)
=========================================

概要
----
KabuSys は日本株の自動売買およびそれを補助する監視・リサーチ機能をまとめた小規模なフレームワークです。  
主な目的は「安全性を重視した注文実行」「ポートフォリオ構築ロジック」「ファクター計算・リサーチ」「ニュースの NLP によるスコアリング」「監視ダッシュボード」の提供です。

主要機能
--------
- ExecutionEngine：シグナルに基づく発注エンジン（Signal Pull + WebSocket Push ドレイン）。リスクゲート・レート制御・リコンシリエーションを備える。
- MonitoringEngine：プロセス健全性、データ鮮度、滞留注文・約定異常、ドローダウン監視・アラート送信（LINE）。
- Portfolio construction：候補選定、重み計算、ポジションサイズ算出、セクター制限やレジーム乗数。
- Research：DuckDB 上の価格・財務データからファクター（Momentum/Value/Volatility 等）を計算し、IC や将来リターン解析を実行。
- AI モジュール：
  - news_nlp：OpenAI を用いたニュースのセンチメント集約・銘柄スコア化（ai_scores への書き込み）。
  - regime_detector：ETF（1321）の MA とマクロニュースの LLM センチメントを合成して市場レジームを判定。
- Monitoring DB：SQLite に監視ログ・トレードログ・ポジション・リスクイベント・ダッシュボードを永続化。
- Streamlit ダッシュボード：監視データを可視化（Streamlit で起動可能）。
- ユーティリティ：プロセス優先度 / CPU affinity の設定、環境設定自動ロードなど。

セットアップ
------------
前提
- Python 3.9+（typing 機能・モジュール構成に依存）
- 以下のライブラリが必要（主要なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード使用時）
インストール例:
  pip install duckdb psutil requests openai streamlit

プロジェクトの .env 自動ロード
- パッケージ起動時、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、
  .env（優先度低）および .env.local（優先度高）を自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN：J-Quants API トークン（必須）
- KABU_API_PASSWORD：kabuステーション API 用パスワード（必須）

任意 / 設定可能な環境変数（代表例）
- KABUSYS_ENV：起動環境（development / paper_trading / live）。デフォルト: development
- OPENAI_API_KEY：OpenAI API キー（news_nlp / regime_detector 利用時）
- KABU_API_BASE_URL：kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID：LINE 通知設定
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH：paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE：paper_trading の MockBroker の約定モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH：ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH：ExecutionEngine 停止用フラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START：起動時に kill.flag を消すか（1 で clear）
- MONITOR_POLL_INTERVAL：Monitoring のポーリング間隔（秒、デフォルト 60）。0 以下や不正値は 60 にフォールバック。

初期データベース
- Monitoring 用 SQLite（SQLITE_PATH）は run_monitoring/run_execution が起動時に init_monitoring_db を呼び出して必要テーブルを作成します（冪等）。
- DuckDB 側はリサーチ / AI モジュールが prices_daily / raw_financials / raw_news 等のテーブルを参照します。これらは利用側で作成・投入してください（DuckDB ファイルのスキーマはコード内の SQL を参照）。

使い方
------
1. 開発環境の準備
   - .env を作成して必須鍵や DB パスを設定する（.env.example を用意している場合は参照）。
   - 必要な Python パッケージをインストール。

2. 監視プロセス（MonitoringEngine）の起動
   - デフォルトで MONITOR_POLL_INTERVAL=60 を使用します。上書き可能:
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 実行方法:
     - パッケージがインストール済み: python -m kabusys.run_monitoring
     - もしくはリポジトリ直下から: python src/kabusys/run_monitoring.py
   - 動作: プロセス優先度を高に設定し（psutil 必須）、SQLite と DuckDB に接続してポーリングを開始します。

3. 発注エンジン（ExecutionEngine）の起動
   - KABUSYS_ENV によって挙動が変わります:
     - KABUSYS_ENV=paper_trading: MockBrokerClient を使用し、データは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に書き込まれ本番 DB と分離されます。
     - KABUSYS_ENV=live: 実ブローカークライアントを使用（KABU_API_PASSWORD 等必要）。
   - 実行:
     python -m kabusys.run_execution
   - 起動前に kill.flag をクリアしたい場合、環境変数 KILL_FLAG_CLEAR_ON_START=1 にするか直接ファイルを削除してください。
   - 実行中に kill.flag が作成されると ExecutionEngine は安全に停止します。kill.flag は Monitoring の KillSwitch から作られます。手動で停止するには data/kill.flag を作成してください（中身は理由テキストを推奨）。

4. Streamlit ダッシュボード
   - 起動コマンド:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only で monitoring DB を開き、Overview / Positions / Orders / System を表示します。

5. AI / リサーチ関数の利用
   - news_nlp.score_news(conn, target_date, api_key=None)：
     - DuckDB 接続を与え、指定日のニュース窓でスコアを ai_scores テーブルに書き込みます。
     - OPENAI_API_KEY が必要（api_key 引数でも可）。
   - regime_detector.score_regime(conn, target_date, api_key=None)：
     - ETF 1321 の MA とマクロニュースの LLM 評価を合成し market_regime に書き込みます。

注意点 / 運用メモ
- process priority / cpu affinity の設定は psutil の権限によって失敗する場合がありますが、ログで警告を出してスキップします。
- Monitoring は本番 sqlite_path を使用する設計です（KABUSYS_ENV に依らず）。
- ExecutionEngine の paper_trading モードは本番 DB と完全に分離されます。
- news_nlp/regime_detector は OpenAI API に依存します。API エラーはリトライやフォールバック（macro_sentiment=0 等）する設計ですが、APIキー未設定時は例外を出します。
- kill.flag の書き込みは冪等設計：既に存在する場合は上書きしません。clear() で削除できます。
- .env のパースはシェル風の quoting をサポートしますが、ファイルがプロジェクトルートにない場合は自動ロードをスキップします。

ディレクトリ構成（src/kabusys の主なファイル）
-----------------------------------------
- run_monitoring.py         — SystemMonitor のポーリング起点スクリプト
- run_execution.py          — ExecutionEngine の起動スクリプト

- config.py                 — 環境変数 / .env 自動ロード / Settings クラス
- __init__.py               — パッケージメタ情報

- ai/
  - news_nlp.py             — ニュースセンチメントの OpenAI スコアリング
  - regime_detector.py      — 市場レジーム判定（MA + マクロLLM）

- monitoring/
  - monitoring_db.py        — SQLite スキーマ初期化・永続化 API
  - system_monitor.py       — CPU/メモリ/disk/process/data freshness チェック
  - trade_monitor.py        — 注文滞留・約定異常監視
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag の作成/評価
  - alert_manager.py        — LINE push での通知
  - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py  — Streamlit ダッシュボード

- execution/
  - execution_engine.py     — メインの発注エンジン（Signal 処理 / Push ドレイン）
  - order_manager.py        — 注文の状態遷移と broker 連携制御
  - order_repository.py     — （省略されたが DB 操作を担当）
  - reconciler.py           — 起動時の注文・ポジションの再同期ロジック
  - risk_manager.py         — リスクゲート（設定・レート制限・サーキットブレーカー）
  - broker_factory.py       — BrokerClient の生成（実・Mock の振り分け）
  - broker_api.py           — Broker API の抽象定義（Protocol）
  - order_record.py         — 注文状態の純粋ロジックモデル

- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 株数決定・丸め・aggregate cap
  - risk_adjustment.py      — セクター上限・レジーム乗数

- research/
  - factor_research.py      — momentum/value/volatility ファクター計算（DuckDB）
  - feature_exploration.py  — 将来リターン・IC・統計サマリ等

- utils/
  - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

補足（トラブルシューティング）
--------------------------------
- psutil に関する権限エラー：priority/affinity の設定で AccessDenied が出る場合はログに警告が出てスキップされます。通常動作に致命的ではありません。
- DuckDB のテーブルが不足していると research / ai の関数は正しく動作しません。prices_daily / raw_financials / raw_news 等の投入を確認してください。
- LINE 通知が届かない場合はトークン/ユーザーID の設定を確認してください（AlertManager は未設定時はログのみ出します）。
- Monitoring/Execution のログレベルは logging.basicConfig で INFO がデフォルトです。詳しいデバッグ出力が必要なら環境変数 LOG_LEVEL を設定してください（DEBUG/INFO/...）。

ライセンス / 貢献
-----------------
この README はコードベースの説明に基づく開発者向けドキュメントです。実稼働を行う場合は追加のテストとセキュリティ監査を実施してください。貢献はプルリクエストで歓迎します。

以上。必要であれば README にサンプル .env.example、起動スクリプトの systemd ユニット例、または各モジュールの API 使用例（関数サンプル）を追加します。どれを優先で追加しますか？
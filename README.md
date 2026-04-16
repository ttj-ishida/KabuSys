KabuSys — 日本株自動売買システム
このリポジトリは日本株向けの自動売買フレームワーク（KabuSys）の一部を構成するモジュール群です。監視・発注・ポートフォリオ構築・リサーチ・AI（ニュースNLP／レジーム判定）などの機能を含みます。以下はコードベース（src/kabusys）に基づく README（日本語）です。

プロジェクト概要
- KabuSys は自動売買エンジンとそれを支える監視・リスク管理・リサーチ機能群から構成されます。
- DuckDB を使った時系列データ解析（prices_daily / raw_financials 等）、SQLite を使った監視ログ・注文ログ管理、OpenAI（GPT）を使ったニュースセンチメント評価などを含みます。
- 本リポジトリはライブラリ／実行スクリプト群を提供し、実運用（live）・ペーパートレード（paper_trading）・開発（development）を想定しています。

主な機能一覧
- Execution（発注）
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - ブローカー抽象化（BrokerClientFactory）による本番/モック切替（KABUSYS_ENV）
  - OrderManager / OrderRepository / Reconciler による注文管理と再同期
  - RiskManager による発注時リスク制限
- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク・プロセス生存・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常監視
  - RiskMonitor：ドローダウン・ポジション上限監視
  - MonitoringEngine：各モニタのポーリングとアラート/キルスイッチ評価
  - MonitoringDB：SQLite を用いた監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - Streamlit ダッシュボード（監視用）
- Portfolio（ポートフォリオ構築）
  - 候補選定・等重/スコア加重配分（portfolio_builder）
  - セクター集中制限・レジーム乗数適用（risk_adjustment）
  - 株数計算（position_sizing） — 単元株丸め・合計コストスケーリング等
- Research（リサーチ）
  - factor_research: momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリなど
- AI（OpenAI を利用）
  - news_nlp: ニュースを LLM でセンチメント評価し ai_scores に書き込む
  - regime_detector: ETF（1321）MA200 とマクロ記事センチメント合成による市場レジーム判定
- ユーティリティ
  - process_priority: プロセス優先度・CPU affinity 設定（Windows / POSIX 対応）
  - .env 読み込みロジック（Settings）と各種設定プロパティ

セットアップ手順（概要）
1. 必要ライブラリをインストール
   - 主要依存例: python (>=3.10), duckdb, psutil, requests, openai, streamlit
   - 例: pip install duckdb psutil requests openai streamlit
   - （プロジェクトの requirements.txt があればそれを使ってください）

2. リポジトリをクローン／配置
   - コードは src/kabusys 以下に配置されている前提です。
   - プロジェクトルートには data/ ディレクトリを作成しておくと便利です（DB・PID・フラグファイル保存先）。

3. 環境変数（.env）設定
   - 自動ロード: Settings モジュールはプロジェクトルートの .env と .env.local を自動で読み込みます（OS 環境 > .env.local > .env）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数（代表例）:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
     - KABU_API_PASSWORD: kabuステーション API 用（必須）
     - OPENAI_API_KEY: OpenAI 呼び出し用（news_nlp / regime_detector）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db） — Monitoring は環境にかかわらず本番 sqlite_path を使用
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading のモック約定モード（instant|partial|never|reject、デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - PID_FILE_PATH / KILL_FLAG_PATH 等（デフォルトは data 内）

4. データディレクトリと初期 DB
   - data/ 以下に DB（DuckDB, SQLite）と PID/flag ファイルを配置します。MonitoringDB の初期化は実行時に自動でテーブルを作成します。

使い方（主要な起動方法）
- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor をポーリングし、monitoring DB に記録します。
  - オプション: MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - stop: プロジェクトルート data/stop_requested.flag を作成するとループが終了します（ファイル検出で安全停止）。

- 発注エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 説明: ExecutionEngine を起動し、BrokerClient を利用して発注処理を行います。
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録して本番 DB と分離します。
  - 起動前に data/kill.flag がある場合は起動を行わず終了します。実行中に data/stop_requested.flag が作成されると安全に停止します。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - デフォルトは data/monitoring.db（読み取り専用で開く）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）
  - 指標: 稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等の簡易判定を出力

- AI 関連
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を使ってニューススコア／レジーム判定を行えます。OpenAI API キー（OPENAI_API_KEY）を必ず設定してください。
  - API 呼出しはリトライロジックやレスポンスバリデーションを備えていますが、失敗時は安全にフォールバック（スコア=0 等）する設計です。

停止・緊急停止
- Execution 側強制停止（KillSwitch）
  - KillSwitch はリスク条件（ドローダウン超過、ポジション上限等）を満たした場合に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（エンジンは起動時に kill.flag をクリアするか、存在すれば起動を拒否します）。
- 一般停止フラグ
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して安全に停止します。

設定（Settings）に関する重要事項
- Settings はプロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV 値: development, paper_trading, live（無効な値は例外）
- PAPER_FILL_MODE の許容値: instant | partial | never | reject（無効な値は例外）
- Monitoring は環境にかかわらず sqlite_path（デフォルト data/monitoring.db）を使用します。

ディレクトリ構成（src/kabusys の主要ファイル／モジュール）
- src/kabusys/
  - __init__.py (パッケージ情報)
  - config.py (Settings / .env 読み込み)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)
  - ai/
    - news_nlp.py (ニュースセンチメントスコアリング)
    - regime_detector.py (市場レジーム判定)
  - monitoring/
    - monitoring_db.py (監視ログの SQLite 永続化、MonitoringDB クラス)
    - system_monitor.py (システム / データ鮮度監視)
    - trade_monitor.py (滞留注文 / 約定異常監視)
    - risk_monitor.py (ドローダウン / ポジション上限監視)
    - monitoring_engine.py (各 Monitor を束ねてポーリング)
    - alert_manager.py (LINE 通知)
    - kill_switch.py (kill.flag 書き込みユーティリティ)
    - streamlit_dashboard.py (Streamlit ダッシュボード)
  - execution/
    - reconciler.py (起動時リコンシリエーション)
    - order_manager.py (発注状態管理)
    - ...（Broker 関連・OrderRepository などは同ディレクトリに存在）
  - portfolio/
    - portfolio_builder.py (候補選定・重み計算)
    - risk_adjustment.py (セクター制限、レジーム乗数)
    - position_sizing.py (株数計算)
  - research/
    - factor_research.py (モメンタム/ボラ/バリュー等)
    - feature_exploration.py (将来リターン・IC 等)
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity)

開発メモ / 注意事項
- MonitoringDB.init_monitoring_db() は起動時にテーブルを冪等に作成し、必要なマイグレーション（カラム追加）も実行します。
- process_priority.set_process_priority("high") を起動直後に呼ぶ設計（run_* スクリプト）。権限不足や非対応 OS の場合は警告を出してスキップします。
- DuckDB 接続は research / ai / regime 判定でデータ参照専用に使われます。prices_daily / raw_financials / raw_news 等テーブルを前提とします。
- OpenAI API 呼び出しはレスポンスのバリデーション・リトライを行いますが、APIキー未設定時は ValueError を送出します（呼び出し元で捕捉してください）。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータが作成されていることを確認してください。

トラブルシュート（よくある質問）
- 「.env が読み込まれない」: KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか、プロジェクトルートが .git / pyproject.toml によって検出できているか確認してください。手動で環境変数を export することも可能です。
- 「OpenAI キーがない」: news_nlp / regime_detector は OPENAI_API_KEY が必要です。開発時はキーの提供／モック化して unit test を実行してください。
- 「監視が何も記録しない」: run_monitoring を起動すると MonitoringDB が初期化され、system_status 等に定期登録されます。MONITOR_POLL_INTERVAL を短くしてテストすると確認しやすいです。

貢献 / 拡張案（参考）
- 単元株（lot_size）を銘柄ごとに管理するためのマスタ追加
- transaction コスト（スリッページ/手数料）を動的に推定して position_sizing に反映
- AlertManager に Slack / PagerDuty など別チャネルを追加
- AI モジュールのレスポンスフォーマット検証を強化

以上がコードベース（src/kabusys）に基づく README の要点です。必要であれば、環境変数テンプレート（.env.example）や具体的なコマンド例、systemd / supervisor 用のサービス定義サンプル、Dockerfile／docker-compose のテンプレートも作成できます。どれを優先して欲しいか指示してください。
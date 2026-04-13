KabuSys — 日本株自動売買システム
概要
本リポジトリは「KabuSys」と呼ぶ日本株自動売買システムのコアライブラリ群です。  
主に以下を提供します。
- 注文発行・状態管理・リコンシリエーション（execution）
- ポートフォリオ構築・ポジションサイジング（portfolio）
- ファクター計算・リサーチユーティリティ（research）
- ニュース NLP（OpenAI）を用いた銘柄スコアリング・レジーム判定（ai）
- 実行系／注文本体の監視・アラート・ダッシュボード（monitoring）
- テスト・検証用ユーティリティ（tools）

機能一覧
- Execution
  - Broker クライアント抽象化（本番/モックの切替）
  - OrderManager：注文の作成→送信→同期の安全な状態遷移
  - Reconciler：再起動時の自動同期（ブローカーとの突合）
  - RiskManager（設定に基づく発注制約）
- Portfolio
  - 候補選定（スコア昇順ソート等）
  - 等金額／スコア加重配分
  - セクター集中制限、レジーム乗数
  - 株数決定（単元丸め、aggregate cap）
- Research
  - Momentum/Volatility/Value 等のファクター計算（DuckDB を入力）
  - 将来リターン、IC（Spearman）等の評価ユーティリティ
- AI
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント化して ai_scores に保存
  - マクロニュース + ETF MA200 を使った市場レジーム判定
- Monitoring
  - system/trade/risk 各監視（DB ログ + LINE 通知）
  - Kill switch（kill.flag）で ExecutionEngine の停止指示
  - streamlit ダッシュボード（監視 DB の可視化）
  - Paper Trading 用検証レポート生成ツール

セットアップ手順
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトの requirements.txt があれば pip install -r requirements.txt）
4. データディレクトリを準備
   - mkdir -p data
   - デフォルトで使用されるファイル:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (監視用 SQLite)
     - data/paper_trading.db (Paper Trading 用 SQLite)
5. 環境変数設定
   - .env または .env.local をプロジェクトルートに置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 重要な環境変数（一例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須な箇所あり）
     - KABU_API_PASSWORD — kabu ステーション API パスワード
     - OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）
     - KABUSYS_ENV — 起動環境: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading の専用 SQLite（デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE — paper_trading の fill モード（instant|partial|never|reject）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - PID_FILE_PATH, KILL_FLAG_PATH — PID / kill.flag のパス

主な使い方（コマンド例）
- 実行エンジン（ExecutionEngine）を起動
  - 環境による動作差: KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading 用 DB に記録されます。
  - 実行:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - あるいは（デフォルト環境で）python -m kabusys.run_execution
- 監視ループを起動（SystemMonitor 単独）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（デフォルト 60秒）。
  - 実行:
    - python -m kabusys.run_monitoring
- Streamlit ダッシュボード（監視 DB の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - （-- のあとに渡すオプションで DB パスを指定）
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH を使用
- AI モジュールの呼び出し（コードから）
  - 例（Python REPL など）:
    - from openai import OpenAI
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date=datetime.date(2026,4,10), api_key="sk-...")
  - OPENAI_API_KEY が環境変数にある場合、api_key 引数は省略可能

重要な挙動・設定メモ
- 環境（KABUSYS_ENV）
  - development: 開発用（デフォルト）
  - paper_trading: ブローカーをモックに切替、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離
  - live: 本番運用
- .env の自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を読み込みます。
  - 読み込み順序: OS 環境変数 > .env.local（上書き） > .env（未設定のみ）
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。0 や負値は無効でデフォルト 60 秒にフォールバック。
- PAPER_FILL_MODE（paper_trading 時）
  - instant | partial | never | reject のいずれか。無効値は例外。
- kill.flag / PID
  - モニタリング側は PID ファイルの存在・生存を確認してプロセス停止を検出します。
  - KillSwitch は data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります（Execution 側で kill.flag を見て停止する実装が想定されます）。
- LINE アラート
  - AlertManager は LINE Messaging API を用いた一方向通知を行います。channel token / user id が未設定の場合は送信せずログ出力に留めます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / 設定読み込みロジック
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor 単体のポーリング起動スクリプト
  - execution/
    - broker_factory.py, broker_api.py, ... — ブローカー抽象・実装 (Mock/Live)
    - execution_engine.py — ExecutionEngine のコア
    - order_manager.py, order_repository.py, order_record.py — 注文管理
    - reconciler.py — 再起動リコンシリエーション
    - risk_manager.py — リスク制御ロジック
  - portfolio/
    - portfolio_builder.py — 候補選定・配分
    - position_sizing.py — 株数計算（単元丸め・制限）
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — マクロ + ETF MA200 によるレジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py — SQLite による永続化層（テーブル作成・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 制御
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるランナー
    - streamlit_dashboard.py — Streamlit ダッシュボード（起動用スクリプト）
  - data/ （想定）
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

開発・実行上の注意
- DuckDB/SQLite のデータスキーマやマイグレーションは各モジュール内に記載のロジックで管理されます（例: monitoring_db.init_monitoring_db は冪等でテーブル作成・カラム追加を行う）。
- OpenAI（ai モジュール）を呼ぶ箇所は API エラーに対してリトライやフェイルセーフ（スコア 0.0 やスキップ）を実装していますが、API キーの管理・コストには注意してください。
- プロセス優先度や CPU affinity 設定は psutil を経由して行います。権限がない環境では警告が出てスキップされます。
- パッケージ内スクリプトはパッケージでの実行（python -m kabusys.run_execution 等）を推奨します。これにより相対インポートが正しく機能します。

よく使う例まとめ
- Paper Trading 実行（モックブローカー）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視（SystemMonitor）起動（デフォルト 60s 間隔）
  - python -m kabusys.run_monitoring
  - 短くしたい場合: MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
- （ここにプロジェクトのライセンスや貢献ガイドラインを追加してください）

問い合わせ・補足
- 実運用に移行する場合はブローカー API のレート制限、エラーハンドリング、セキュリティ（API キー格納）、常時稼働環境での監視/再起動戦略を十分に検討してください。README に追加したい具体的な運用手順や環境固有の情報があれば教えてください。
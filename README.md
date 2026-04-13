# KabuSys

KabuSys は日本株の自動売買システム（プロトタイプ）です。戦略（ファクター計算・ポートフォリオ構築）・実行エンジン・監視・研究用ツール・AI ベースのニュースセンチメントなどのコンポーネントを含みます。本リポジトリはモジュール群の実装（純粋関数群・DB 永続化・外部 API 呼び出しなど）を提供します。

注意: この README はソースコード（src/kabusys 以下）を基にした概要と操作手順をまとめたものです。実運用前には十分なテストと安全対策（ブローカー資格情報・資金管理等）を行ってください。

---

## 主要機能

- 戦略・リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算・IC（Information Coefficient）計算
- ポートフォリオ構築
  - 候補選定、等金額・スコア重み・リスクベース配分
  - セクター上限適用、レジーム乗数
  - 株数の決定（lot 単位丸め、利用可能現金に応じたスケール）
- 実行（Execution）
  - ExecutionEngine（起動スクリプト: run_execution.py）
  - OrderManager / Reconciler: ブローカーとの同期、再起動時の復旧
  - Paper Trading モード（本番 DB と分離）
- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor: 滞留注文、約定異常価格検出
  - RiskMonitor: ドローダウン監視、ポジション上限監視
  - KillSwitch / AlertManager: 条件により ExecutionEngine 停止フラグを書き込み、LINE へ通知可能
  - Monitoring DB（SQLite）への永続化と Streamlit ダッシュボード
- AI（OpenAI）
  - ニュースを LLM でスコアリングして ai_scores に書き込み（news_nlp）
  - マクロセンチメントと ma200 を合成して市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
  - Streamlit ベース監視ダッシュボード

---

## セットアップ手順（開発 / 試験用）

前提
- Python 3.10 以上（ソースが型ヒントの union 型や新しい構文を使用）
- Git, SQLite（標準ライブラリで利用）、任意で DuckDB ライブラリ

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - （本リポジトリに requirements.txt がある場合）pip install -r requirements.txt
   - 主要依存（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

4. 環境変数 / .env
   - プロジェクトルートの .env / .env.local が自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須例（機能により必須）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API（研究用）
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（実行時）
     - OPENAI_API_KEY: OpenAI を利用する機能（news_nlp / regime_detector）
   - 任意:
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
     - KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルトは development
     - PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite パス（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH など

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

注意: 実行時に各スクリプトが DB ファイルの存在を確認して必要なテーブルを作成します（init_monitoring_db は冪等）。

---

## 起動・使い方

以下は代表的な起動方法です。各スクリプトは src/kabusys 配下のモジュールとして実行できます。

1. ExecutionEngine（実行エンジン）を起動
   - 本番 / 開発 / Paper トレードを切り替え:
     - KABUSYS_ENV=development|paper_trading|live
   - 実行:
     - python -m kabusys.run_execution
   - 動作:
     - paper_trading の場合は MockBroker / PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。
     - 起動時にプロセス優先度を High に設定し、pid ファイル（Settings.pid_file_path、デフォルト data/execution.pid）を参照・出力します。

2. 監視ループ（Monitoring）を起動
   - python -m kabusys.run_monitoring
   - オプション:
     - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き（デフォルト 60 秒）。
   - 動作:
     - SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、監視 DB（Settings.sqlite_path）へログを書き込みます。
     - KillSwitch によりデータベース上の条件が満たされると data/kill.flag を書き込み、ExecutionEngine 停止を促します。

3. Streamlit ダッシュボード（監視の可視化）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - (別プロセスで MonitoringEngine を起動しておくとデータが反映されます)

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db。--db オプションで別パス指定可。

5. AI スコア / レジーム判定
   - AI 関連機能は OpenAI API キー（OPENAI_API_KEY）が必要です。
   - 関数呼び出し例（スクリプトから）:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 実行は DuckDB 接続を作成して呼ぶ設計になっています（DB に raw_news / prices_daily 等が必要）。

---

## 重要な設定（Settings と環境変数）

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（研究モジュールが参照）
- KABU_API_PASSWORD: kabuステーション API パスワード（Execution 時に必要）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）を使う場合
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring でのポーリング間隔（秒）

.env の自動読み込み
- プロジェクトルートに .env / .env.local があれば自動で読み込まれます。
- OS 環境変数が優先され、.env.local は .env を上書きできます。
- 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主なファイル / モジュール）

src/
- kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数の集中管理、.env 自動ロード）
  - run_execution.py
    - ExecutionEngine の起動スクリプト（KABUSYS_ENV により paper_trading モードを使い分け）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py         — SQLite テーブル作成 / MonitoringDB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py     — 各 Monitor を束ねる
    - streamlit_dashboard.py
    - __init__.py
  - execution/
    - order_manager.py
    - reconciler.py
    - （その他 execution 関連モジュールが想定される）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/ (上記)
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (外部データアクセス用のモジュール群、DuckDB/Prices 等が存在する想定)

data/
- デフォルトの永続化ファイル（実行時に作成される）
  - data/kabusys.duckdb (DuckDB データファイル)
  - data/monitoring.db (SQLite 監視 DB)
  - data/paper_trading.db (Paper Trading 用 SQLite、KABUSYS_ENV=paper_trading のときに使用)
  - data/execution.pid (ExecutionEngine が作成する pid ファイル)
  - data/kill.flag (KillSwitch が作成する停止フラグファイル)

---

## 追加メモ / トラブルシューティング

- DB 初期化: run_monitoring / run_execution は起動時に監視用テーブル群を作成します（冪等）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading のときは本番用 DB と分離されます。PAPER_TRADING_SQLITE_PATH を確認してください。
  - PAPER_FILL_MODE を適切に設定して約定挙動を制御できます。
- OpenAI 呼び出し:
  - API エラーやレート制限に対してはリトライやフォールバック（ゼロスコア）などの安全策がありますが、API キーは必ず設定してください。
- プロセス優先度設定:
  - run_* スクリプトは起動時に set_process_priority("high") を呼びます。psutil の権限により失敗する場合があります（警告ログ）。
- LINE 通知:
  - Channel token / user id が未設定の場合は通知は送信されずログに記録されます。
- ログレベル:
  - Settings.log_level による制御が可能です（環境変数 LOG_LEVEL）。
- セキュリティ:
  - 認証情報（API キー、パスワード）は .env に保存する場合アクセス権限に注意してください。公開リポジトリに含めないでください。

---

必要があれば、この README に以下の情報を追加できます:
- requirements.txt の推奨内容
- 実際の ExecutionEngine / EngineConfig の詳細な設定例
- DuckDB / prices_daily テーブルのスキーマやデータ投入手順
- CI / テストの実行方法

必要な追加情報やドキュメント化してほしい箇所があれば教えてください。
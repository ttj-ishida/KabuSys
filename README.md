# KabuSys

軽量な日本株自動売買システムのモジュール群（ライブラリと起動スクリプト群）。  
このリポジトリは、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI 補助（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動・ツール）
- 環境変数 / 設定
- ディレクトリ構成
- 運用メモ / ファイルの意味

---

プロジェクト概要
- KabuSys は日本株向けの自動売買サブシステムを想定したモジュール群です。
- 発注・状態管理・再整合（reconciliation）・リスク管理・監視・通知・検証レポート作成・研究用ファクター計算・AI を使ったニュースセンチメント評価・レジーム判定等の機能を持ちます。
- DB 永続化は SQLite（監視ログ、paper trading）と DuckDB（時系列価格・財務データなど分析用）を利用します。
- 実稼働 / Paper Trading を分離して運用できる設計になっています（KABUSYS_ENV による切り替え）。

機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - 本番接続 / paper_trading（モックブローカー）を環境変数によって切替
  - ブローカークライアント生成、OrderManager / RiskManager / Reconciler の組立てと ExecutionEngine 起動
  - 停止フラグ（data/stop_requested.flag）により安全停止
- 監視プロセス（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングしてログとリスクイベントを記録
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path を参照（環境に依存しない）
- 監視 DB 層（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard のテーブル生成・マイグレーション・読み書き
- 監視コンポーネント
  - SystemMonitor: プロセス生存、CPU/MEM/DISK、データ鮮度チェック
  - TradeMonitor : 滞留注文、約定異常価格チェック
  - RiskMonitor  : ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch   : 条件発動時に data/kill.flag を書き ExecutionEngine に停止シグナル送出
  - AlertManager : LINE Messaging API による通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- Portfolio（portfolio パッケージ）
  - 候補選定、等金額/スコア重み付け、セクター制限、レジーム乗数、株数決定（単元丸め・リスク制限）
- Research（research パッケージ）
  - ファクター計算（momentum/value/volatility）、将来リターン計算、IC、特徴量サマリ
- AI（ai パッケージ）
  - news_nlp: raw_news を OpenAI に送り銘柄単位のセンチメントスコアを ai_scores に書き込み
  - regime_detector: ETF ma200 とマクロニュースセンチメントを合成して market_regime を決定
- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率、注文成功率、レイテンシ等）

セットアップ手順（開発 / 実行環境）
1. Python
   - 推奨: Python 3.10+（typing 機能や modern パッケージ互換のため）
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージインストール
   - pip install duckdb psutil openai requests streamlit
   - （実環境では追加で必要なパッケージがあるかもしれません。requirements.txt がある場合はそちらを使用してください）
4. プロジェクトルートに `data/` ディレクトリを作成
   - mkdir -p data
   - 初期 DB ファイルは実行時に自動生成されます（init_monitoring_db が作成）
5. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードは無効化）
   - 必須項目や主な環境変数は後述（「環境変数 / 設定」参照）

使い方（起動例・ツール）
- 実行エンジン（ExecutionEngine）を起動
  - 本番 / development / paper_trading を KABUSYS_ENV で切替
  - 例（Paper Trading）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 例（本番/開発）:
    - export KABUSYS_ENV=development
    - python -m kabusys.run_execution
  - 注意: paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）にログを記録し本番 DB と分離されます。

- 監視プロセスを起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
  - python -m kabusys.run_monitoring

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - MonitoringEngine が data/monitoring.db に書き込んでいることが前提。DB が存在しない場合はエラー表示されます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能（優先度はコマンドラインより低い）

- AI 関連（ニューススコア / レジーム判定）
  - API キーは OPENAI_API_KEY 環境変数、または関数引数で指定
  - 例: score_news(conn, target_date, api_key="...") / score_regime(conn, target_date, api_key="...")
  - 実行スクリプトは含まれていませんが、ライブラリ API を呼び出す形で使用します。

環境変数 / 設定（主なもの）
- アプリ動作モード
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト "development"）
- 外部 API / トークン
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は送信をスキップ）
- DB パス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- Paper Trading 設定
  - PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（デフォルト "instant"）
- 監視 / PID / Kill Flag
  - PID_FILE_PATH: ExecutionEngine が書く PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: KillSwitch が書き込む flag（default data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: "1" にすると ExecutionEngine 起動時に kill flag をクリア
- 監視しきい値（デフォルト値）
  - CPU_THRESHOLD_PCT (90.0)
  - MEMORY_THRESHOLD_PCT (85.0)
  - DISK_THRESHOLD_PCT (90.0)
- 自動 .env 読込
  - .env / .env.local はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に自動で読み込まれます
  - OS 環境変数は上書き保護されます
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読込を無効化

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化・読み書き
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
    - (他に broker_factory, execution_engine, order_repository 等が存在する想定)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                    — 実行時に使用する flag / pid / DB を置く想定（リポジトリ直下に data ディレクトリを作成）
- data/
  - monitoring.db (SQLite、監視ログ)
  - paper_trading.db (SQLite、paper trading)
  - kabusys.duckdb (DuckDB、価格・財務データ等)
  - execution.pid (ExecutionEngine の PID)
  - kill.flag / stop_requested.flag (停止・キル制御用フラグファイル)

運用メモ / 注意事項
- 停止制御
  - data/stop_requested.flag や data/kill.flag によるフラグファイルで、監視や実行スクリプトを安全に停止できます。手動でフラグファイルを作成・削除して操作します。
- プロセス優先度
  - run_execution/run_monitoring は起動時に set_process_priority("high") を呼び出します。psutil の権限不足等で設定に失敗した場合は警告が出ますが処理は継続します。
- DB マイグレーション
  - init_monitoring_db は冪等でテーブルを作成し、既存 DB にカラムが不足している場合は ALTER を試みます。
- AI 呼び出し
  - OpenAI API 呼び出しはリトライ・バックオフやレスポンス検証を行いますが、API キー管理・コストにはご注意ください。
- Paper Trading と本番 DB は分離
  - 環境 KABUSYS_ENV=paper_trading の場合は paper_trading DB を使い、本番データを汚さない設計です。

問い合わせ / 貢献
- このドキュメントはコードベースからの抜粋に基づいています。実行時の環境や追加モジュールにより多少の差異があり得ます。実装に関する修正や拡張提案は Pull Request を歓迎します。

---- 

必要であれば、README にサンプル .env.example、依存関係の requirements.txt、または各スクリプトのコマンド例（systemd ユニット例、docker-compose 例）も追記できます。どの情報を追加しますか？
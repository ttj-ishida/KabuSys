# KabuSys

KabuSys は日本株の自動売買システム向けユーティリティ群です。  
バックテスト／リサーチ用のファクター計算、ポートフォリオ構築、注文実行の補助、監視・アラート、LLM を使ったニュースセンチメントやレジーム判定などのモジュールを含みます。

主な設計方針:
- DuckDB / SQLite をデータ格納に使用（ローカルファイルベース）
- 環境変数 / .env で設定を管理（Settings クラス）
- Paper Trading と Live を完全分離（paper_trading 用 DB を使用）
- LLM 呼び出しはエラーに寛容（リトライ・フォールバックを採用）
- 監視は独立プロセス（stop/kill フラグで制御）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成
- 重要な環境変数（主要なもの）

---

プロジェクト概要
- モジュール群は主に以下の責務を提供します。
  - research: DuckDB 上の市場データからファクター・リターン・統計を計算
  - portfolio: 候補選定、重み付け、ポジションサイズ計算、リスク調整
  - execution: ブローカーとのやり取り（Engine / OrderManager / Reconciler 等）
  - monitoring: システム状態・注文・リスク監視、LINE によるアラート、Streamlit ダッシュボード
  - ai: OpenAI を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
  - tools: 補助スクリプト（例: paper_trading の検証レポート生成）

機能一覧
- ファクター計算（モメンタム、ボラティリティ、バリュー）
- 将来リターン / IC（Information Coefficient）計算・統計サマリー
- 銘柄選定（スコア順／等配分）と重み計算
- ポジションサイズ計算（リスクベース、等配分、スコアベース）、単元株丸め、投資上限・集計キャップ処理
- Paper Trading 向けの Mock ブローカーと DB 分離
- ExecutionEngine の起動スクリプト（再起動時のリコンサイル機能）
- 監視エンジン（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE）
- Kill Switch（しきい値超過で Execution を停止するフラグファイル）
- Streamlit による監視ダッシュボード
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント・レジーム検出
- Paper Trading の検証レポート生成スクリプト

セットアップ手順
1. Python バージョン
   - Python 3.10 以上を推奨（型ヒントや | 演算子を使用）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .\.venv\Scripts\activate     (Windows)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - 追加で必要なライブラリがあれば適宜インストール（sqlite3 は標準ライブラリ）
   - （実運用では requirements.txt を用意して pip install -r requirements.txt を使ってください）
4. 環境変数 / .env
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数は以下「重要な環境変数」を参照してください。
5. データディレクトリ
   - data/ 配下に DB ファイルやフラグファイルが作られます:
     - data/kabusys.duckdb（DuckDB、価格等の時系列データ）
     - data/monitoring.db（監視ログ用 SQLite）
     - data/paper_trading.db（paper_trading 時に使用する SQLite）
     - data/execution.pid（ExecutionEngine が書き込む PID）
     - data/stop_requested.flag（手動停止用フラグ）
     - data/kill.flag（Kill Switch が書き込む停止フラグ）

使い方（主要なスクリプト / API）
- 実行（モジュールとして）
  - 監視ループを起動
    - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト: 60）
    - 監視は Settings.env に依らず本番 SQLite（settings.sqlite_path）を使用します
  - ExecutionEngine を起動
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
    - 停止は data/stop_requested.flag を作成すると検知して停止します
- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で監視 DB のパスを指定可能（デフォルト: data/monitoring.db）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite パスを指定（環境変数 PAPER_TRADING_SQLITE_PATH でも可）
- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=None)
    - target_date に対して前日15:00 JST〜当日08:30 JST の記事を集計して ai_scores を更新
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
    - ETF 1321 の MA200 乖離とマクロニュースを合成して market_regime を更新
- ライブラリとして利用
  - 研究用 API 例:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - result = calc_momentum(duckdb_conn, date(2026, 4, 1))

運用に関する注意
- KABUSYS_ENV が paper_trading の場合、発注ロジックは Mock ブローカーに切り替わり、書き込み先 SQLite が別になります（PAPER_TRADING_SQLITE_PATH）。
- 実行プロセス起動時にプロセス優先度を上げる処理が走ります（kabusys.utils.process_priority.set_process_priority）。
- 停止は data/stop_requested.flag（run_monitoring.py/run_execution.py が参照）や data/kill.flag（KillSwitch により作成）で制御します。
- OpenAI 関連は API キーが必須です。API エラー時は自動的にリトライやフォールバック（スコア 0.0 など）する設計ですが、API キーの漏洩に注意してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — Settings / .env ローダ
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading の検証レポート生成
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI でセンチメント）
    - regime_detector.py       — レジーム判定（MA200 + マクロセンチメント）
  - research/
    - factor_research.py       — モメンタム/ボラ/バリュー等の計算
    - feature_exploration.py   — 将来リターン、IC、統計サマリー
  - portfolio/
    - portfolio_builder.py     — 候補選定、重み計算
    - position_sizing.py       — 発注株数計算、集計キャップ処理
    - risk_adjustment.py       — セクター制限、レジーム乗数
  - monitoring/
    - monitoring_db.py         — SQLite テーブル作成・読み書きラッパ
    - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度/プロセス存在チェック
    - trade_monitor.py         — 注文滞留・約定異常検出
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag の作成/管理
    - alert_manager.py         — LINE Push 通知
    - monitoring_engine.py     — 各モニタを束ねるループ
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py        — 発注 State Machine の外向き API
    - reconciler.py           — 起動時の注文 / ポジション照合
    - ... (ブローカーインターフェース等)
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (実行時生成される想定)
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - stop_requested.flag
    - kill.flag

重要な環境変数（主要なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用のトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用トークン（任意）
- LINE_USER_ID: LINE 通知先ユーザー ID（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject。デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むパス（デフォルト: data/kill.flag）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化（テスト時など）

補足
- .env のパースは config.py 内のロジックに従い、export 形式・クォート・インラインコメント等をある程度サポートします。
- DuckDB / SQLite の接続はファイルパスで行うため、実行ユーザーのファイルアクセス権に注意してください。
- LLM 呼び出し部分（news_nlp / regime_detector）は外部 API エラーに対してリトライやフォールバックを組み込んでいますが、API 利用料・レート制限等の運用面は別途考慮してください。

ライセンス・貢献
- 本 README はコードベースに基づく簡易ドキュメントです。実際のライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。

問題や質問があれば、どの機能について詳しく知りたいか教えてください。デプロイ手順や具体的な運用例（systemd サービスや Docker 化など）についても補足できます。
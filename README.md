# KabuSys

日本株自動売買システムの一部（実行エンジン・監視・ポートフォリオ構築・リサーチ・AI補助）を含むコードベースの README です。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数 / .env の扱い
- 使い方（起動方法・主要 API の呼び出し例）
- 重要設定と動作モード
- ディレクトリ構成（ファイル一覧と説明）
- 注意点 / 運用上の補足

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムのコンポーネント群です。
- 主な役割は（1）シグナルを受けて発注する ExecutionEngine、（2）稼働中のプロセス・注文・リスクを監視する Monitoring、（3）ポートフォリオ構築・ポジションサイジング、（4）ファクター計算・リサーチ、（5）ニュースを LLM でスコア化する AI モジュール、などです。
- DB は主に DuckDB（時系列・リサーチ用）と SQLite（監視ログ・発注履歴など）を併用します。

主な機能一覧
- ExecutionEngine
  - シグナルを読み込み Gate（リスクチェック）を通して発注
  - WebSocket / push を想定したドレイン処理で約定同期
  - 再起動時の Reconciler による発注状態リコンシリエーション
  - Paper Trading モード（本番DBとは分離）をサポート
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセスの監視
  - TradeMonitor: 滞留注文や約定価格異常の検出
  - RiskMonitor: ドローダウンやポジション上限の監視（kill.flag 発動）
  - AlertManager: LINE に一方向プッシュ通知（任意）
  - Streamlit による監視ダッシュボード
- Portfolio（純粋関数）
  - 候補選定、等金額 / スコア加重配分、ポジションサイズ計算（単元丸め含む）
  - セクターキャップやレジーム乗数の適用
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（情報係数）、統計サマリー
- AI
  - ニュースの銘柄別センチメントスコア化（OpenAI API）
  - マクロニュース + ETF MA200 を元に市場レジーム判定（LLM + ルール合成）

セットアップ手順（例）
1. Python バージョン
   - Python 3.10 以上を推奨（型ヒントで | を使用しているため）。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージ（例）
   - pip install duckdb psutil requests openai streamlit
   - 実運用では requirements.txt を用意して pip install -r requirements.txt を推奨。

4. プロジェクトルート
   - このリポジトリをクローンしたディレクトリをプロジェクトルートとして使います。
   - config モジュールは .git または pyproject.toml を起点にプロジェクトルートを探索し、.env / .env.local を自動読み込みします（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

5. データディレクトリ（デフォルト）
   - DuckDB: data/kabusys.duckdb
   - Monitoring SQLite: data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading のとき使用）
   - PID ファイル: data/execution.pid
   - Kill flag: data/kill.flag

環境変数（主要）
- 必須（運用に応じて）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD — kabuステーション API 用
- OpenAI
  - OPENAI_API_KEY — LLM 呼び出し（ai.score_news / score_regime で使用）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- 動作モード等
  - KABUSYS_ENV — 開発/ペーパー/本番: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG|INFO|...）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — paper_trading の fill 動作（instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB パス
  - SQLITE_PATH / DUCKDB_PATH — 各 DB のパス（デフォルトは data/...）

.env の取り扱い
- 自動読み込み順: OS 環境変数 > .env.local > .env
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env ファイルのフォーマットは一般的な shell style（export KEY=VAL / quoted values / コメント）に対応

使い方（起動方法）
- 実行スクリプト（ソースから実行）
  - Monitoring を起動:
    - python src/kabusys/run_monitoring.py
    - 環境変数で間隔を変える: MONITOR_POLL_INTERVAL=30 python src/kabusys/run_monitoring.py
    - 注意: Monitoring は監視用 DB（sqlite）は常に settings.sqlite_path（本番のパス）を使用します（環境に関係なく）。
  - Execution（注文実行）を起動:
    - python src/kabusys/run_execution.py
    - Paper trading モードで起動するには: export KABUSYS_ENV=paper_trading; python src/kabusys/run_execution.py
    - Paper trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用します。
- 実行スクリプト（パッケージとしてインストールした場合）
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- AI モジュール呼び出し例（Python REPL またはスクリプト）
  - ニューススコアリング:
    - from datetime import date
      import duckdb
      from kabusys.ai import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026, 3, 20), api_key="sk-...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, date(2026, 3, 20), api_key="sk-...")
- MonitoringEngine（統合モニタ）
  - MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager を束ね、run() で定期ポーリングします。
  - テスト用に1回だけ評価する場合は MonitoringEngine.run_once() を使用可能。

重要な動作モード / 設定（要点）
- KABUSYS_ENV:
  - development: 開発用
  - paper_trading: ブローカークライアントを Mock に切り替え、発注 DB を data/paper_trading.db に分離
  - live: 本番運用
- PAPER_FILL_MODE（paper_trading 時）
  - instant / partial / never / reject（MockBroker の約定挙動を制御）
- Kill Switch:
  - RiskMonitor などが一定条件を満たした場合、KillSwitch が data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 起動時に kill.flag を自動消去する設定（kill_flag_clear_on_start）があります（Settings 参照）。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。psutil の権限により失敗することがありますが警告でスキップされます。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env ロード、Settings クラス（各種設定プロパティ）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 単体のポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/
    - execution_engine.py — ExecutionEngine（発注 / ドレイン / シグナル処理）
    - order_manager.py — 発注ワークフロー（create/send/sync/cancel）
    - order_repository.py — （コードベース中に参照あり：Order repository / SQLite）
    - reconciler.py — 起動時リコンシリエーション
    - risk_manager.py — 実行時レート制限 / CircuitBreaker / Gate チェック
    - broker_factory.py / broker_api.py — ブローカー抽象 / ファクトリ（Mock/実ブローカー切替）
  - monitoring/
    - monitoring_db.py — SQLite による監視ログテーブル初期化・読み書き
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス PID 監視
    - trade_monitor.py — 注文滞留・約定価格異常の検出
    - risk_monitor.py — ドローダウン / ポジション上限の監視
    - kill_switch.py — kill.flag の作成・判定ユーティリティ
    - alert_manager.py — LINE 送信ユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード（起動コマンドあり）
  - portfolio/
    - portfolio_builder.py — 候補選定・スコア降順フィルタ
    - position_sizing.py — 株数算出・単元丸め・aggregate cap 対応
    - risk_adjustment.py — セクターキャップ・レジーム乗数等
  - research/
    - factor_research.py — momentum/volatility/value などのファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - __init__.py — 便利関数の公開
  - ai/
    - news_nlp.py — raw_news → OpenAI による銘柄別センチメント生成と ai_scores 書込み
    - regime_detector.py — ETF MA200 + マクロニュース（OpenAI）で market_regime を判定
    - __init__.py — ai API の公開
  - monitoring/、execution/ 等の詳細ファイルは上記参照

注意点 / 運用上の補足
- OpenAI API を使う処理（news_nlp / regime_detector）は外部 API 呼び出しのため、API キーとレート制限に注意してください。失敗時はフォールバック（多くはスコアを 0 にする／処理スキップ）して継続する設計になっています。
- run_monitoring の MONITOR_POLL_INTERVAL は環境変数で上書き可能（デフォルト 60 秒）。0 や負の値は無効でデフォルトにフォールバックされます。
- 実運用では PID ファイルや kill.flag の取り扱いを運用手順としてドキュメント化することを推奨します。
- Monitoring の DB 初期化関数 init_monitoring_db は冪等（既存テーブルを壊さない）設計です。初回起動でテーブルを作成します。
- Paper trading を使用すると本番用 DB と完全分離されるため、テスト運用に便利です。

簡単なトラブルシュート
- .env が読み込まれていないと Settings のプロパティ（必須キー）が ValueError を投げます。KABUSYS_DISABLE_AUTO_ENV_LOAD を確認し、必要なら .env を明示的に読み込むか環境変数で設定してください。
- psutil による優先度設定で AccessDenied が出る場合は権限を確認してください（警告で継続）。
- DuckDB のテーブルや raw_news 等のスキーマは research / ai モジュールで仮定された列が存在することを前提にしています。事前に ETL / データ取り込み処理を実行してください。

---

この README はコードベースの主要点をまとめたものであり、詳細な API ドキュメントや運用手順（監視オンコール手順、バックアップ、DB マイグレーション手順など）は別途用意することを推奨します。必要であれば、特定のモジュール（例えば ExecutionEngine の逐次フローや ai.news_nlp のプロンプト仕様）についてより詳細なドキュメントを作成します。
KabuSys — README
以下は、このコードベース (KabuSys) の概要・使い方・セットアップ手順・ディレクトリ構成の説明です。日本語で要点をまとめています。

プロジェクト概要
- KabuSys は日本株自動売買のためのシステム基盤（シグナル→発注→監視→リコンシリエーション／検証ツール群）です。
- DuckDB を使ったリサーチ（ファクター計算・特徴量解析）、SQLite を使ったモニタリング / 発注ログ、ExecutionEngine を中心とした発注フロー、LLM を使ったニュースセンチメント評価などを含みます。
- 環境別に挙動を切り替える設計（development / paper_trading / live）。paper_trading 環境ではモックブローカー／専用 DB を使い本番 DB と切り離します。

主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントの抽象化と OrderManager による注文ライフサイクル制御
  - 起動時リコンシリエーション（Reconciler）によりクラッシュ後の自動復旧
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねて定期実行する MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard を永続化する MonitoringDB
  - LINE によるアラート送信（AlertManager）、kill.flag による強制停止（KillSwitch）
  - Streamlit ダッシュボード（streamlit_dashboard.py）で監視情報可視化
- Portfolio construction / sizing
  - 候補選定（select_candidates）、等重・スコア重み付け、ポジションサイズ計算、セクター制限、レジーム乗数適用
- Research
  - DuckDB 上でのファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（LLM）連携
  - ニュース記事のセンチメントを OpenAI API で評価して ai_scores に格納（news_nlp）
  - マクロニュース＋ETF MA200 を合成して市場レジームを判定し market_regime に書き込む（regime_detector）
- ツール
  - Paper Trading データの検証レポート出力スクリプト（tools/paper_verification_report.py）

前提 / 必要条件
- Python 3.10 以上（型注釈の表記に合わせるため推奨）
- system-level: sqlite3（標準ライブラリ）、DB ファイル用の書き込み権限
- 推奨 Python パッケージ（pip インストール）
  - duckdb
  - psutil
  - openai（OpenAI SDK）
  - requests
  - streamlit（ダッシュボードを使う場合）
- それぞれの OS によってプロセス優先度や CPU affinity の挙動が異なります（utils/process_priority.py が抽象化しています）。

環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定なら送信しない）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行管理用ファイルパス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます

自動 .env ロード
- プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索して .env / .env.local を自動で読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。

セットアップ手順（例）
1. リポジトリをクローンして src をパスに含める（またはパッケージとしてインストール）
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （ローカルで requirements.txt があれば pip install -r requirements.txt）
4. 環境変数を設定（.env を作成）
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=paper_trading
     PAPER_FILL_MODE=instant
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
5. データディレクトリを作成
   - mkdir -p data
   - （必要に応じて空のファイル execution.pid や stop_requested.flag を利用）
6. DB 初期化は各起動スクリプト内で行われる（init_monitoring_db が冪等にテーブル作成を行います）。

基本的な使い方（実行コマンド例）
- Monitoring を起動（ポーリングして監視を行う）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は data/stop_requested.flag の作成で終了を検出します
- ExecutionEngine を起動（発注エンジンを動かす）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に書き込みます
  - 実行停止は data/stop_requested.flag を作成することで指示できます
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- AI / リサーチ機能（プログラム内で利用）
  - 例: from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key=...)
  - regime_detector の score_regime(conn, target_date, api_key=...)

運用上のポイント
- paper_trading は本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（設定に注意）。
- stop フラグ / kill.flag / pid ファイルによるプロセス管理を行います（data ディレクトリを利用）。
- OpenAI 呼び出しはリトライロジック・レスポンス検証を実装しており、API キー未設定時は明示的なエラーまたはフェイルセーフ動作をします。
- psutil を使ったプロセス優先度設定はプラットフォーム差を吸収しますが権限不足で警告が出る場合があります。

主要ファイル・ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py (パッケージ定義, __version__)
  - config.py (環境変数 / Settings クラス、.env 自動ロード)
  - run_monitoring.py (SystemMonitor のポーリング起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング -> ai_scores)
    - regime_detector.py (マクロ+MA200 による市場レジーム判定)
  - monitoring/
    - monitoring_db.py (SQLite スキーマ + MonitoringDB ラッパ)
    - system_monitor.py (CPU/メモリ/ディスク/データ鮮度/プロセス監視)
    - trade_monitor.py (滞留注文 / 約定価格異常検知)
    - risk_monitor.py (ドローダウン / ポジション上限監視)
    - kill_switch.py (kill.flag 管理)
    - alert_manager.py (LINE 通知)
    - monitoring_engine.py (3 つのモニタ統合)
    - streamlit_dashboard.py (Streamlit ベースの可視化)
  - execution/
    - reconciler.py (起動時の注文・ポジション再照合)
    - order_manager.py (Order 管理と発注フロー)
    - （その他 broker_factory, execution_engine, order_repository 等、発注処理関連）
  - portfolio/
    - portfolio_builder.py (候補選定・重み計算)
    - risk_adjustment.py (セクター上限・レジーム乗数)
    - position_sizing.py (株数計算・単元丸め・キャップ適用)
  - research/
    - factor_research.py (momentum/volatility/value 等のファクター計算)
    - feature_exploration.py (将来リターン・IC・統計サマリー)
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity ユーティリティ)
  - data/（実行時に使うディレクトリ、README ではリポジトリに含めないこと）
    - monitoring.db（デフォルト）
    - paper_trading.db（paper_trading 環境）
    - kabusys.duckdb（DuckDB ファイル）
    - execution.pid, stop_requested.flag, kill.flag（運用用フラグ / PID）

テスト / 開発
- 各モジュールは純粋関数や依存注入を意識した設計になっているため、ユニットテストが書きやすい構造です（例: OpenAI API 呼び出し箇所をテスト時にモック化）。
- .env の自動ロードはプロジェクトルート探索に依存するため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境を制御できます。

よくある運用コマンドまとめ
- 監視開始: python -m kabusys.run_monitoring
- エンジン開始: python -m kabusys.run_execution
- ダッシュボード: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
- 本 README はコードベースに含まれる docstring / コメントを基に作成しています。実際の運用では .env.example を参照して環境変数を設定し、権限やネットワーク（API キー、ブローカ接続）を事前に確認してください。
- セキュリティ: API キーやパスワードは .env やシークレットマネージャに安全に保管し、公開リポジトリに含めないでください。

必要であれば、以下を追加で作成できます
- requirements.txt（プロジェクトに合わせて推奨バージョンを固定）
- .env.example（必須・任意の環境変数のテンプレート）
- 運用手順（systemd / supervisor / Docker Compose を使ったプロセス管理の例）
- より詳しい各モジュールの API ドキュメント（関数引数・戻り値の表）
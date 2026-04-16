KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムを想定したコードベースです。  
主要コンポーネントは以下です。

- Execution Engine：発注・注文管理・リスク管理・リコンシリエーション
- Monitoring：システム状態・注文状態・リスクを監視しアラートや停止フラグを発行
- Research / Portfolio：ファクター計算・特徴量解析・銘柄選定・ポジションサイズ計算
- AI モジュール：ニュース NLP を用いた銘柄センチメント評価、レジーム判定（OpenAI）
- Tools：Paper Trading 用の検証レポート等の実用ユーティリティ
- DB 層：SQLite（監視ログ等）と DuckDB（価格・ファイナンスデータ等）

機能一覧
--------
主な機能（抜粋）：

- 発注フロー（OrderManager）とブローカークライアント抽象化（BrokerAPIProtocol）
- ExecutionEngine：起動・停止・バックグラウンド実行の管理、リスク管理（RiskManager）
- リコンシリエーション（Reconciler）：再起動時の注文・ポジション突合
- 監視コンポーネント：
  - SystemMonitor：CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor：滞留注文、約定価格の異常検知
  - RiskMonitor：ドローダウン・ポジション上限監視
  - AlertManager：LINE への通知（クールダウン付き）
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）書き込み
  - MonitoringEngine：上記を束ねたポーリングループ
- Paper Trading：
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading.db に隔離して記録
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成
- Research：
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリ
- AI：
  - news_nlp.score_news：OpenAI を用いた銘柄別ニュースセンチメント付与（ai_scores テーブルへ）
  - regime_detector.score_regime：ETF MA とマクロニュースを統合した市場レジーム判定
- ユーティリティ：
  - process_priority：プロセス優先度 / CPU affinity 設定ユーティリティ
  - streamlit ベースの監視ダッシュボード（read-only で SQLite を表示）

前提・必要環境
--------------
- Python 3.9+（typing / annotations を用いているため 3.9 以上を推奨）
- pip install 可能な環境
- 必要な Python パッケージ（主なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite は組み込みのため追加インストール不要

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - プロジェクトルート配下に `data/` ディレクトリが作成されます（なければ自動作成される箇所もある）。
2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
4. 環境変数設定
   - 必須（運用機能に依存するもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - その他の主な環境変数（省略時はデフォルトを使用）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
     - PID_FILE_PATH / KILL_FLAG_PATH など（デフォルトは data 以下）
   - .env / .env.local をプロジェクトルートに置くことで自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）
5. DB 初期化
   - 監視用テーブルは run_monitoring/run_execution 等の起動時に自動作成（init_monitoring_db）されます。
   - DuckDB のスキーマ（prices_daily, raw_financials 等）は別途用意する必要があります（外部データ取り込み処理を想定）。

使い方（起動・主要コマンド）
----------------------------
- 実行エンジンを起動（本番／開発）
  - KABUSYS_ENV によって本番 DB と paper_trading の切り替えがされます。
  - 例（Linux/macOS）:
    - export KABUSYS_ENV=development
    - python -m kabusys.run_execution
  - Paper Trading:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - （paper_trading 環境では MockBrokerClient が動作し、PAPER_TRADING_SQLITE_PATH に記録されます）

- 監視プロセス（Monitoring）を起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（秒）
  - 例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定することも可能

- 監視ダッシュボード（Streamlit）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - データベースは read-only モードで開かれます。MonitoringEngine が書き込む監視 DB を参照表示します。

- AI モジュール（ニューススコア / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - api_key を渡すか、OPENAI_API_KEY を環境変数で設定してください
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に API キーが必要
  - これらは DuckDB 接続を受け取り、内部で ai_scores / market_regime テーブルへ書き込みます

- 停止フラグと停止処理
  - 実行プロセスの停止制御はフラグファイルで行われます:
    - data/stop_requested.flag: run_execution / run_monitoring のループを終了させる（存在を検出すると終了）
    - data/kill.flag: KillSwitch が書き込み、ExecutionEngine 停止を誘発するために使用
  - kill.flag は KillSwitch.clear() で削除可能（Execution 起動時にクリーンアップする設定あり）

設定例（.env の例）
------------------
（プロジェクトルートに .env を置く例）
- .env.example（実際のファイルは .env として作成してください）
  - JQUANTS_REFRESH_TOKEN=your_token_here
  - KABU_API_PASSWORD=your_password_here
  - OPENAI_API_KEY=sk-...
  - KABUSYS_ENV=development
  - SQLITE_PATH=data/monitoring.db
  - DUCKDB_PATH=data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - MONITOR_POLL_INTERVAL=60

注意事項 / 運用メモ
-------------------
- Monitoring のログやテーブルは run_monitoring / run_execution 起動時に自動で初期化・マイグレーションされます（init_monitoring_db）。
- Paper Trading 環境は本番 DB と完全分離する設計です（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI など外部 API を使う機能は API キー・レート制限に注意してください。失敗時はフェイルセーフ（デフォルトスコア、ログ記録など）で継続する設計になっています。
- プロセス優先度の設定（set_process_priority）は OS によっては権限不足で失敗することがあり、その場合はワーニングが出力されます（処理は継続）。

主要ディレクトリ構成（抜粋）
---------------------------
src/kabusys/
- __init__.py                     — パッケージ定義、バージョン
- config.py                       — 環境変数 / Settings 管理（.env 自動ロード含む）
- run_execution.py                — ExecutionEngine 起動スクリプト（KABUSYS_ENV に対応）
- run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py   — Paper Trading 検証レポート生成 CLI
- execution/
  - order_manager.py               — 発注の外向き API
  - reconciler.py                  — 起動時のリコンシリエーション
  - ...                            — ブローカー抽象・Engine 等（未列挙ファイルあり）
- monitoring/
  - monitoring_db.py               — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py              — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py               — 滞留注文・約定異常検出
  - risk_monitor.py                — ドローダウン・ポジション数監視
  - kill_switch.py                 — kill.flag 書き込みユーティリティ
  - alert_manager.py               — LINE への通知送信（クールダウン管理）
  - monitoring_engine.py           — 各監視を束ねるエンジン
  - streamlit_dashboard.py         — Streamlit ダッシュボード（read-only）
- portfolio/
  - portfolio_builder.py           — 候補選定・重み計算
  - position_sizing.py             — 株数決定・単元丸め・資金割当
  - risk_adjustment.py             — セクターキャップ・レジーム乗数
- research/
  - factor_research.py             — momentum/volatility/value の計算（DuckDB 使用）
  - feature_exploration.py         — 将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py                    — ニュースを OpenAI で評価し ai_scores に書き込む
  - regime_detector.py             — 市場レジーム判定（ETF + マクロニュース）
- utils/
  - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ
- data/                            — 実行時生成される DB・PID・フラグファイル等（リポジトリにない場合は起動時に作成される箇所があります）

ライセンス / 貢献
-----------------
- 本リポジトリのライセンスは明記されていないため、利用前にライセンスを確認してください。  
- バグ報告や改善提案は Issue / PR を送ってください（実運用では安全性・金銭リスクに関する注意が必要です）。

問い合わせ・補足
-----------------
必要であれば、起動例のスクリーンキャプチャ、.env.example の完全版、docker / systemd ユニットの例、DuckDB 用のテーブルスキーマ（prices_daily / raw_financials / raw_news 等）のテンプレートを追加します。どれを優先して欲しいか教えてください。
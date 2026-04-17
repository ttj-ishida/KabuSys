# KabuSys

KabuSys は日本株の自動売買・調査・監視のためのコンポーネント群です。本リポジトリは以下の機能を含む小さなモジュール群で構成されています: 注文実行エンジン、監視デーモン、ポートフォリオ構築・ポジションサイジング、ファクター計算、ニュース NLP（OpenAI）連携、ストリーミングダッシュボードなど。

以下はこのコードベースの概要・セットアップ・起動方法・ディレクトリ構成の説明です。

プロジェクト概要
- 目的: 日本株の自動売買システム（実行・監視・研究）の基盤的コンポーネントを提供
- 主要コンポーネント:
  - ExecutionEngine（発注・リスク管理・リコンシリエーション）
  - MonitoringEngine（システム状態・注文異常・リスク監視）
  - Portfolio construction（候補選定・重み計算・ポジションサイズ算出）
  - Research（ファクター計算・特徴量解析）
  - AI（ニュースセンチメント、レジーム検出 — OpenAI を利用）
  - Tools（Paper Trading 検証レポート出力、Streamlit ダッシュボードなど）

主な機能一覧
- 発注・注文状態管理（OrderManager / OrderRepository）
- ブローカー抽象化（本番 or PaperTrading 用の切替）
- 起動時リコンシリエーション（Reconciler）
- リスク管理（RiskManager、RiskMonitor）
- 監視（SystemMonitor、TradeMonitor、MonitoringEngine）
- 監視ログ永続化（SQLite via MonitoringDB）
- ニュース NLP による銘柄センチメント（OpenAI 利用、ai/news_nlp.py）
- 市場レジーム判定（ai/regime_detector.py）
- ファクター計算（research/factor_research.py）
- ポートフォリオ構築（portfolio/*）
- Streamlit ダッシュボード（監視データの可視化）
- 検証レポート生成ツール（tools/paper_verification_report.py）

セットアップ手順（開発向け）
1. システム要件
   - Python 3.10 以上（PEP 604 の型注釈やその他機能を使用）
   - SQLite（標準ライブラリに含まれる）
   - DuckDB（duckdb パッケージ）
   - 追加依存: psutil, openai, requests, streamlit（ダッシュボード利用時）
2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール
   - もし requirements.txt があるなら:
     - pip install -r requirements.txt
   - なければ最低限次をインストール:
     - pip install duckdb psutil openai requests streamlit
4. プロジェクトルートに data ディレクトリを用意
   - mkdir -p data
   - 実行時に PID/flag/DB ファイルが data/ 以下に作成されます
5. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成して必要な環境変数を設定できます。自動ロード機能が有効（デフォルト）。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（代表）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルトは development。
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な機能がある場合）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 監視アラートを LINE に送る場合
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper trading の fill 模擬モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

注意点
- Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番用の監視 DB）を使用する実装です。
- Execution エンジンは KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と完全に分離）。
- OpenAI を使うモジュールは API キーが必要です。key 未設定時は ValueError を投げる関数があります。

使い方（起動 / 実行）
- 監視ループを起動（デーモン的に監視を回す）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で上書き可（例: MONITOR_POLL_INTERVAL=30）
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します
- 実行エンジンを起動（注文処理を行う）
  - python -m kabusys.run_execution
  - Paper Trading モード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - PaperTrading の場合は data/paper_trading.db に記録され、本番 DB とは分離されます
  - 実行中の安全停止:
    - 実行ループは data/stop_requested.flag と data/kill.flag を参照し、停止や外部指示の発火を行います
- Streamlit ダッシュボードを起動（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - またはコマンドラインで --db オプションに読み取り専用 DB を指定
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db でカスタム DB を指定可能（デフォルト: data/paper_trading.db）
- AI 関連関数（プログラムから呼び出す例）
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)
  - 上記は OPENAI_API_KEY が必要（関数引数で渡しても可）

運用上のファイル・フラグ
- data/execution.pid: ExecutionEngine が自身の PID を書き込むファイル
- data/stop_requested.flag: run_* スクリプトがポーリング中に検出すると優雅に終了するためのフラグ
- data/kill.flag: KillSwitch が書き込むと ExecutionEngine に強制停止シグナルを送る（停止理由の文字列がファイル内容）
- monitoring DB（SQLite）: data/monitoring.db（init_monitoring_db() により自動で必要テーブルが作成されます）
- paper trading DB（SQLite）: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポートツール
  - ai/
    - news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py          — 市場レジーム判定（OpenAI と価格データ）
  - monitoring/
    - monitoring_db.py            — SQLite ベースの永続層（テーブル初期化含む）
    - system_monitor.py           — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py            — 注文滞留・約定異常監視
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag の生成・管理
    - alert_manager.py            — LINE 通知ラッパー
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py      — Streamlit ダッシュボード（監視表示）
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他発注関連モジュール)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/ (想定: 実行時に生成されるファイル群)
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid, kill.flag, stop_requested.flag

サンプル .env（最低限必要なキーの例）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- LOG_LEVEL=INFO

運用上の注意
- KABUSYS_ENV を live にして実際のブローカーと接続する際は十分に注意してください。設定ミスや権限不足による誤発注のリスクがあります。
- OpenAI を利用する機能は API リクエストが発生します（料金・レート制限に注意）。
- monitoring は監視 DB を直接更新します。DB ファイルのバックアップや保護を運用ポリシーに合わせて検討してください。
- run_execution/run_monitoring は stop_requested.flag を見ることで安全に終了できます。強制停止の際はフラグファイルや PID を確認してください。

よくある操作例
- 監視を手動で1回だけ実行して確認（テスト用）
  - Python から MonitoringEngine を組み立て run_once() を呼ぶ（テストコード内での利用を想定）
- 監視ダッシュボードを立ち上げて状態確認
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

さらに知りたい場合・拡張
- PortfolioConstruction.md / StrategyModel.md のような設計ドキュメント（コード内コメントで参照あり）が存在する想定です。戦略やポジション算出ルールを変更する際は portfolio/* と research/* を参照してください。
- OpenAI との API 呼び出しは _call_openai_api をモックすることでユニットテスト可能な設計になっています。

この README はコードベースの主要点をまとめたものです。実際の導入・運用時は環境変数と data ディレクトリ、権限・バックアップ方針を事前に整えてください。必要なら README に追記したい具体的な運用手順や Docker 化、CI/CD 用の設定例などをご依頼ください。
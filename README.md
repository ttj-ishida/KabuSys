KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・研究・監視機能群をまとめたモジュール群です。  
主要なコンポーネントは ExecutionEngine（発注実行）、Monitoring（稼働監視・アラート）、Research / Portfolio（因子計算・ポートフォリオ構築）、AI モジュール（ニュース NLP / レジーム判定）、およびユーティリティ群です。

要点
- Python のモジュール群として設計（src/kabusys 以下）
- SQLite + DuckDB を利用したローカル DB（デフォルトは data/ 配下）
- Paper Trading モードでは本番 DB とは分離された専用の SQLite を使用
- OpenAI を用いたニュースセンチメント／レジーム判定機能あり（OPENAI_API_KEY 必須）
- 監視は LINE Push による通知が可能（LINE のトークン設定が必要）

機能一覧
- 実行系
  - ExecutionEngine 起動・発注管理（run_execution.py）
  - Broker クライアントの抽象化（本番 / モック切り替え）
  - 再起動時のリコンシリエーション（Reconciler）
  - OrderManager による状態管理・重複防止等
- 監視系
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存確認 / データ鮮度チェック
  - TradeMonitor：滞留注文検出・約定異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringEngine：各モニタのポーリング実行、KillSwitch 評価、AlertManager 経由で通知
  - Streamlit ダッシュボード（簡易 UI）
- 研究・ポートフォリオ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量解析・IC 計算
  - 候補選定・配分（等配分・スコア加重）・ポジションサイズ計算
  - セクター制限・レジーム乗数
- AI（OpenAI）
  - news_nlp: raw_news → 銘柄別センチメント（ai_scores へ書き込み）
  - regime_detector: ma200 + マクロニュースセンチメントを合成して market_regime を算出
- ツール
  - paper_verification_report: Paper Trading DB を読み取り検証レポート出力

セットアップ手順（ローカル開発向け）
- 推奨 Python バージョン: 3.10 以上（型ヒントに | を使用）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
  - sqlite3 は標準モジュール
- インストール例（仮想環境推奨）
  1. 仮想環境の作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
  2. パッケージのインストール
     - pip install duckdb psutil requests openai streamlit
     - （必要に応じて他パッケージを追加）
- 環境変数 / .env の準備
  - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（OS 環境変数が優先）。
  - 自動読み込みを無効化する場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - 主要な環境変数（例とデフォルト）
    - KABUSYS_ENV: environment（development | paper_trading | live） — デフォルト: development
    - JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
    - KABU_API_PASSWORD: （必須）kabuステーション API パスワード
    - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定時は通知をスキップ）
    - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
    - SQLITE_PATH: data/monitoring.db（デフォルト、Monitoring DB）
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（Paper Trading 用 DB）
    - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動、デフォルト: instant）
    - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
    - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視関連設定

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数・.env ロード、Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py — 市場レジーム判定（ma200 + macro sentiment）
  - monitoring/
    - monitoring_db.py — monitoring DB の初期化と永続化 API
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
    - monitoring_engine.py — 監視ポーリングの取りまとめ
    - alert_manager.py — LINE 通知ラッパー
    - kill_switch.py — kill.flag の作成（Execution 停止）
    - streamlit_dashboard.py — Streamlit で監視ダッシュボードを起動
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, execution_engine.py 等（発注関連）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py（構成ロジック）
  - research/
    - factor_research.py, feature_exploration.py（ファクター計算／統計）
  - data/ （想定データディレクトリ）
    - monitoring.db（デフォルトの監視 SQLite）
    - paper_trading.db（Paper Trading 用）
    - kabusys.duckdb（DuckDB データベース）
  - tools/
    - paper_verification_report.py — paper_trading DB の検証レポートジェネレータ

データベース（デフォルト）
- SQLite（監視ログ）: data/monitoring.db
  - テーブル: system_status, trade_logs, positions, risk_logs, dashboard（init_monitoring_db が自動作成）
- DuckDB（時系列データ、prices_daily / raw_financials / raw_news 等）: data/kabusys.duckdb
- Paper Trading 用 SQLite（paper_trading モード）: data/paper_trading.db（Execution は環境が paper_trading の場合こちらを使用）

起動・使い方（主要コマンド）
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - run_monitoring は data/stop_requested.flag の存在を監視し、存在すれば終了します
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します
  - Execution は data/stop_requested.flag を検知すると安全に停止します
- Streamlit ダッシュボード起動（監視 DB を読み取り専用で開く）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
- AI 機能（OpenAI 必須）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を直接呼び出して利用
  - OPENAI_API_KEY を環境変数に設定するか、関数に api_key を渡してください
  - モデルは gpt-4o-mini を想定しています（コード内で定義）

停止・制御フラグ
- 起動中のプロセスを即時停止させたい場合:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のスクリプトが検知して停止します
- 自動停止判定（Kill Switch）
  - RiskMonitor が条件を満たした場合（ドローダウン超過等）、KillSwitch が data/kill.flag を書き込みます
  - ExecutionEngine 起動時に Settings.kill_flag_clear_on_start が 1 であれば起動時に kill.flag をクリアできます
- PID 管理
  - ExecutionEngine は data/execution.pid に PID を書きます。SystemMonitor はこの PID を検査してプロセス生存を確認します

重要な実装メモ（運用上の注意）
- .env の自動読み込み順:
  - OS 環境変数 > .env.local > .env（プロジェクトルートに .git または pyproject.toml があることを検出して自動読み込み）
- MonitoringDB の初期化は冪等（init_monitoring_db）
- Paper Trading は本番 DB と完全に分離されるよう設計
- OpenAI への繰り返し呼び出しは指数バックオフ・JSON 検証を行う。API キー未設定時は明示的に ValueError を出します
- プロセス優先度を起動直後に "high" に設定する処理が各 run スクリプトに含まれます（環境によって権限が必要 / 失敗時は警告）

例: .env（最小例）
- 以下は最低限必要な環境変数の例（値は適宜書き換えてください）。
  - KABUSYS_ENV=development
  - JQUANTS_REFRESH_TOKEN=your_jquants_token
  - KABU_API_PASSWORD=your_kabu_password
  - OPENAI_API_KEY=sk-...
  - LINE_CHANNEL_ACCESS_TOKEN=...
  - LINE_USER_ID=...
  - SQLITE_PATH=data/monitoring.db
  - DUCKDB_PATH=data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

開発・デバッグ
- 単体関数群（portfolio, research, ai の一部）は DB によらずメモリ計算のみの純関数として実装されているため単体テストが容易です
- MonitoringEngine.run_once() を使えば単発チェックのみ実行できます（テスト用）
- OpenAI 呼び出し部分は関数単位で差し替え（モック）しやすい設計になっています（テスト用に patch 推奨）

ライセンス / その他
- 本 README ではコードの要点と運用手順をまとめています。実際の運用では証券会社 API の利用規約や取引リスクに十分注意して下さい。

補足 — よく使うコマンドまとめ
- 監視起動: python -m kabusys.run_monitoring
- 実行起動: python -m kabusys.run_execution
- Paper 検証: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

質問・改善提案があれば教えてください。README に含めたい追加の使用例や具体的な運用手順（サービス化、systemd ユニット例、コンテナ化など）があれば追記します。
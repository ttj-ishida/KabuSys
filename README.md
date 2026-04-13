# KabuSys

KabuSys は日本株の自動売買および周辺ツール群のコアライブラリです。本リポジトリには以下の機能群が含まれます: 注文実行エンジン（ExecutionEngine）、監視（Monitoring）サブシステム、ポートフォリオ構築ロジック、リサーチ／ファクター計算、AI を使ったニュースセンチメント評価など。

以下はこのコードベースの README（日本語）です。

※本リポジトリのソースは src/kabusys 以下に配置されています。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / 依存関係
- セットアップ手順
- 環境変数（主要）
- 実行方法（使い方）
- ディレクトリ構成（主要ファイルの説明）
- 運用上の注意点

---

プロジェクト概要
- 日本株向けの自動売買システムのコアライブラリです。
- ブローカー接続（kabuステーション等）をラップした Execution Engine、監視（System / Trade / Risk）やアラート、Streamlit ベースの監視ダッシュボード、ポートフォリオ構築・サイズ決定ロジック、ファクター計算・リサーチ、OpenAI を利用したニュース NLP / レジーム判定機能を提供します。
- DB 永続化は SQLite（監視用）と DuckDB（価格・ファクター計算用）を利用します。

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / Paper Trading の切り替えに対応。Paper Trading は専用 SQLite（data/paper_trading.db）を使用し本番 DB と分離。
  - BrokerClientFactory を通じて実際のブローカー or MockBroker を利用。
  - リスクマネージャ、注文管理、リコンシリエーションなどの組み立てを行う。
- Monitoring（監視）サブシステム
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度を監視しログ化。
  - TradeMonitor: 注文の滞留、約定価格の異常などを検出しログ/リスクイベント登録。
  - RiskMonitor: ドローダウン・保有銘柄数上限を監視し、kill flag 書き込み等。
  - AlertManager: LINE Messaging API へのプッシュ通知（クールダウン管理あり）。
  - MonitoringEngine: 上記を定期ポーリングでまとめて実行。
  - Streamlit ダッシュボード: 監視 DB を可視化。
- ai.news_nlp / ai.regime_detector
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄別）評価とマクロセンチメントに基づく市場レジーム判定。ai_scores / market_regime テーブルへ書き込み。
- portfolio モジュール
  - 候補選定、重み算出（等金額／スコア加重）、セクターキャップ適用、ポジションサイズ計算（単元丸め・aggregate cap）等の純粋関数群。
- research モジュール
  - DuckDB を用いたファクター計算（momentum/value/volatility）・将来リターン計算・IC 計算など。
- tools
  - paper_verification_report: Paper Trading の検証レポートを SQLite（paper_trading.db）から生成。

前提条件 / 依存関係
- Python 3.10 以上（ソース内で X | Y 型アノテーションを使用）
- 主要ライブラリ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- 標準ライブラリ: sqlite3, logging, pathlib 等

セットアップ手順（簡易）
1. リポジトリをクローンし、作業ディレクトリへ
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があればそれを使ってください）
4. データディレクトリを作成
   - mkdir -p data
5. 環境変数を設定（.env ファイルをプロジェクトルートに置くと自動読み込みされます）
   - 自動ロード条件: プロジェクトルートは .git または pyproject.toml を基準に検出されます
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
6. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...           （AI 機能使用時に必須）
   - LINE_CHANNEL_ACCESS_TOKEN=...（アラート送信に必要）
   - LINE_USER_ID=...
   - KABUSYS_ENV=development | paper_trading | live
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - PAPER_FILL_MODE=instant | partial | never | reject
   - LOG_LEVEL=INFO / DEBUG / ...
   - MONITOR_POLL_INTERVAL（秒。監視ループの間隔。既定 60）

実行方法（使い方）
- ExecutionEngine を起動（実運用・Paper 切り替えは KABUSYS_ENV で制御）
  - python -m kabusys.run_execution
  - 動作: プロセス優先度を "high" に設定 → 設定に応じた SQLite（paper_trading 時は専用 DB）と DuckDB に接続 → ExecutionEngine 実行
- Monitoring を起動（監視ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）
  - 監視は monitoring 用の sqlite_path（Settings.sqlite_path）に常にアクセスします（KABUSYS_ENV に関係なく本番設定の sqlite_path を使用）
- Streamlit ダッシュボード（ローカルで可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - もしくはダッシュボード内の --db オプションで DB パスを指定
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - あるいは --db オプションで別ファイルを指定
- AI 関連（ニューススコア/レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（OPENAI_API_KEY）を必要とします。キーが未設定だと ValueError を返します。

主要な動作挙動のポイント
- .env 読み込み
  - プロジェクトルート（.git または pyproject.toml）を起点に .env と .env.local を自動読み込みします（OS 環境変数を優先、.env.local は .env を上書き）。
  - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。
- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、run_execution は MockBrokerClient を使用し、別 DB（PAPER_TRADING_SQLITE_PATH）へすべての発注ログを記録して本番 DB と完全に分離します。
  - PAPER_FILL_MODE によりモック約定動作を制御できます（instant/partial/never/reject）。
- Kill Flag
  - KillSwitch は data/kill.flag（デフォルト）へテキストを書き込み、ExecutionEngine に停止シグナルを送ります。フラグが既に存在する場合は上書きしません。
  - ExecutionEngine 起動時にフラグを自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定してください。
- プロセス優先度
  - 起動スクリプトは start 時に set_process_priority("high") を呼びます（psutil を用い OS に依存した操作を行います）。権限不足時は警告が出てスキップされます。

ディレクトリ構成（主要ファイル / モジュールの説明）
- src/kabusys/
  - __init__.py — パッケージ定義とバージョン
  - config.py — Settings クラス（環境変数のラッパー、.env 自動ロード、各種設定値）
  - run_execution.py — ExecutionEngine 起動スクリプト（本番/ペーパートレード対応）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール（CLI）
  - execution/
    - order_manager.py — 注文作成/送信の外向き API
    - reconciler.py — 起動時のリコンシリエーション（OrderSent 照合・ポジション差分）
    - order_repository.py, order_record.py, broker_factory.py, risk_manager.py 等（注文・ブローカー関連、詳細は該当ファイル参照）
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（テーブル作成・CRUD）
    - system_monitor.py — システムの CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag を書き込むユーティリティ
    - alert_manager.py — LINE Push による通知
    - monitoring_engine.py — 上記モニタをまとめてポーリングするエンジン
    - streamlit_dashboard.py — Streamlit による可視化ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数算出・上限・単元丸め・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ等
  - ai/
    - news_nlp.py — raw_news を OpenAI に投げて銘柄別センチメントを作成し ai_scores に書き込む
    - regime_detector.py — ETF MA200 とマクロセンチメントの合成による市場レジーム判定
  - utils/
    - process_priority.py — OS 別プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/monitoring_db.py — 監視用 DB の初期化・操作（テーブル作成・マイグレーション等）

運用上の注意点
- DB マイグレーション
  - monitoring_db.init_monitoring_db(conn) は冪等で実行され、必要なテーブルとインデックスを作成します。既存 DB に対しては一部カラム追加（ALTER TABLE）で軽微なマイグレーションを行います。
- データ鮮度
  - SystemMonitor は DuckDB の prices_daily テーブルから最終価格日を参照し、データ鮮度（既定: ≤3日）をチェックします。prices_daily の更新がないとアラート対象になります。
- OpenAI / API 利用
  - OpenAI 呼び出しは外部 API に依存します。API のレート制限や一時エラーに対してはエクスポネンシャルバックオフでリトライを行う設計です（ただしリトライ上限があります）。API キーは安全に管理してください。
- Paper Trading の分離
  - Paper Trading では本番 DB に影響を与えないよう設計されていますが、設定ミスに注意してください（環境変数やパスを確認）。
- 権限
  - set_process_priority / cpu_affinity の変更は OS 権限に依存します。権限不足や未対応 OS の場合は警告が出て処理をスキップします。

最後に
- ここに説明したのはコードベースの主要機能と運用方法です。詳細実装やテスト、ブローカ連携部分（BrokerClientFactory 等）は各ファイルをご参照ください。
- 追加のドキュメント（API仕様や設計資料）はプロジェクトの別ファイル（例: PortfolioConstruction.md, StrategyModel.md 等）がある場合はそちらを参照してください。

必要でしたら README を英語版で出力したり、サンプル .env.example を作成したり、セットアップ用の requirements.txt / docker-compose のひな型を用意します。どれを作成しましょうか？
KabuSys
======

日本株向けの自動売買システムのコアライブラリ群です。
本リポジトリは、注文発行・実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、
およびニュースNLP / レジーム判定などの補助モジュールを含みます。

主な設計方針
- 実運用（live）と紙上検証（paper_trading）を環境で切り替え可能
- DuckDB を使った時系列データ処理（prices_daily / raw_financials 等）
- SQLite を監視ログ / 発注ログに利用（監視 DB は実運用 DB と分離）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（フェイルセーフ設計）
- プロセス優先度 / CPU affinity の簡易ユーティリティを提供

機能一覧
- Execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - ブローカークライアント抽象化（本番 / Mock for paper_trading）
  - OrderManager / OrderRepository / Reconciler（自動リコンシリエーション）
  - RiskManager（発注前リスク制約）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor とそれらを束ねる MonitoringEngine
  - SQLite ベースの監視 DB（init_monitoring_db, MonitoringDB）
  - KillSwitch（フラグファイルで ExecutionEngine 停止指示）
  - Streamlit ベースの監視ダッシュボード起動スクリプト
  - AlertManager（LINE Push 通知）
- Portfolio
  - 候補選定・重み付け・ポジションサイズ計算（等重、スコア重み、リスクベース）
  - セクター集中制限、レジーム乗数
- Research
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - ニュース NLP（ai.news_nlp.score_news）：OpenAI でニュースをスコアリングして ai_scores に書き込み
  - レジーム判定（ai.regime_detector.score_regime）：MA 系指標とマクロニュースセンチメントを合成
- Tools
  - paper_verification_report：Paper Trading データから検証レポートを生成

セットアップ手順（ローカル）
- 前提
  - Python 3.9+（実際の互換性はプロジェクトポリシーに従ってください）
  - 必要な Python パッケージ: duckdb, psutil, openai, requests, streamlit など

1. リポジトリをクローン、仮想環境の作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt または poetry/poetry.lock があればそれに従ってください）

3. 環境変数 / .env の準備
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）
   - 主要な環境変数（代表例）:
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須になる箇所あり）
     - KABU_API_PASSWORD: kabuステーション API パスワード（本番接続時）
     - OPENAI_API_KEY: OpenAI 呼び出しで必要（ai モジュール利用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager の通知設定
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: 紙上取引用 DB（paper_trading のときに使用、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
     - PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag のパス（デフォルト: data/...）

4. データディレクトリの作成
   - mkdir -p data

使い方（主要なスクリプト）
- 実行エンジン（ExecutionEngine）を起動
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に書き込まれます。
  - 特徴:
    - プロセス優先度を high に設定して起動します（psutil による試行）
    - PID ファイル（Settings.pid_file_path）を用いてプロセス監視 / 再起動検知に対応

- 監視ポーリングを起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
    - 監視は Settings の sqlite_path を用いて常に本番の監視 DB を参照します（KABUSYS_ENV に依らない）

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    - 監視 DB を read-only で開きダッシュボードを表示します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプションで --db PATH を指定して PAPER_TRADING_SQLITE_PATH を上書き可能

- AI モジュール（プログラム的利用）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

設定 (Settings)
- 設定は kabusys.config.Settings クラス経由で取得されます（環境変数または .env）
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env / .env.local をロード
  - OS 環境変数は保護され .env による上書きは行われません（.env.local は override=True で上書き可）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
- 主要なプロパティ（デフォルトや注意点は前述の「セットアップ」節を参照）

監視・停止（Kill Switch）
- kill.flag を書くことで ExecutionEngine に停止シグナルを送る仕組み
  - KillSwitch は RiskMonitor 等の結果に基づき評価し、必要であれば flag を作成します
  - ExecutionEngine 側は PID と kill.flag を参照して安全停止を行う想定です

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数 / 設定のロードと検証（Settings）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 単体の起動スクリプト（短周期ポーリング用）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - order_manager.py, reconciler.py, ... — 発注管理、リコンシリエーション等（Engine 関連）
  - monitoring/
    - monitoring_db.py — SQLite のスキーマ初期化 / 永続化層（MonitoringDB）
    - system_monitor.py — CPU/メモリ/Disk/データ鮮度/プロセス状態の監視
    - trade_monitor.py — 注文滞留・約定異常の検出
    - risk_monitor.py — ドローダウン監視・ポジション数上限
    - kill_switch.py — フラグファイル操作
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ベースの GUI ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定、等重・スコア重み
    - position_sizing.py — 数量計算、集約キャップ処理
    - risk_adjustment.py — セクター上限、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value の計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
  - tools/
    - paper_verification_report.py — paper_trading 用検証レポート
  - data/ (推奨ローカル格納場所)
    - kabusys.duckdb (default)
    - monitoring.db (default)
    - paper_trading.db (paper_trading 用、optional)

注意事項 / 運用上のポイント
- OpenAI 呼び出し（ai.news_nlp / ai.regime_detector）は API キーが必須です。失敗時はフォールバック動作（fail-safe）を行うよう実装されていますが、API キーを用意してください。
- paper_trading 環境では本番 DB と分離して動作します（PAPER_TRADING_SQLITE_PATH を使用）。
- プロセス優先度 / CPU affinity の設定は OS 権限に依存します。権限不足などで失敗した場合はログ警告に留まり継続します。
- DuckDB への書込みや SQLite マイグレーションは init_monitoring_db で安全に行われます。既存スキーマに対する簡易マイグレーション処理も実装されています。
- スクリプトは多くの箇所で例外を捕捉してログに出力し、システム全体の停止を防ぐ設計になっています。運用時はログの監視と LINE 通知設定を併用してください。

開発における推奨フロー
1. .env.example を元に .env を用意
2. DuckDB に prices_daily / raw_financials / raw_news 等を投入
3. paper_trading モードで Execution を動かして挙動を確認
4. Monitoring を起動して監視ログ / ダッシュボードを確認
5. AI モジュールは少量のターゲット日で手動実行してレスポンスを検証

ライセンス / 貢献
- 本 README はコードベースの抜粋から生成しています。実運用前にセキュリティ・法規面のチェックを行ってください。
- 外部 API キー（OpenAI / kabuステーション / J-Quants 等）の取り扱いは慎重に。機密情報は公開しないでください。

お問い合わせ・追加ドキュメント
- 各機能（PortfolioConstruction.md, StrategyModel.md 等）に言及するコメントがソースに含まれています。詳細設計や数式・推奨パラメータは該当ドキュメントを参照してください（プロジェクトに含まれている想定）。
- さらに具体的な README の追加/改善や運用手順書（systemd 定義, docker-compose, k8s 等）作成が必要であればお知らせください。
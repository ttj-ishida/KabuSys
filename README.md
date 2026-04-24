README — KabuSys（日本株自動売買システム）
概要
- KabuSys は日本株向けの自動売買／研究用ライブラリ兼実行フレームワークです。
- 戦略のファクター計算、ポートフォリオ構築、注文実行（本番 / ペーパートレード）、監視・アラート、LLM を使ったニュース NLP／レジーム判定、検証レポート生成などを含みます。
- モジュール設計は「DBアクセスを伴う処理」と「純粋関数（メモリ内計算）」を分離し、テストや安全運用を考慮しています。

主な機能
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）。
  - RiskManager / OrderManager / Reconciler 等を組み合わせた実行フロー。
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング監視。
  - Kill Switch（条件に応じて data/kill.flag を書いて ExecutionEngine を停止）。
  - 監視結果を SQLite に永続化。
- 研究用モジュール
  - ファクター計算（momentum, volatility, value 等） — DuckDB を用いた高速集計。
  - 特徴量探索・IC 計算・将来リターン計算。
- AI（OpenAI）連携
  - ニュースのセンチメント評価（news_nlp）と市場レジーム判定（regime_detector）。
  - API のレート制御やリトライ、レスポンス検証を実装。
- ポートフォリオ構築
  - 候補抽出、重み計算（等金額・スコア）、レジーム補正、セクター上限、株数決定（単元丸め・集計キャップ）。
- ユーティリティ
  - ログ設定（コンソール＋日次ローテーションファイル）、プロセス優先度設定、.env ウィザード、設定検証 CLI、ペーパートレード検証レポート生成。

前提・依存
- Python 3.9+ を想定（typing 機能を利用）。
- 推奨インストールパッケージ（最低限）:
  - duckdb, psutil, openai
  - 開発/一部機能: PyYAML（config 検証時に YAML パースを行う場合）
- SQLite は標準で利用（組み込み）。
- 環境によっては追加のネイティブライブラリやネットワーク接続（kabuステーション, OpenAI）が必要。

セットアップ
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成。
   - 自動ロード: kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を起点）を検出すると .env / .env.local を自動で読み込みます。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

重要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 運用系
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、発注は MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログファイル格納先（デフォルト: logs/）
- DB パス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- その他
  - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
  - PAPER_FILL_MODE — ペーパートレードでの約定挙動: instant | partial | never | reject
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)

設定検証
- 対話で .env を作成したら設定検証を実行:
  - python -m kabusys.validate_config
  - 警告をエラーとして扱いたい場合: python -m kabusys.validate_config --strict

使い方（主要コマンド）
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使用（本番 DB とは分離）
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 実行中に data/stop_requested.flag が作成されるとエンジン停止を試みる
    - 実行中は data/execution.pid に PID を書きます
    - 起動直後に KILL_FLAG_CLEAR_ON_START=1 かつ kill.flag が存在する場合に kill.flag をクリアする設定がある（Settings による）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path (SQLITE_PATH) を使用して監視データを書き込みます
  - run_monitoring は data/stop_requested.flag の存在を検知すると停止

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- 研究用 / スクリプト呼び出し
  - research モジュールの関数は DuckDB 接続を受け取る設計です（例: calc_momentum）。
  - AI 機能（news_nlp.score_news, regime_detector.score_regime）は OPENAI_API_KEY が必要です。

運用上のファイル / フラグ
- data/kill.flag — Kill Switch が作動した旨を記録。ExecutionEngine はこのファイルの存在で停止を受ける設計。
- data/stop_requested.flag — run_* スクリプトの外部停止フラグ（手動で作成するとループを終了）
- data/execution.pid — ExecutionEngine の PID を格納
- data/monitoring.db — 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard 等）
  - run_monitoring / run_execution は init_monitoring_db を呼び、必要なテーブルが存在することを保証します
- data/paper_trading.db — ペーパートレード専用 DB（paper_trading モード時に使用）

ログ
- デフォルトログディレクトリ: logs/
- setup_logging を各起動スクリプトで呼んでおり、stdout（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler）を設定します。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py              — 環境変数／設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 起動前の設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py           — ニュースの LLM センチメント評価（ai_scores 書込）
    - regime_detector.py    — レジーム判定（ma200 + マクロ NLP）
  - research/
    - factor_research.py    — ファクター計算（momentum/volatility/value）
    - feature_exploration.py— 将来リターン / IC / 統計サマリー
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 株数決定・集計キャップ
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py      — 監視用 SQLite 永続化層
    - system_monitor.py     — システム/データ鮮度監視
    - trade_monitor.py      — （注文ログ等の監視）※実装参照
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - monitoring_engine.py  — Monitor を束ねる実行ループ
    - kill_switch.py        — Kill Switch 実装（kill.flag 書込み）
    - alert_manager.py      — （アラート送信：LINE 等の実装参照）
  - execution/
    - execution_engine.py   — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - broker_factory.py     — 本番 / Mock ブローカー生成
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - data/                  — 既定の data 配下ファイル（DB / flags）は実行時に作成されます（.gitignore で除外推奨）

実運用上の注意
- 本番（KABUSYS_ENV=live）では設定に細心の注意を払い、validate_config で警告・エラーを確認してください。
- kill.flag / stop_requested.flag は運用者による重要な制御手段です。KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険です（デフォルト 0 を推奨）。
- OpenAI 利用時のコスト・レート制限に注意してください。API キーは安全に管理してください。
- DuckDB / SQLite のファイルパスは適切なバックアップ方針に従ってください（特に本番データ）。

お問い合わせ・拡張
- 新しいストラテジーやリスクルールを追加する場合、portfolio/* と execution/* のインターフェースに従って実装してください（pure function の分離・ユニットテスト容易性を意識）。
- 研究用途の結果は DuckDB に格納してクエリで分析するワークフローを推奨します。

以上。必要であればサンプル .env のテンプレートや運用例（systemd ユニット / Dockerfile / cron ジョブ）を追加で提供できます。どの情報をより詳しく載せたいか教えてください。
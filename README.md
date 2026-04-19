# KabuSys

日本株向け自動売買システムの Python コードベース。ポートフォリオ構築・ポジションサイジング・監視（Kill Switch）・ペーパートレード検証・LLM ベースのニュース評価などの主要機能を含みます。

注意: このリポジトリは実運用を前提とした設計要素（本番/ペーパー用 DB 分離、Kill Switch、実取引 API とのインタフェース等）を含みます。実際に本番環境で稼働させる際は設定やシークレットの管理に十分ご注意ください。

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 使い方（主要スクリプト）
- 環境変数（主な設定項目）
- ファイル・ディレクトリ構成（主要ファイルの説明）

---

プロジェクト概要
- 日本株自動売買に必要なコンポーネント群を持つモジュール群。
- 戦略研究（ファクター計算、特徴量探索）、ポートフォリオ構築、ポジションサイジング、注文実行（ExecutionEngine）、監視（Monitoring）、LLM を使ったニュース評価・レジーム判定などを含む。
- 本番環境（live）とペーパートレード（paper_trading）を明確に分離する設計。監視ログは SQLite、分析用に DuckDB を使用。

機能一覧
- 環境設定ウィザード（config_setup.py）: 対話式に .env を生成
- 設定検証 CLI（validate_config.py）: .env と config/*.yaml の基本チェック
- Execution エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の際は MockBroker を使用し、paper_trading DB に書き込む（本番 DB と分離）
  - execution.pid 管理・停止フラグの監視
- Monitoring エンジン起動スクリプト（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）
  - 一部の監視は本番 sqlite_path（監視 DB）を使用（環境に依らず本番 path を使う設計あり）
- 監視・ログ永続化（monitoring_db.py）: SQLite ベースのスキーマ作成・読み書き
- Kill Switch（kill_switch.py）: ドローダウンやポジション上限超過時に data/kill.flag を書く
- RiskMonitor（risk_monitor.py）: drawdown, position count の監視とリスクログ記録
- Portfolio 関連（portfolio/）: 候補選定、重み計算、セクター制限、ポジションサイズ計算
- Research（research/）: ファクター計算（モメンタム、ボラティリティ、バリュー）、特徴量解析（IC 等）
- AI（ai/）:
  - news_nlp.score_news(): OpenAI を使った銘柄ごとのニュースセンチメント評価（ai_scores テーブルへ）
  - regime_detector.score_regime(): ETF MA とマクロ記事を組み合わせた市場レジーム判定
- ユーティリティ（utils/）:
  - logging_setup: コンソール + 日次ローテートログ設定
  - process_priority: プロセス優先度 / CPU affinity 設定
- ツール（tools/）:
  - paper_verification_report.py: ペーパートレード DB から検証レポート生成（稼働率、約定率、レイテンシ等）

前提・依存関係
- Python 3.10+（型注釈に | 演算子を使用）
- 必須（利用する機能に応じて最低限必要なもの）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
- 任意:
  - PyYAML（config/*.yaml の構文チェックを行う場合）
- DB: SQLite（組み込み）および DuckDB（分析用ファイル）
- ネットワーク: 実取引・API 利用には外部アクセスが必要（kabuステーション 等）

セットアップ手順（ローカル開発用）
1. リポジトリをクローンしワークディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install duckdb psutil openai
   - 任意で PyYAML を入れる: pip install PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数の初期設定（.env）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
   - 主な必須項目:
     - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
     - KABU_API_PASSWORD（kabuステーション API 用）

5. DB の初期化
   - monitoring 用 SQLite と DuckDB は初回起動時に必要なテーブルが自動生成されます（init_monitoring_db 等）。
   - デフォルトのファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

使い方（主要スクリプト）
- 環境設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）
  - 出力で未設定の必須環境変数や DB パスの親ディレクトリ存在などをチェックします

- Execution（エンジン）起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の時は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）
    - 起動時に data/execution.pid を作成し、停止は data/stop_requested.flag / data/kill.flag などのフラグで制御
    - プロセス優先度を high に設定します（utils.process_priority）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は system_status / trade_logs / risk_logs / dashboard などを操作します
  - 監視は KABUSYS_ENV にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用する点に注意

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite のパスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 機能（OpenAI を用いる操作）
  - 環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡す
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を与えて呼び出す

重要なファイル・フラグ
- data/kill.flag: Kill Switch が書き込む停止フラグ（ExecutionEngine の停止トリガ）
- data/stop_requested.flag: run_* スクリプトが外部から停止リクエストを検知するために見るファイル
- data/execution.pid: 実行プロセスの PID 格納に使用
- ログ: デフォルト logs/ にアプリ別ログファイル（例: logs/execution.log, logs/monitoring.log）を出力

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必要)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- LOG_DIR: ログディレクトリ（デフォルト: logs）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用 DB）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用 DB）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の Fill モード）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動的にクリアするか (0/1)（本番では 0 推奨）

ディレクトリ構成（抜粋・説明）
- src/kabusys/
  - __init__.py: パッケージ定義、バージョン
  - config.py: 環境変数読み込み・Settings クラス（アプリ設定）
  - config_setup.py: .env 対話式ウィザード
  - validate_config.py: 設定検証 CLI
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート
  - ai/
    - news_nlp.py: ニュースを LLM によるセンチメント評価（ai_scores 書き込み）
    - regime_detector.py: 市場レジーム判定（MA + マクロ LLM）
  - monitoring/
    - monitoring_db.py: 監視用 SQLite スキーマ・ラッパ
    - system_monitor.py: システム状態・データ鮮度チェック
    - risk_monitor.py: ドローダウン/ポジション上限監視
    - kill_switch.py: kill.flag 書込みユーティリティ
    - monitoring_engine.py: 複数 Monitor を束ねてポーリング
    - (その他 TradeMonitor / AlertManager 等のモジュールが想定)
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 発注株数計算・資金配分
    - risk_adjustment.py: セクター上限・レジーム乗数
  - research/
    - factor_research.py: モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py: 将来リターン、IC、統計サマリ
  - utils/
    - logging_setup.py: ログ設定ユーティリティ
    - process_priority.py: プロセス優先度 / CPU affinity 設定

開発上の注意点 / 運用上の注意点
- .env（シークレット情報）は絶対に Git 等へコミットしないでください。
- KABUSYS_ENV=live（本番）時は LINE 通知設定や Kill Switch の挙動を特に確認してください（validate_config にて警告を出します）。
- AI（OpenAI）を使う機能は API 利用料が発生します。テスト時はモック化（ユニットテストでの差し替え）が想定されています。
- run_monitoring は監視 DB に対して本番 sqlite_path を使用する設計の箇所があるため、ペーパー用と本番用の DB 分離に注意してください。
- 複数インスタンスの実行や自動起動スクリプトを作る場合は PID ファイル / stop/kill フラグの取り扱いを厳密に管理してください。

問い合わせ / 貢献
- README に記載のない点や実行上の問題がある場合は issue を作成してください。
- 仕様改善・バグ修正は PR を受け付けます。特にログ・監視・Kill Switch 周りは本番互換性に関わるため注意深いレビューを行います。

以上。必要なら、README に入れるサンプル .env のテンプレートや systemd / docker-compose でのサービス定義例、よくあるトラブルシューティング（権限、psutil の権限エラー、DuckDB のファイル作成失敗など）を追加します。どの情報を追加したいか教えてください。
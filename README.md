# KabuSys

日本株自動売買システムのコアライブラリ（README）。  
このドキュメントはリポジトリ内の主要スクリプト／モジュールを元に、セットアップと使い方、ディレクトリ構成を日本語でまとめています。

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / 依存パッケージ
- セットアップ手順
- 環境変数（.env）と重要設定
- 実行方法（主要スクリプト）
- 運用上のポイント（Kill Switch / フラグファイル 等）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買・リサーチ・監視機能を備えたパッケージ群です。
- 戦略（ファクター計算、ポートフォリオ構築、ポジション決定）、発注実行（ExecutionEngine）、監視（MonitoringEngine / SystemMonitor / RiskMonitor 等）、AI を用いたニュース評価（OpenAI）などの機能を含みます。
- 設定は .env ファイル（または環境変数）で管理され、開発／ペーパートレード／本番（live）を切り替えられます。

主な機能一覧
- 環境設定ウィザード（kabusys.config_setup）で .env を対話的に作成・更新
- 設定検証 CLI（kabusys.validate_config）で起動前チェック
- ExecutionEngine（発注処理）：本番 or ペーパートレード（mock broker）対応、paper_trading 時は別 SQLite に記録
- Monitoring（System / Trade / Risk Monitor）：定期ポーリングでシステム稼働状況・注文状況・リスクを監視
- Kill Switch：条件（例: ドローダウン超過）で停止フラグ（data/kill.flag）を作成して発注エンジンを停止
- リサーチモジュール：ファクター計算（Momentum / Volatility / Value 等）と特徴量解析（IC 等）
- AI モジュール：ニュース NLP による銘柄センチメント評価（OpenAI 使用）
- ツール：Paper Trading 検証レポート生成スクリプト

前提条件 / 依存パッケージ
- Python 3.10+ を想定
- 必須（主要）パッケージ（例）:
  - duckdb
  - psutil
  - openai
- 任意:
  - PyYAML（config/*.yaml の文法チェックに使用）
- SQLite は標準ライブラリ（sqlite3）で使用
- 依存はプロジェクトの requirements.txt がある場合はそれを利用してください。なければ以下で必要パッケージをインストールします（例）:
  - pip install duckdb psutil openai pyyaml

セットアップ手順
1. リポジトリをチェックアウト
2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   （requirements.txt があれば pip install -r requirements.txt）
4. .env の作成
   - python -m kabusys.config_setup
     - 対話式ウィザードで .env を生成します（.env は絶対に Git にコミットしないでください）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

環境変数（.env）と重要設定
- 必須（validate_config による）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- よく使う設定（主なもの）:
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）
    - paper_trading: 発注は MockBrokerClient を使い、data/paper_trading.db に記録（本番DBと分離）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - OPENAI_API_KEY: OpenAI を使う機能に必要
  - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant / partial / never / reject）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1。本番は0推奨）
- 自動ロード:
  - プロジェクトルートが特定できる場合、.env（→.env.local）を起動時に自動読み込みします。無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

実行方法（主要スクリプト）
- 実行はパッケージモジュールとして行います（推奨）。プロジェクトルートで以下を実行。

1) 監視ループ起動（Monitoring）
- python -m kabusys.run_monitoring
- 説明:
  - Monitoring 用のポーリングループを開始します。
  - デフォルトのポーリング間隔: 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可）
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用（KABUSYS_ENV に依存しない）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成すると検知して終了

2) 発注エンジン起動（Execution）
- python -m kabusys.run_execution
- 説明:
  - ExecutionEngine（発注ループ）を別スレッドで実行します
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
  - 起動前に data/stop_requested.flag が存在すると起動せずに終了
  - 起動中に stop flag を検知するとエンジンを停止します
  - 実行中は data/execution.pid に PID を書く想定（設定に依存）

3) 設定検証
- python -m kabusys.validate_config [--strict]
- .env と config/*.yaml の基本的なチェックを行います（PyYAML があれば YAML のパースも検証）

4) .env 作成ウィザード
- python -m kabusys.config_setup
- 対話式に .env を生成／更新します

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定できます
- 出力: 稼働率、注文成功率、レイテンシ等のレポート（PASS/FAIL 判定）

運用上のポイント（Kill Switch / フラグファイル 等）
- Kill Switch:
  - リスク監視が閾値を超える（例: ドローダウン）と data/kill.flag に理由を書き込み、ExecutionEngine に停止シグナルを送ります。
  - KillSwitch は冪等で既存の kill.flag があれば書き直しません。
- 停止フラグ:
  - run_execution/run_monitoring は data/stop_requested.flag を監視し、存在を検知すると安全終了します（手動停止用）。
- PID / ログ:
  - デフォルトのログは logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリを作成）。
  - run_execution は data/execution.pid（設定で変更可）を利用します。
- 初回起動の注意:
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動で削除しますが、本番では危険なので 0 を推奨します。

設定例 (.env の抜粋例)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

その他の重要環境変数
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。run_monitoring で使用。1 以上の整数。
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — Settings クラス（環境変数 / .env 自動ロード / バリデーション）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度・プロセス監視
    - trade_monitor.py — （注文監視ロジック）※コードベースに定義あり
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 monitor を束ねるエンジン
    - alert_manager.py — アラート送信管理（LINE 等）※存在想定
  - execution/
    - execution_engine.py — ExecutionEngine 本体（発注セッション管理）
    - broker_factory.py — ブローカークライアント生成（本番 / モック）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・リスク管理関連
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数決定・単元丸め・資金配分
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI を使って ai_scores を更新）
    - regime_detector.py — マクロ + MA200 を組合わせレジーム判定（OpenAI optional）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py — 共通ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ （実行時に生成・使用）
    - monitoring.db（デフォルト）等の DB ファイル
    - paper_trading.db（paper_trading 用）
    - stop_requested.flag, kill.flag, execution.pid などのフラグファイル/PID

補足・注意事項
- AI（OpenAI）を使う機能は API キー（OPENAI_API_KEY）が必須です。API 利用は課金・利用制限に注意してください。
- 本番環境で KABUSYS_ENV=live を使う際は validate_config の警告に従い、LINE 通知や Kill Switch の動作を確認してください。
- .env はセキュアに管理し、絶対にバージョン管理にコミットしないでください。
- DuckDB / SQLite のパスやログディレクトリは .env で上書きできます。ログディレクトリ作成失敗時はコンソールのみの出力になります。

お問い合わせ／開発時メモ
- 開発者向けには各モジュール（research, portfolio, execution）のユニットテストを用意すると安心です。
- 外部サービスのモック（kabu API / J-Quants / OpenAI）を用意してローカルテストを行ってください。

以上がこのコードベースの README として必要な主要情報です。追加で「導入手順の自動化（systemd / Docker / docker-compose）」や「運用例（デプロイ手順・監視ダッシュボード）」などが必要であれば、その要件に応じて追記できます。
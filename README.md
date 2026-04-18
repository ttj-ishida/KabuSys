KabuSys
======

日本株向け自動売買システムの軽量実装（ライブラリ＋起動スクリプト群）。  
本リポジトリは、取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ／ファクター計算、AI を用いたニュース評価などの主要コンポーネントを含みます。

要点
- 設計方針の一例：本番 DB とペーパートレード DB を分離、.env による環境設定、Monitoring による安全弁（Kill Switch）など。
- 起動／運用用のスクリプト群を提供（実行エンジン、監視ループ、設定ウィザード、設定検証、検証レポートなど）。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / レジーム判定機能を含む（API キーが必要）。

主な機能
- ExecutionEngine（発注エンジン、実運用 or ペーパー）
  - ブローカークライアントの抽象化（環境により Mock を使用）
  - オーダーマネージャ、リスク管理、リコンシリエーション
  - 起動時のプロセス優先度設定、PIDファイル管理、停止フラグ対応
- Monitoring（監視サブシステム）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス監視
  - TradeMonitor / RiskMonitor: 注文・リスク（ドローダウン・ポジション上限）監視
  - KillSwitch によるフラグファイル書き込み（ExecutionEngine の停止トリガ）
  - SQLite ベースの監視ログ永続化
- ポートフォリオ構築（純粋関数）
  - 候補選定、等分配／スコア加重、セクター制限、リスクベースのポジションサイズ計算
- リサーチ / ファクター計算
  - momentum / volatility / value 等のファクターを DuckDB 上で計算
  - 将来リターンや IC（Information Coefficient）計算などのユーティリティ
- AI モジュール
  - news_nlp: ニュースを集約して OpenAI で銘柄ごとのセンチメントを算出し ai_scores に保存
  - regime_detector: ma200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: .env および config/*.yaml の静的検証 CLI
  - paper_verification_report: ペーパートレード結果の集計・判定レポート生成

セットアップ（開発 / 最小動作確認）
- 推奨 Python バージョン: 3.10+
- 仮想環境作成（例）
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- 依存パッケージ（主に利用しているもの）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML — validate_config が config/*.yaml の中身をチェックする際に使用
- インストール例（pip）
  - pip install duckdb psutil openai PyYAML
  - （requirements.txt があれば pip install -r requirements.txt を使用）
- 初期ファイル / ディレクトリ
  - data/ および logs/ は自動作成されますが、必要に応じて作成してください。
  - .env は config_setup で対話的に生成可能（推奨）。

環境変数（主要）
- 必須（起動前に設定または .env に記述）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主要オプション
  - KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
    - paper_trading: Execution は MockBrokerClient を使用し、専用 DB に書き込む
  - OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）で必須
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: ペーパー時の約定モード（instant/partial/never/reject）
- 自動 .env ロード
  - プロジェクトルートの .env / .env.local を自動読み込み（OS 環境変数を保護）。
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

基本的な使い方（コマンド例）
- .env を対話作成
  - python -m kabusys.config_setup
- 設定の静的検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗にする）: python -m kabusys.validate_config --strict
- 実行エンジン起動（本番／ペーパーは KABUSYS_ENV による）
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag が作成されると停止します
  - 実行時は data/execution.pid が使用されます
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）
  - 監視は常に（KABUSYS_ENV に関係なく）本番 sqlite_path を使用します
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB は --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH

重要な運用挙動（注意点）
- Monitoring の Kill Switch
  - RiskMonitor がドローダウンやポジション上限を検出すると data/kill.flag を書き込み、ExecutionEngine 停止のトリガとなります（Execution はこのフラグを検知して停止します）。
  - 本番では KILL_FLAG_CLEAR_ON_START の自動クリア設定に注意（default=0 推奨）。
- DB の分離
  - KABUSYS_ENV=paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。
  - Monitoring は環境にかかわらず監視用 sqlite_path（通常 data/monitoring.db）を使います。
- OpenAI 関連
  - OpenAI API 呼び出しはリトライ・バックオフ実装あり。API キー未設定時は関連機能は動作しません（明示的に例外を出す箇所あり）。
- ロギング
  - setup_logging を共通で使い、stdout（StreamHandler）と logs/<app_name>.log（日次ローテーション）に出力します。
  - デフォルトログディレクトリ: logs/
- 自動 .env パーサ
  - .env のパースはシェル風の quoting とコメント処理に対応。export KEY=val 形式もサポート。

ディレクトリ構成（主なファイル / モジュール）
- src/kabusys/
  - __init__.py              — パッケージ初期化 / バージョン
  - config.py                — Settings クラス（環境変数・自動 .env ロード）
  - config_setup.py          — 対話式 .env 作成ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト（メイン）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - execution/               — 発注エンジン周り（broker, engine, order_manager...）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル初期化・CRUD）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文関連の監視（存在）
    - risk_monitor.py        — ドローダウン・ポジション制限監視
    - monitoring_engine.py   — 各 Monitor を束ねるランナー
    - kill_switch.py         — フラグ書き込みロジック
    - alert_manager.py       — 通知管理（存在）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・丸め処理・資金割り当て
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン計算・IC・統計
  - ai/
    - news_nlp.py            — ニュースセンチメント取得（OpenAI）
    - regime_detector.py     — マーケットレジーム判定（ma200 + LLM）
  - data/                    — 実行時に用いる data/ 以下の DB 等（例: data/*.db, stop_requested.flag）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

開発・拡張メモ
- DuckDB を使った分析／ファクター計算は SQL を直接書いて高速に実行する設計。prices_daily / raw_financials / raw_news 等のテーブルを前提とします。
- AI 関連処理は外部 API（OpenAI）に依存するため、テスト時は API 呼び出しをモックすることを推奨します（コード内で _call_openai_api を patch する想定）。
- validate_config は PyYAML がある場合に config/*.yaml の中身チェックを行います。軽量環境では PyYAML を optional にできます。

トラブルシューティング（よくある問題）
- validate_config が YAML をチェックしない:
  - PyYAML が未インストールのため警告が出ます。pip install PyYAML で解決。
- OpenAI 機能が例外を出す:
  - OPENAI_API_KEY が未設定。環境変数に設定するか該当関数へ api_key を渡してください。
- ログファイル作成に失敗:
  - LOG_DIR の作成権限がないなど。stdout ログは継続して出力されますが、ファイル出力を有効にするにはディレクトリ権限を確認してください。
- システム監視がプロセス停止を検出してしまう:
  - ExecutionEngine の PID 管理 / stop_requested.flag / kill.flag の有無を確認してください。

ライセンス / 責任
- 本 README はコードベースから抽出した説明をまとめたものであり、実運用にあたってはコードの実装内容を必ず読み、必要な安全対策（事前テスト、監査、キー管理）を行ってください。

以上。必要であれば各コマンドのより詳細な使用例（起動スクリプトのログ出力例、.env のサンプルテンプレート等）を追加します。どの部分を詳しく書きたいか教えてください。
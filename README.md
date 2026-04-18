KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤のモジュール群です。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注を管理（本番 / ペーパートレード対応）
- 監視（Monitoring）: システム状態、注文ログ、リスク監視、Kill Switch（停止フラグ）等のポーリング監視
- ポートフォリオ構築ユーティリティ: 候補選定・重み計算・ポジションサイズ算出・セクター制約等
- リサーチ: ファクター計算（モメンタム／ボラティリティ／バリュー）・特徴量探索
- AI 支援モジュール: ニュース NLP（OpenAI を利用したセンチメント）、レジーム判定
- ツール類: Paper Trading 検証レポート生成、設定ウィザード、設定検証 CLI 等
- 共通ユーティリティ: ロギング設定、プロセス優先度制御、設定読み込み等

主な機能一覧
-------------
- 設定管理
  - .env 自動ロード（プロジェクトルートの .env/.env.local）
  - interactive ウィザードで .env を生成（kabusys.config_setup）
  - validate_config による起動前チェック
- 実行 / 発注
  - 本番（live） / ペーパートレード（paper_trading）を環境変数で切替
  - paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
- 監視
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - MonitoringEngine によるポーリング、Kill Switch による自動停止
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額／スコア重み付け、リスクベースのポジション決定、セクター上限適用
- リサーチ
  - DuckDB 上の prices_daily / raw_financials からファクターを計算（モメンタム、ボラティリティ、バリュー）
  - IC 計算・将来リターン計算などの統計ツール
- AI（OpenAI）
  - ニュース記事をまとめて銘柄別センチメントを算出し ai_scores テーブルへ保存
  - マクロ記事から市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込み
  - OpenAI API キー（OPENAI_API_KEY）が必要
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを出力

セットアップ手順
----------------
前提
- Python 3.10+ 推奨（typing の構文等に依存）
- SQLite は標準ライブラリで利用可
- 必要な外部パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML の構文チェックを行いたい場合、任意）

例: 仮想環境とパッケージインストール
- Unix 系:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai pyyaml

環境変数 / .env
- 対応主要環境変数（.env で設定）
  - JQUANTS_REFRESH_TOKEN （必須）
  - KABU_API_PASSWORD （必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパー用 DB、デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY（AI モジュールを利用する場合）
  - LOG_LEVEL（デフォルト: INFO）
  - その他: LINE チャネル用設定、PAPER_FILL_MODE（paper_trading の振る舞い）など

.env を作る（対話ウィザード）
- python -m kabusys.config_setup
  - 対話形式で .env を生成・更新します
  - 生成後は python -m kabusys.validate_config で検証してください

設定検証
- python -m kabusys.validate_config
  - 必須 env の未設定や config/*.yaml の存在等をチェックします
  - --strict を付けると警告を FAIL 扱いで終了します

データベース初期化
- 監視用 SQLite と DuckDB は起動スクリプト実行時に必要なテーブルを自動で作成します（init_monitoring_db など）
- データディレクトリ（data/）や logs/ は起動スクリプトが自動作成する場合がありますが、必要に応じて手動作成してください

使い方（起動例）
----------------

監視ループ（SystemMonitor）
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可（例: export MONITOR_POLL_INTERVAL=30）
- 起動:
  - python -m kabusys.run_monitoring
  - 停止: プロジェクトルート/data/stop_requested.flag を作成すると監視ループが検知して終了します
  - 監視は Settings に従い monitoring DB（SQLite）に記録します（監視は本番 sqlite_path を使用）

ExecutionEngine（発注エンジン）
- 起動:
  - python -m kabusys.run_execution
- ペーパートレード:
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）が使われます（本番 DB と分離）
- 停止:
  - data/stop_requested.flag を作成するとエンジンに停止シグナルが送られます
  - Kill Switch（データベースのリスク判定に基づき）で data/kill.flag を書き込むこともあります
- PID / フラグ:
  - data/execution.pid が ExecutionEngine の PID に使われます
  - Settings.kill_flag_clear_on_start=1 をセットすると起動時に kill.flag を自動クリアします（本番では 0 推奨）

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from YYYY-MM-DD --to YYYY-MM-DD
- 簡易的に PAPER_TRADING_SQLITE_PATH 環境変数を参照します（指定がない場合は data/paper_trading.db）

AI 関連
- news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします
- API 呼び出しはレート制限や 5xx を考慮したリトライを実装していますが、キーと接続を正しく設定してください

ログ
- デフォルトで logs/ ディレクトリに毎日ローテーションされるログファイルが出力されます（kabusys.utils.logging_setup）
- LOG_LEVEL / LOG_DIR の環境変数で制御できます

停止 / Kill フロー
- run_execution / run_monitoring は data/stop_requested.flag を監視して graceful shutdown を行います
- KillSwitch はリスク閾値超過時に data/kill.flag を書き込み、別プロセス（ExecutionEngine）が検出して停止します
- kill.flag のクリアは KillSwitch.clear() または起動設定で制御できます（KILL_FLAG_CLEAR_ON_START）

ディレクトリ構成
----------------
以下はソースの主要ファイル・モジュール構成（README 作成時点の抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env ロードと Settings クラス
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - utils/
    - __init__.py
    - logging_setup.py        — 共通ロギングセットアップ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル初期化・CRUD）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション監視
    - trade_monitor.py       — （注文監視ロジック）※詳細はソース参照
    - kill_switch.py         — フラグファイルによる停止信号
    - alert_manager.py       — （アラート集約）※詳細はソース参照
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定 / 等重・スコア重み
    - position_sizing.py     — 発注株数算出、集約キャップ処理
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ma200 + macro sentiment）
  - data/                    — 実行時に生成されることの多いディレクトリ（DB ファイル、フラグ等）
  - logs/                    — ログファイル出力先（デフォルト）

注意事項 / 運用上のヒント
------------------------
- 本番（live）運用時は KABUSYS_ENV=live に設定し、.env の値を慎重に管理してください（.env は決して Git にコミットしないこと）。
- kill.flag / stop_requested.flag の扱いに注意してください。特に本番で KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動で消してしまい危険です（本番は 0 推奨）。
- AI 機能は外部 API（OpenAI）に依存します。API キーは安全に保管し、API コスト・レート制限を考慮して運用してください。
- DuckDB / SQLite のファイルパスは Settings で上書き可能です。分析用と実行用は分離して運用することを推奨します（特に paper_trading）。

追加情報
--------
- 各モジュールの詳細やパラメータ（例: RiskConfig、EngineConfig、ポジション算出のパラメータ等）はソース内の docstring / コメントに記載しています。実装やチューニングの際は該当モジュールを参照してください。
- config/*.yaml（system_config.yaml 等）のテンプレートや生成スクリプトがある場合、validate_config はそれらを参照して検証します（PyYAML が無い場合は内容検証をスキップします）。

問題や改善案
-------------
- ログ出力や DB パス等は環境依存なので、コンテナ化（Docker）や systemd サービス化を行うと運用が楽になります。
- 大量のデータを扱う分析処理は DuckDB を利用しています。処理時間・メモリに応じてリソース割当てを調整してください。

以上。必要であれば README に「環境変数一覧（全キー）」や「よくある運用手順（起動 / 停止 / ローテーション）」の詳細版を追加で作成します。どの情報が欲しいか教えてください。
KabuSys — 日本株自動売買システム
=============================

この README はリポジトリ内の主要スクリプト・モジュール（src/kabusys 以下）をもとにした概要と使い方ガイドです。開発者・運用担当者向けの最小限の手順と設定項目をまとめています。

プロジェクト概要
---------------
KabuSys は日本株の自動売買・リサーチ基盤です。主な役割は次のとおりです。

- 市場データ（DuckDB を利用）からファクター計算・特徴量分析を行う（research）。
- ポートフォリオ構築・ポジションサイズ決定ロジックを提供（portfolio）。
- ExecutionEngine によりブローカーへ発注（実運用／ペーパートレード両対応）。
- 監視コンポーネント（MonitoringEngine／SystemMonitor／TradeMonitor／RiskMonitor）により稼働状況・データ鮮度・リスクを監視し、必要時に Kill Switch（data/kill.flag）で停止信号を出す。
- OpenAI を利用したニュース NLP（ai.news_nlp）やレジーム判定（ai.regime_detector）を実装（APIキー必要）。
- ペーパートレード検証レポート生成スクリプト等の補助ツールを提供。

主な機能一覧
--------------
- 実行エンジン起動: run_execution.py（本番 / paper_trading 切替）
- 監視ループ起動: run_monitoring.py（定期ポーリング、停止フラグ対応）
- 環境設定ウィザード: config_setup.py（.env の対話的生成）
- 設定検証 CLI: validate_config.py（.env / config/*.yaml の事前チェック）
- Paper Trading 検証レポート: tools.paper_verification_report
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- リサーチ（モメンタム / ボラティリティ / バリュー 等のファクター計算）
- ニュースセンチメント・市場レジーム判定（OpenAI API 使用）
- 監視DB 操作ユーティリティ（SQLite に監視ログを永続化）

セットアップ手順
----------------
前提:
- Python 3.9 以上を推奨（duckdb 等が利用されるため互換性を確認してください）。
- システムにより追加のネイティブ依存（psutil など）が必要になる場合があります。

1. リポジトリのクローン
   - 任意の場所にクローンして作業する。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 必須（代表例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config ファイル検証を行う場合にあると便利）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - ※ requirements.txt がある場合はそれを使用してください。

4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
     - 主要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV など）を設定できます。
   - 手動で作成する場合は .env.example を参考に .env を作成してください（.env は Git にコミットしないこと）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit code 1）になります。

6. データディレクトリの準備
   - デフォルトでは data/ に SQLite / DuckDB 等のファイルを置きます。必要に応じて環境変数で上書き（下記参照）。

使い方（主要スクリプト）
-----------------------
- 環境変数の主な項目（デフォルト / 説明）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading のモック成行埋め方（instant|partial|never|reject、デフォルト: instant）
  - OPENAI_API_KEY: OpenAI API キー（ai 機能で必要）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR: ログ格納ディレクトリ（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、ペーパートレード用 DB（data/paper_trading.db）へ記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
  - 実行中に停止させるには data/stop_requested.flag を作成するか、kill.flag を書く監視ロジックを利用します（Monitoring 側で kill.flag を書く）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使って行われます（環境にかかわらず）。
  - data/stop_requested.flag を置くとループは終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）
  - ペーパートレード DB の稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL を判定します。

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- AI 機能
  - ai.news_nlp.score_news / ai.regime_detector.score_regime は OPENAI_API_KEY が必要です。
  - API 呼び出しはリトライやパースの安全策を含む実装になっていますが、API 使用料に注意してください。

停止・Kill Switch
------------------
- 監視コンポーネントは特定の条件（ドローダウンやポジション上限超過など）で kill.flag（既定: data/kill.flag）を書き込み ExecutionEngine に停止を促します。
- ExecutionEngine / Monitoring の停止制御は次のファイルで行われます:
  - data/stop_requested.flag: ループを安全に停止するためのフラグ（run_* スクリプトはこのファイル存在で終了します）。
  - data/kill.flag: Kill Switch が発動した旨を記録するファイル（Execution 側は起動時にこのフラグをクリアするオプションがある）。

ディレクトリ構成（主要部分）
----------------------------
以下は src/kabusys 配下の主要モジュールと用途の一覧です（抜粋）。

- kabusys/
  - __init__.py            : パッケージ定義、バージョン
  - config.py              : 環境変数読み込み・Settings クラス（主要設定をラップ）
  - config_setup.py        : .env 対話式ウィザード
  - validate_config.py     : 設定検証 CLI
  - run_execution.py       : ExecutionEngine 起動スクリプト
  - run_monitoring.py      : SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py     : ロギング設定ユーティリティ（コンソール + 日次ローテーション）
    - process_priority.py  : プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py     : 監視用 SQLite のスキーマ初期化 / 永続化 API
    - monitoring_engine.py : 各 Monitor を束ねるエンジン
    - system_monitor.py    : システム状態・データ鮮度監視
    - risk_monitor.py      : ドローダウン / ポジション上限監視
    - kill_switch.py       : kill.flag 管理
    - (trade_monitor.py, alert_manager.py 等が存在する想定)
  - execution/             : ExecutionEngine / ブローカーラッパー / 注文管理（詳細は該当ファイル）
  - portfolio/
    - portfolio_builder.py : 候補選定・重み計算
    - position_sizing.py   : 発注株数計算・資金配分・単元丸め
    - risk_adjustment.py   : セクターキャップ・レジーム乗数
  - research/
    - factor_research.py   : momentum / volatility / value ファクター計算（DuckDB 使用）
    - feature_exploration.py: forward returns / IC / 統計サマリー
  - ai/
    - news_nlp.py          : ニュース NLP（OpenAI 呼び出し・JSON 検証・結果書込み）
    - regime_detector.py   : マーケットレジーム判定（MA200 + マクロ NLP 合成）
  - tools/
    - paper_verification_report.py : ペーパートレード検証レポート生成

運用上の注意
-------------
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知や各種しきい値を事前に確認してください。validate_config.py は live 特有の警告も出します。
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください。
- OpenAI を使う機能は API コストが発生します。API キーの管理・利用制限に注意してください。
- run_execution はペーパートレードと本番で DB を分けています（PAPER_TRADING_SQLITE_PATH を設定すると paper_trading モードの DB を使用）。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR を変更可能です。
- process_priority.set_process_priority() により起動時に優先度を上げようとしますが、権限不足などで失敗することがあります（警告に留まる）。

トラブルシューティングのヒント
-----------------------------
- データベースが見つからない・アクセスできない場合、validate_config は警告を出します。パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を確認してください。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL（秒）で調整できます。0 や負の値は無効でデフォルトにフォールバックします。
- OpenAI 呼び出しで 5xx/429/タイムアウトが発生した場合は内部でリトライを行いますが、最終的に取得できない場合は該当処理はスキップされフェイルセーフで継続します。

最後に
------
この README はコードベースの主要点をまとめたものです。詳細な実装（ExecutionEngine の発注ロジック、trade_monitor, alert_manager など）は該当モジュールのソースを参照してください。導入や運用に関する追加ドキュメントが必要であれば、その項目（例: デプロイ手順、システム構成図、監視アラート設計）を指定してください。
KabuSys — 日本株自動売買システム（README）
=================================

概要
----
KabuSys は日本株向けの自動売買／研究／監視を支援する Python パッケージです。  
主な機能はトレーディング実行エンジン、監視エンジン、ポートフォリオ構築・サイズ決定、ファクター計算、ニュース NLP（OpenAI）を利用したスコアリングなどを含みます。  
設計方針として「本番 DB とテスト（ペーパー）を分離」「ルックアヘッドバイアス防止」「外部 API 呼び出しは明示的に行う」などを採用しています。

主な特徴（機能一覧）
------------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い paper DB に記録
  - PID ファイル / stop フラグでプロセス制御
  - RiskManager / OrderManager / Reconciler 組み込み
- Monitoring（run_monitoring.py）
  - System / Trade / Risk モニタをポーリングしてログ保存・アラート発行
  - Kill Switch（stop フラグ）による Execution 停止トリガ
  - MONITOR_POLL_INTERVAL 環境変数で間隔指定（デフォルト 60 秒）
- 監視 DB 層（monitoring_db.py）
  - SQLite に system_status / trade_logs / positions / risk_logs / dashboard を冪等的に作成・更新
- ポートフォリオ構築（portfolio）
  - 候補選定、等重・スコア重み、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算
- 研究用モジュール（research）
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン、IC（Information Coefficient）、統計サマリ等
- AI（kabusys.ai）
  - ニュース NLP による銘柄別センチメントスコア生成（OpenAI）
  - 市場レジーム判定（MA200 とマクロセンチメントの合成）
- ツール
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ
  - 統一ロギング設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）
  - 設定管理（config.py）：.env の自動読み込み、Settings クラスで環境変数を提供

セットアップ手順
---------------
1. Python バージョン
   - Python 3.10 以降（型ヒントで | を使用、3.10+ 推奨）。3.11 を推奨。

2. 依存パッケージ（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config ファイル検証を行いたい場合）
   - 例: pip install duckdb psutil openai pyyaml

   ※ requirements.txt は本リポジトリに含まれていないため、プロジェクト用途に応じて固定してください。

3. プロジェクトルートへ移動
   - パッケージは src/ 配下に配置されています。プロジェクトルートには .env/.env.local, data/, logs/ などを置きます。

4. 環境変数設定（.env）
   - 対話的に生成するには:
     - python -m kabusys.config_setup
     - ウィザードが .env を生成します（.env は絶対に Git にコミットしないこと）
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数（とデフォルト）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - OPENAI_API_KEY — OpenAI 呼び出し用
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
   - config.validate_config により設定検証:
     - python -m kabusys.validate_config [--strict]

5. ディレクトリ作成（data/logs）
   - デフォルトで data/ と logs/ を使用します。config_setup で指定したパスの親ディレクトリが存在しない場合は警告されますが、実行時に自動作成されることがあります。

使い方（主要スクリプト）
------------------------

- 設定ウィザード（.env の生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit 1

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 動作モード:
    - KABUSYS_ENV=paper_trading のときは paper DB（PAPER_TRADING_SQLITE_PATH）と MockBroker を使用
    - 本番（live）では本番 sqlite_path を使用
  - 停止は data/stop_requested.flag を作成することで安全停止できます（stop フラグ）

- 監視エンジン起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 確認指標: 稼働率、注文成功率、送信率、P95 レイテンシ等

- AI（ニューススコア / レジーム判定）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡して ai_scores テーブルへ書き込み
    - api_key を渡さない場合は環境変数 OPENAI_API_KEY を使用
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

運用上の注意
-------------
- Kill Switch / stop フラグ
  - data/kill.flag は ExecutionEngine を停止するためのフラグ（KillSwitch により作成）
  - data/stop_requested.flag は run_* スクリプトの外部停止制御に使用（プロセスが存在する場合は慎重に）
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨

- ログ
  - logs/<app_name>.log に日次ローテートで出力（utils.logging_setup）
  - LOG_DIR 環境変数で出力先を変更可能

- DB マイグレーション
  - monitoring_db.init_monitoring_db() はテーブル作成と簡易マイグレーション（列追加）を冪等に行います

- OpenAI 利用
  - API の失敗（レート制限・5xx 等）はリトライを実装していますが、API キーとコストには注意してください
  - 入力トークン量対策やバッチ処理（1 回に最大 20 銘柄）を行っています

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys をプロジェクトパッケージとしたときの主要ファイル一覧）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証ツール
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, ...）
    - system_monitor.py      — システム / データ鮮度監視
    - trade_monitor.py       — （trade 関連の監視、ファイルに含まれます）
    - risk_monitor.py        — ドローダウン、ポジション上限監視
    - kill_switch.py         — Kill Switch 実装
    - monitoring_engine.py   — 各 monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信管理、ファイルに含まれます）
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (ランタイムで作成されることが多い)
    - monitoring.db / paper_trading.db / kill.flag / execution.pid / stop_requested.flag
  - logs/ (ログ出力先)

補足（よくある質問）
-------------------
- Q: ペーパートレードのログはどこに入る？
  - A: KABUSYS_ENV=paper_trading 時は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。

- Q: 監視はどの DB に書き込まれる？
  - A: monitoring は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。KABUSYS_ENV に依存しません。

- Q: .env を自動で読み込ませたくないときは？
  - A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト等で利用）。

- Q: DuckDB がないと何が使えない？
  - A: research / ai の一部（raw_news, prices_daily 等の分析クエリ）は DuckDB 接続を前提にしています。DuckDB がないとそれらの機能が使えません。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（本 README に未記載）。

最後に
------
この README はコードベースの主要な使い方・構成を簡潔にまとめたものです。運用前に python -m kabusys.validate_config で設定を確認し、開発環境では KABUSYS_ENV=development を使うなどの安全策を取ってください。必要であれば各モジュールの docstring を参照して詳細な挙動を確認できます。
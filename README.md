README
=====

概要
----
KabuSys は日本株の自動売買・研究パイプラインを想定した Python パッケージです。本リポジトリには以下のような主要コンポーネントが含まれます。

- ExecutionEngine（発注実行／ペーパートレード対応）
- Monitoring（システム状態・注文・リスク監視、Kill Switch）
- 研究モジュール（ファクター計算・特徴量解析）
- AI モジュール（ニュース NLP / レジーム判定：OpenAI を利用）
- ポートフォリオ構築ユーティリティ（候補選定・配分・サイズ決定）
- CLI ツール（.env ウィザード・設定検証・レポート生成）

主要設計方針として、発注ロジックや研究ロジックは DB（DuckDB / SQLite）を用いて完全に分離され、ペーパートレード時には本番 DB と排他に動作するよう配慮されています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）を使用
  - PID ファイル管理（data/execution.pid）・停止フラグ検出
- Monitoring（run_monitoring.py + MonitoringEngine）
  - CPU / メモリ / ディスク / プロセス存在チェック
  - データ鮮度チェック（DuckDB の prices_daily 等参照）
  - Trade / Risk の監視（滞留注文・約定異常・ドローダウン等）
  - Kill Switch（条件で data/kill.flag を書き込み Execution を停止）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可
- AI モジュール
  - news_nlp.score_news(): raw_news を OpenAI（gpt-4o-mini 等）へ投げて銘柄毎センチメントを ai_scores へ保存
  - regime_detector.score_regime(): ETF の MA200 とマクロニュースで市場レジーム判定
  - 再試行・パースバリデーションなどフェイルセーフ機構あり
- 研究モジュール
  - factor_research: momentum / volatility / value 等の計算（DuckDB 接続を受ける）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）など
- ポートフォリオユーティリティ
  - 候補選定、等配分 / スコア加重、リスクベースのポジションサイズ計算、セクターキャップ適用
- CLI ツール
  - kabusys.config_setup: 対話式 .env ウィザード
  - kabusys.validate_config: .env / config/*.yaml の事前チェック
  - kabusys.tools.paper_verification_report: ペーパートレード検証レポート生成

セットアップ
----------
1. Python 環境（推奨: 3.10+）を用意します。
2. 依存パッケージをインストールします（例: pip）:

   pip install duckdb psutil openai

   補足:
   - YAML ファイル検証を行う場合は PyYAML が必要です（pip install pyyaml）。
   - テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます。

3. .env の作成／編集:
   - 対話式ウィザードを使う（推奨）:

     python -m kabusys.config_setup

   - 重要な環境変数（最低限必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   - 主な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視DB。monitoring は常に本番 sqlite_path を使用）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
     - LOG_LEVEL, LOG_DIR
     - KILL_FLAG_CLEAR_ON_START: 0/1（起動時に kill.flag を自動クリアするか。production では 0 推奨）
     - MONITOR_POLL_INTERVAL: 監視ポーリング秒（run_monitoring のオーバーライド）

4. ディレクトリ作成:
   - ログ・DB・data ディレクトリは自動作成されますが、権限やパスを事前に確認してください。
   - ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。

使い方（例）
------------
- 設定検証:
  python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit(1)）として扱います。

- ExecutionEngine を起動（通常）は以下のいずれかで:
  - 環境変数でペーパートレードに切替:
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
  - または本番:
    export KABUSYS_ENV=live
    python -m kabusys.run_execution

  実行の挙動:
  - 起動時にプロセス優先度を high に設定し、SQLite / DuckDB に接続します。
  - ペーパートレード時は settings.paper_sqlite_path（default: data/paper_trading.db）を使用。
  - 起動中は data/execution.pid が作成され、停止制御には data/stop_requested.flag と data/kill.flag を使用します。

- Monitoring を起動:
  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（デフォルト 60 秒）。

  python -m kabusys.run_monitoring

  挙動:
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行して監視ログ（SQLite）へ記録。
  - KillSwitch により異常時に data/kill.flag を作成して Execution を停止させられます。
  - stop_requested.flag（data/stop_requested.flag）を置くと監視ループ自体を終了します。

- Paper Trading 検証レポート（CSV ではなく端末出力）:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能。デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
  - レポートは稼働率、注文成功率、送信率、レイテンシ等を評価して PASS/FAIL を出力します。

- AI 機能呼び出し（プログラム的な使用例）:
  from kabusys.ai import score_news
  score_news(duckdb_conn, target_date, api_key="...")

  - OpenAI API キーは引数または OPENAI_API_KEY 環境変数から取得されます。
  - API 呼び出しはリトライ・パース検証を備えています。

運用上の注意
------------
- 監視（monitoring）は設定にかかわらず settings.sqlite_path（本番の monitoring DB）を使用します。監視は本番 DB へ書き込みを行うため注意してください。
- ペーパートレードは専用 DB に限定され、本番データとは明確に分離されます（settings.is_paper が切替）。
- Kill Switch（data/kill.flag）は本番での強制停止用の重要スイッチです。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアされますが、本番では 0 を強く推奨します。
- ロギングは共通ユーティリティを利用しているため、logs ディレクトリとログレベルを適切に設定してください。

ディレクトリ構成（抜粋）
--------------------
- src/kabusys/
  - __init__.py
  - config.py .................. 環境変数・設定の抽象化（Settings クラス）
  - config_setup.py ............ .env 対話式ウィザード
  - validate_config.py ........ 設定検証 CLI
  - run_execution.py .......... ExecutionEngine 起動スクリプト
  - run_monitoring.py ......... Monitoring 起動スクリプト
  - utils/
    - logging_setup.py ........ ログ設定ユーティリティ
    - process_priority.py ..... プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py ........ SQLite の監視用永続化層
    - system_monitor.py ....... システム状態・データ鮮度監視
    - trade_monitor.py ........（注文監視: 滞留注文等）※コードベースに存在
    - risk_monitor.py ......... ドローダウン・ポジション上限監視
    - kill_switch.py .......... Kill Switch の実装（kill.flag 書き込み等）
    - alert_manager.py ........（アラート送信管理）※コードベースに存在
    - monitoring_engine.py .... 複数 Monitor を束ねるエンジン
  - execution/
    - execution_engine.py ..... ExecutionEngine 実装（発注ループ等）※コードベースに存在
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - ai/
    - news_nlp.py ............. ニュース NLP（OpenAI）スコアリング
    - regime_detector.py ...... 市場レジーム判定（MA200 + マクロ NLP）
  - research/
    - factor_research.py ...... ファクター計算（momentum/volatility/value）
    - feature_exploration.py .. 将来リターン / IC / 統計サマリー
  - portfolio/
    - portfolio_builder.py .... 候補選定・等/スコア重み
    - position_sizing.py ...... 単元丸め・投下資金スケーリング・リスク制限
    - risk_adjustment.py ...... セクターキャップ・レジーム乗数
  - tools/
    - paper_verification_report.py  ペーパートレード検証レポート生成

よくある操作例
---------------
- .env を生成して検証する:
  python -m kabusys.config_setup
  python -m kabusys.validate_config

- ペーパートレードで Execution を実行:
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution

- 監視を起動（ポーリング間隔を 30 秒に）:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

追加情報 / 拡張
----------------
- config/*.yaml（system_config.yaml 等）はサンプル生成スクリプトやドキュメントを参照して作成できます（validate_config で存在チェック・パース検証を行います）。
- AI 周り（news_nlp / regime_detector）は OpenAI のレスポンス仕様に依存します。API SDK の変更やレスポンスフォーマットの差異に注意してください（ライブラリバージョン固定を推奨します）。
- DB スキーマは monitoring_db.init_monitoring_db で冪等的に作成・マイグレーションされます。

サポート
-------
この README はコードベースの主要な機能と使い方を簡潔にまとめたものです。詳細な設計仕様やアルゴリズムの背景（PortfolioConstruction.md など）はリポジトリ内のドキュメントを参照してください。質問や不明点があればリポジトリの開発者にお問い合わせください。
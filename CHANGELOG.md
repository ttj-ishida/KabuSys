CHANGELOG
=========

すべての注目すべき変更を時系列で記録します。  
このファイルは「Keep a Changelog」準拠の形式で記載しています。

[Unreleased]
------------

（なし）

0.1.0 - 2026-04-25
-----------------

初回リリース。以下の主要機能・モジュールを追加しました。

Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 停止用フラグファイル（data/stop_requested.flag）検知でループを終了。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用し、duckdb にも接続して監視 DB 初期化を行う。
    - プロセス優先度を起動直後に "high" に設定。
    - 例外発生時にログ出力して次回ポーリングまで待機する堅牢化処理を追加。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient（BrokerClientFactory で生成）を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）に記録して本番 DB と完全に分離。
    - PID ファイル管理、停止フラグによる安全シャットダウン処理を実装。
    - スレッドで engine.run_session を実行し、停止フラグ検知で engine.stop() を呼び出して安全に終了。
    - プロセス優先度を起動直後に "high" に設定。

- 設定・環境管理
  - config.py
    - Settings クラスを導入し、各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ関連、閾値など）をプロパティとして提供。
    - KABUSYS_ENV/LOG_LEVEL のバリデーションを実装（valid 値セットを定義）。
    - .env 自動読み込み機能を実装（プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を適切な優先順位で読み込み）。既存 OS 環境変数は保護（protected）される。
    - .env のパースでクォートや export プレフィックス、インラインコメント等を正しく処理するパーサを実装。

  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を追加。
    - 入力支援、既存 .env の読み取り、シークレット表示マスク、確認プロンプト、ファイル書き込みを実装。
    - デフォルト値や選択肢、説明文を含む設定項目定義を提供。

  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性を検査する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証、本番時のガードチェック（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）などを実装。
    - --strict オプションにより警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ設定するユーティリティを追加。
    - レベルとログディレクトリの解決順序を明確化（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックを追加。

  - utils/process_priority.py
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対するプロセス優先度設定（nice/priority class）を抽象化して提供。
    - CPU affinity 設定関数を追加（最初の N コアに固定）。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、signal_rank によるタイブレーク）。
    - 重み算出: 等金額（calc_equal_weights）・スコア加重（calc_score_weights）。全スコアが 0 の場合は等金額にフォールバックして警告を出す。

  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数算出ロジックを実装。
    - 1銘柄上限（max_position_pct）、aggregate 上限（available_cash）、lot_size（単元株）で丸める処理、手数料/スリッページを考慮する cost_buffer、残余キャッシュを利用した端数分配（fractional remainder に基づき lot 単位で追加配分）を実装。
    - 価格欠損時のスキップやログ出力など堅牢化。

  - portfolio/risk_adjustment.py
    - セクター集中リスク制限（apply_sector_cap）: 既存保有のセクター別エクスポージャーを算出し、max_sector_pct を超えるセクターの新規候補を除外するロジック。unknown セクターは制限対象外とする仕様。
    - レジーム乗数（calc_regime_multiplier）: "bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは警告を出して 1.0 にフォールバック。

- Execution（注文）周りの基盤
  - execution パッケージ（複数モジュール）へのエンジン組立ておよびリスク管理設定の追加（EngineConfig, RiskConfig を利用）。
  - Reconciler、OrderManager、OrderRepository の組み合わせによる注文ワークフロー基盤を組み込む。RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 構成、max_drawdown 等）を含む。
  - ExecutionEngine は PID ファイルを受け取り、停止フラグに対応する。

- 監視DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を用いて monitoring 用テーブルが存在することを起動時に保証（冪等性）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、レイテンシ（avg/max/P95）を集計して判定（PASS/FAIL）を出力。
    - デフォルト閾値を定義: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - --from / --to / --db オプションで期間・DB を指定可能。DB 存在チェックとエラーハンドリングを実装。

- 研究用モジュール（下地）
  - research/factor_research.py
    - モメンタム・ボラティリティ・バリュー等のファクター計算用モジュールを追加。DuckDB の prices_daily / raw_financials を参照してファクターを返す設計。
    - 定数・方針や calc_momentum の骨組みを実装（モジュールは今後の拡張を想定）。

Changed
- プロジェクトルート検出ロジックは __file__ を起点に親ディレクトリを探索する方式を採用し、CWD に依存しない自動 .env ロードを実現。

Fixed
- （初回リリースのため特定の「修正」扱いの項目はなし。実装時に検討された堅牢化やフォールバック挙動は上記 Added に含む。）

Known Issues / TODO
- research/factor_research.calc_momentum の実装ファイルが途中で切れている（未完）。今後、prices_daily を参照した具体的な SQL / 計算ロジックを実装予定。
- portfolio.position_sizing 内の価格が 0.0（欠損）だった場合の扱いについて注記（コメントでフォールバック価格導入の TODO を残している）。
- process_priority.set_cpu_affinity / nice 設定は権限不足や OS 非対応時にスキップするようにしているが、動作確認は各プラットフォームで必要。
- 一部の外部依存（psutil, duckdb, PyYAML）は環境により未インストールの場合があるため、該当機能はフォールバックや警告で対応している。実運用前に依存関係を確認してください。

Notes
- 本リリースは基盤機能（環境設定、起動スクリプト、ロギング、プロセス管理、ポートフォリオ構築、発注基盤、監視、検証ツール）を一通り揃えた初版です。今後のリリースで戦略ロジックの完成、テスト充実、ドキュメント整備、CI/デプロイ対応を進めます。
# CHANGELOG

すべての重要な変更点を記録します。本書式は「Keep a Changelog」準拠です。

全般:
- セマンティックバージョニングを採用します（例: 0.1.0）。
- 日付はリリース日を示します。

## [Unreleased]

## [0.1.0] - 2026-04-20

### Added
- 初期リリース。日本株自動売買システム「KabuSys」のコア機能を収録。
- 実行スクリプト / デーモン類:
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を介してブローカークライアントを切り替え。
    - エンジンはバックグラウンドスレッドで実行し、data/stop_requested.flag による停止検知および PID ファイル管理（data/execution.pid）を実装。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは共通の監視 DB に記録）。
    - 停止フラグ（data/stop_requested.flag）による安全終了処理を実装。
- 設定管理:
  - config.py
    - .env の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順を実装（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - export プレフィックス、クォート/エスケープ、インラインコメントなどを考慮した .env パーサー実装。
    - Settings クラスで環境変数をプロパティとして提供（J-Quants、kabu API、DB パス、監視閾値、環境判定メソッド等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
- 設定操作用 CLI:
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - J-Quants / kabu API / DB パス / LOG_LEVEL / Kill Switch 等の項目を対話形式で設定。
    - .env の既存値読み込み・マスク表示・確認保存機能を備える。
  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスおよび config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）。
    - --strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築モジュール (kabusys.portfolio):
  - portfolio_builder.py
    - シグナル選定 (select_candidates)、等重配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバック（警告ログ）。
  - risk_adjustment.py
    - セクター集中制限適用 (apply_sector_cap)。既存保有のセクター別時価を計算し、上限を超えるセクターの候補除外を行う。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバックして警告）。
  - position_sizing.py
    - 発注株数計算 calc_position_sizes を実装。
    - allocation_method として "risk_based"、"equal"、"score" に対応。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（総投資額が available_cash 超過時のスケールダウン）、
      cost_buffer を加味した保守的なコスト見積りと残差配分ロジックを実装。
- ユーティリティ:
  - utils/logging_setup.py
    - 統一的なロギング初期化関数 setup_logging を提供。
    - stdout への StreamHandler、日次ローテーション（TimedRotatingFileHandler）によるログファイル出力（logs/<app_name>.log）を一括設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定（Windows/Linux/Mac の差分吸収）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限不足などの例外を安全にハンドリング）。
- 監視・レポート関連:
  - monitoring.monitoring_db の初期化呼び出しを各起動スクリプトで自動実行（テーブル存在を保証）。
  - tools/paper_verification_report.py
    - Paper Trading 向けの検証レポート生成スクリプトを提供。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL を判定する基準値を定義（稼働率 99% 等）。
    - P95 の計算、期間フィルタ、SQLite DB パスの CLI / 環境変数指定対応を実装。

### Changed
- N/A（初期リリースのため既存機能の変更は無し）

### Fixed
- N/A（初期リリース）

### Deprecated
- N/A

### Removed
- N/A

### Security
- N/A

### Notes / Known issues / TODO
- research/factor_research.py の実装が途中で終端している箇所（関数内で途中記述が途切れている）があります。ファクター計算モジュールは設計方針・定義は存在しますが、一部実装を継続する必要があります。
- position_sizing.apply の price 欠損に対するフォールバック（前日終値や取得原価など）について TODO コメントあり。現状 price が 0.0 の場合は過少評価のリスクがあるため注意が必要です。
- 権限不足などでプロセス優先度 / CPU affinity / ログファイル作成が失敗した場合は、ログに警告を出して処理をスキップする実装になっています（安全優先）。
- config の .env パーサーは多くのケースをカバーしますが、特殊なエスケープや複雑なシェル式はサポートされません。必要に応じて拡張してください。

---

開発・リリースに関する補足や差分の詳細が必要であれば、どのモジュールについて詳しく記載するかを教えてください。
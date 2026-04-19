# Changelog

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
リリース管理はセマンティックバージョニングに従います。

注: 以下の変更点はコードベースの内容から推測してまとめたものです。実際のコミット履歴がある場合はそちらを優先してください。

## [Unreleased]

- ドキュメント／補足の追加や小さな調整（将来的なリリース予定）。
- テストや CI に関する追記・改善を想定。

---

## [0.1.0] - 2026-04-19

初期公開リリース。以下の主要コンポーネントと CLI/ユーティリティを実装。

### Added
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合、MockBroker を使用して paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定するフックを追加。
    - 停止フラグ (data/stop_requested.flag) を監視し、検知時にエンジンの停止を行うロジックを実装。
    - PID ファイル管理（data/execution.pid）をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - Monitoring は環境に関わらず本番用 sqlite_path を使用する仕様（意図的分離）。
    - 停止フラグを用いた優雅な終了処理、KeyboardInterrupt のハンドリング、例外発生時のログ出力を実装。

- 設定・環境管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート判定：.git / pyproject.toml を探索）。
    - .env / .env.local を OS 環境変数と適切にマージするロジック（override / protected 機能）。
    - 各種設定取得用プロパティ（J-Quants トークン、kabu API、DB パス、Paper トレード設定、監視閾値、環境種別判断など）を実装。
    - 設定値の検証（有効な KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の検査）を組み込み。
    - settings = Settings() のインスタンスをモジュールレベルで公開。

  - config_setup.py
    - 対話式ウィザードで .env を作成 / 更新する CLI を実装。
    - J-Quants トークンや kabu API パスワード等の機密項目はシークレット扱いでマスクしてプロンプト表示。
    - 既存 .env の読み込み、項目ごとのデフォルト・選択肢・説明を提示、保存確認を実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証、KABUSYS_ENV=live のガードチェック等を実装。
    - `--strict` オプションで警告を FAIL 扱いにする機能を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順選択（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算（全スコアが 0 の場合は等金額にフォールバックし警告ログ）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存保有比率が閾値を超えるセクターの新規候補除外）。
      - 未知セクター ("unknown") は除外対象としない動作。
      - sell_codes を受け取り当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数を提供（bull/neutral/bear マップ、未知レジームは警告のうえ 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数を計算する多機能ロジックを実装。
      - allocation_method: "risk_based" / "equal" / "score" に対応。
      - リスクベースの単株最大数、単元株（lot_size）丸め、max_position_pct / max_utilization による上限管理。
      - aggregate cap によるスケールダウンと、余り分を fractional remainder に基づきロット単位で再配分するアルゴリズムを実装。
      - cost_buffer を考慮した保守的なコスト見積り。
      - 価格欠損時のスキップ挙動とログ出力。

- ユーティリティ
  - utils.logging_setup
    - 共通ロギング初期化関数 setup_logging を実装。
    - stdout への StreamHandler と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。
    - 既存ハンドラのクリーンアップと例外時のフォールバックを実装（ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ出力）。
    - ログレベル / ログディレクトリは引数 > 環境変数 > デフォルト の優先順位で解決。
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX (Linux, Darwin, FreeBSD) を吸収した優先度設定のユーティリティを実装（psutil ベース）。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能を実装。アクセス拒否等は警告してスキップ。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプト起動時に呼び出して監視テーブル存在を保証（冪等）。

- Paper Trading 検証ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から指標を集計し、検証レポートを生成する CLI を実装。
    - 集計指標:
      - システム稼働率（uptime_pct）、ポーリング数、エラー数
      - 注文成功率（Filled / Created）、送信率（Sent / Created）
      - リスク却下数（risk_logs）
      - レイテンシ（平均 / 最大 / P95） — P95 はリストをソートして算出
    - Pass/Fail 判定閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from / --to）と DB パス指定オプションをサポート。
    - DB スキーマ不在や OperationalError 発生時に N/A を返して堅牢に動作。

- リサーチ（部分実装）
  - research.factor_research
    - モメンタム等のファクター計算方針と定数を定義。DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計。
    - モメンタム計算 calc_momentum のインターフェースを用意（実装途中で切れているファイル有り）。

### Changed
- なし（初期リリースのため、変更はすべて "Added" として記載）。

### Fixed
- なし（初期リリース時点での既知不具合修正は未記載）。

### Security
- 機密情報は .env に格納する設計。`.env` は絶対に Git にコミットしないよう README/ヘッダに注意書きを追加（config_setup が生成する .env テンプレートに注意書きあり）。

---

過去のリリース（もしあれば）をここに追記してください。将来的なリリースでは以下の点に注目すると良いでしょう:
- research.factor_research の未完部分の実装完了
- 詳細なテストケースと CI の追加
- ログの構造化（JSON）やメトリクス出力の追加
- ExecutionEngine / SystemMonitor の監視メトリクス拡充とアラート連携（LINE 等）
- 個別銘柄ごとの lot_size マスタ化などのリファクタリング

--- 

参考: 本 CHANGELOG はコード内容から推測して作成しています。実際の変更履歴（コミットログ等）を反映する場合は、該当の差分情報を提供してください。
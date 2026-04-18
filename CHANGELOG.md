# Changelog

すべての重要な変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています（[Keep a Changelog](https://keepachangelog.com/ja/1.0.0/)）。

## [0.1.0] - 2026-04-18

### Added
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB と MockBrokerClient を使用可能（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御用のフラグファイル（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）に対応。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立ててデーモンとして実行するループを実装。
    - RiskManager に対するデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を組み込み。
- 監視用エントリポイント
  - run_monitoring.py: SystemMonitor を定期的にポーリングする監視スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書き（デフォルト 60 秒、無効値の検出・フォールバック実装）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して DB を初期化（init_monitoring_db）。
    - 停止フラグ（data/stop_requested.flag）の検出で安全にループを終了。
- 設定管理
  - config.py: 環境変数・設定管理モジュールを追加。
    - __init__ 時にプロジェクトルート（.git または pyproject.toml）を自動検出して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env パース機構（export 形式、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い）を実装。
    - Settings クラスに多数のプロパティを定義（J-Quants, kabuAPI, LINE, DB パス, 監視しきい値, 環境判定等）。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path 等の paper_trading 分離設定。
- 設定支援ツール
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 標準的な項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、Kill Switch 設定など）を対話的に設定して .env を生成。
    - 既存 .env の読み込み・再利用、シークレット値のマスク表示、保存確認機能を提供。
- 設定検証ツール
  - validate_config.py: 起動前に .env や config/*.yaml の不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス親ディレクトリの存在確認、YAML ファイルの存在と（PyYAML があれば）パース検証、本番環境向けの追加ガードを実装。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: ルートロガーの統一的設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートに設定。
    - LOG_DIR / LOG_LEVEL / 引数による上書き対応、ログディレクトリ作成失敗時のフォールバック（ファイル出力をスキップ）に対応。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。アクセス権限がない場合は警告ログでスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）と重み算出（calc_equal_weights, calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。
    - "unknown" セクターはセクター上限の適用対象外。
    - レジーム mapping（bull, neutral, bear）を提供。未定義レジームでのフォールバックと警告。
  - portfolio/position_sizing.py: 発注株数計算とリスク制限アルゴリズム（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer による保守的見積り、残余キャッシュの配分ロジックをサポート。
- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計して PASS/FAIL を判定。
    - コマンドラインで期間指定（--from / --to）および DB パス指定（--db）可能。デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
    - P95 計算、閾値（稼働率 >= 99%、fill_rate >= 90% 等）を組み込み。
- リサーチ（ファクター計算）スケルトン
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（モメンタム・ボラティリティ等を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計方針。calc_momentum 等の実装を開始（関数の宣言と定数類を設置）。

### Changed
- パッケージ初期化
  - __init__.py にバージョン __version__ = "0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ として公開。

### Fixed
- 環境読み込みの堅牢化
  - .env パーサーで export 形式、クォート内のバックスラッシュエスケープ、インラインコメント判定などに対応し、意図しないパースエラーを軽減。
- DB 初期化の冪等性担保
  - run_execution.py / run_monitoring.py 起動時に init_monitoring_db を呼び出して監視テーブルの存在を保証（複数起動でも安全）。
- ログ出力の扱い
  - logging_setup が stdout を StreamHandler に使うようにして、タスクスケジューラや cron でのリダイレクト挙動を考慮。
  - ログディレクトリ作成失敗時にファイルハンドラ作成をスキップして安全にフォールバックするよう修正。
- プロセス優先度の安全ハンドリング
  - set_process_priority / set_cpu_affinity は権限不足やプラットフォーム差で失敗した場合に警告を出し処理を中断（例外ではない）。

### Notes / その他
- 監視ループ・エンジン起動の停止制御はフラグファイル（data/stop_requested.flag）に依存するため、運用時は適切なフラグ管理が必要です。
- config の自動 .env 読み込みはプロジェクトルートを基準に行われます（.git または pyproject.toml がない場合は自動ロードをスキップ）。テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- research/factor_research.py は一部実装が続きます（calc_momentum の実装途中でソースが切れているため、完全なファクター計算は次リリース以降に追加予定）。
- Breaking changes はありません（本リリースは初期公開として機能群を整備）。

---

今後の予定:
- factor_research の完成、ファクター正規化・統合ロジック追加
- ExecutionEngine / SystemMonitor の単体テストと E2E テストの拡充
- 銘柄ごとの lot_size 対応（stocks マスタの導入）
- より詳細な運用ドキュメント（運用手順、Kill Switch の運用ガイドなど）

もし特定の箇所（例: ポートフォリオロジック、risk_manager 設定、CLI の挙動）について CHANGELOG に補足してほしい点があれば教えてください。
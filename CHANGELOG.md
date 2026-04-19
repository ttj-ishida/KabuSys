# Changelog

すべての重要な変更をここに記載します。フォーマットは「Keep a Changelog」に準拠しています。

リリースノートはセマンティックバージョニング準拠です。

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム KabuSys の基礎モジュール群、起動スクリプト、ユーティリティ、ポートフォリオ構築ロジック、検証ツールなどを収録しています。

### Added
- 基本パッケージ情報
  - パッケージバージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine の起動、スレッド実行、停止フラグ（data/stop_requested.flag）や PID ファイル管理（data/execution.pid）に対応。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離する設計。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/Reconciler/RiskManager の組み立て。
    - RiskConfig の初期値（max_position_pct など）を設定し、初期ポートフォリオ値を broker.get_available_cash() から取得。
  - システム監視起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを実装。デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL により上書き可能（不正値はデフォルトへフォールバック）。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検知および KeyboardInterrupt による正常終了処理。
    - sqlite3 / duckdb の接続管理と初期化（init_monitoring_db）。

- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動読み込み（.env → .env.local、OS 環境変数優先）。プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
    - クォートや export 記法に対応した .env のパース実装。
    - 各種環境変数のプロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE（値検証）など）。
    - KABUSYS_ENV / LOG_LEVEL の値検証および is_live / is_paper / is_dev のヘルパー。
    - グローバル settings インスタンスをエクスポート。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式に .env ファイルを生成・更新する機能。デフォルト値・選択肢・シークレット入力対応。
    - .env の読み書き（既存読み込み、書式整形）を提供。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - .env や config/*.yaml の基本検証。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、PyYAML が無ければ YAML 検証をスキップ。
    - --strict オプションで警告を FAIL 扱い（exit(1)）にする機能。

- ロギング / プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。
    - LOG_DIR 環境変数・引数でログ出力先を変更可能。既にハンドラがある場合は一旦クリアして再設定。
    - ディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して set_process_priority("high"|"normal"|"low") を提供。アクセス権限不足などは警告でスキップ。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定する機能（対応しない環境では警告でスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、signal_rank でタイブレーク）
    - calc_equal_weights / calc_score_weights（スコア合算がゼロなら等分にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap：既存保有のセクター別時価を算出し、上限超過セクターの候補除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier：regime による投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告して 1.0 フォールバック。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：allocation_method に応じた計算（"risk_based", "equal", "score"）。lot_size（単元）で丸め、max_position_pct や max_utilization、cost_buffer（手数料/スリッページ見積）を考慮した aggregate cap のスケーリングアルゴリズムを実装。
    - 空価格や非正数価格の扱い、スケールダウン時の端数処理（残差順に lot 単位で追加配分）を実装。

- 研究 / 分析ユーティリティ（部分実装）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / MA / ATR / Volume 系の計算方針・定数を定義。DuckDB 接続を受け取り prices_daily 等を参照して計算する設計。
    - （注意）ファイル末尾の calc_momentum 実装は途中で切れており未完の状態。

- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 検証指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。--from / --to を指定した期間フィルタ、P95 算出、閾値判定（稼働率 >=99%、fill_rate >=90% 等）。
    - generate_report の出力フォーマットを実装。

### Changed
- なし（初回リリースのため既存の変更点はありません）。

### Fixed
- なし（初回リリース）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- なし。

### Notes / 備考 / 既知の問題
- factor_research.calc_momentum の実装が途中で終了しており、関数本体が未完成です（ファイル末尾の start_da による切断）。このモジュールは現在設計段階・部分実装扱いです。
- apply_sector_cap 内の価格欠損（price が 0.0 や None）の扱いについて TODO コメントが残っています。将来的に前日終値や取得原価によるフォールバックを検討してください。
- ログディレクトリ作成やプロセス優先度の設定は実行環境の権限に依存します。権限不足時は警告を出して処理をスキップする設計です。
- .env 自動読み込みはデフォルトで有効です。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視用 DB に settings.sqlite_path を常に使用します（監視は環境に依存しない設計）。一方、実行エンジンは paper_trading 環境では paper_sqlite_path を使用して完全に分離されます。

このリリースは基盤機能（設定管理、起動スクリプト、ロギング、プロセスマネジメント、ポートフォリオ構築ロジック、検証ツール）を整えた初回の公開版です。今後、research モジュールの完成、テスト追加、エラーケースの堅牢化、ドキュメント充実などを予定しています。
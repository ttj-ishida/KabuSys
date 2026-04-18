# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-18

### Added
- 初期リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
- 環境設定 / 設定読み込み
  - .env 自動読み込み機能を追加。プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env のパーサ実装を追加。`export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いをサポート。
  - Settings クラスを追加。環境変数をプロパティとして扱う一元化された API（J-Quants / kabu API / DB パス / ログレベル / 監視しきい値など）。KABUSYS_ENV, LOG_LEVEL 等の検証（有効値チェック）を含む。settings のシングルトンを提供。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装し、.env の初期作成・更新をサポート。シークレット項目のマスク表示、選択肢サポート、`--env-file` オプションあり。
  - .env 書き込み時にファイル内容テンプレートを出力（コミット禁止の注意を含む）。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。必須環境変数の存在検査、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DUCKDB/SQLITE パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML が利用可能な場合）を実行。`--strict` フラグで警告を FAIL 扱いにできる。
  - 本番（live）向けの追加ガード（LINE トークン・ユーザーID 未設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。

- 実行用スクリプト
  - `run_execution.py` を追加。ExecutionEngine 起動スクリプト。起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB 接続を確立。`KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を別スレッドで実行。data/stop_requested.flag による停止、PID ファイル管理、監視テーブルの初期化（冪等）を行う。
  - `run_monitoring.py` を追加。SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）でポーリング間隔を上書き可能。監視用 DB は環境に関わらず本番 sqlite_path を使用。停止フラグ検出、例外発生時のログ、最後に DB 接続をクローズ。

- 監視 / DB ユーティリティ
  - monitoring 用 DB 初期化（init_monitoring_db）呼び出しを run_execution / run_monitoring で行い、監視テーブルの存在を保証（冪等）。

- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority` を追加。Windows / POSIX（Linux, macOS, FreeBSD）差異を吸収してプロセス優先度を設定する set_process_priority() と、CPU コア数を最初の N コアに固定する set_cpu_affinity() を実装。権限不足や未対応 OS を検出した場合は警告ログを出して安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を追加。スコア全て 0 の場合は等金額にフォールバック。
  - risk_adjustment: セクター集中排除 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier を追加。未知のレジームは警告を出して 1.0 にフォールバック。apply_sector_cap は "unknown" セクターを除外しない設計。
  - position_sizing: 株数決定 calc_position_sizes を追加。allocation_method として "risk_based" / "equal" / "score" をサポート。lot_size（単元）丸め、単銘柄上限・利用率上限の適用、コストバッファの考慮、aggregate cap を超えた場合のスケーリングと残差配分ロジックを実装。現在は単一 lot_size を全銘柄共通で使用。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research` を追加。DuckDB を用いたモメンタム（1M/3M/6M, MA200乖離）とボラティリティ（ATR20、20日平均売買代金、出来高比率）計算関数を実装。prices_daily / raw_financials のみ参照し外部 API に依存しない設計。計算範囲バッファと欠損データ時の挙動を明示。

- Paper Trading 検証レポートツール
  - `kabusys.tools.paper_verification_report` を追加。paper_trading 用 SQLite（デフォルト data/paper_trading.db）から統計を集計して検証レポートを生成。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定するしきい値を実装。日付フィルタ（--from / --to）と --db オプションをサポート。

- パッケージエクスポート
  - package の __init__ を追加しバージョンを 0.1.0 に設定。portfolio サブパッケージの関数をトップレベルで再エクスポート。

### Changed
- .env パーサのルールを明確化：
  - クォートあり/なしの違い、エスケープ挙動、インラインコメントの扱い、`export` プレフィックス対応等を実装して既存の .env フォーマットとの互換性を高めた。
- 設定ロード順序を明確化：
  - OS 環境変数 > .env.local > .env の優先順位で読み込む（既存 OS 環境変数は保護される）。
- run_monitoring のデフォルトポーリング間隔に MONITOR_POLL_INTERVAL 環境変数を導入。無効値はデフォルトにフォールバックし警告ログを出す。

### Fixed
- 複数箇所での安全なリソースクローズ（SQLite / DuckDB 接続の finally によるクローズ）を追加してプロセス終了時のリソースリークを防止。
- run_execution: 停止フラグ存在時に起動をスキップするガードを追加（停止中に誤ってエンジンを起動しないように）。

### Documentation / Notes
- 多くの関数・モジュールに docstring と使用例・設計方針を追加。特にポートフォリオ構築ロジックやファクター計算関数は PortfolioConstruction.md / StrategyModel.md 相当の参照セクション番号を注記。
- config_setup の出力 .env テンプレートは Git へのコミット禁止の注意を明記。

### Known issues / TODO
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO を残留。将来的に前日終値や取得原価などのフォールバック価格の導入を検討。
- position_sizing: lot_size を銘柄毎に持たせる拡張（stocks マスタへの lot_size 追加）を将来の拡張として記載。
- config/*.yaml の内容検証は PyYAML に依存。PyYAML 未インストール時は検証をスキップし警告を出す仕様。

---

注: 本 CHANGELOG は現在のコードベースの実装内容から推測して作成した初期リリースノートです。将来的な変更はセマンティックバージョニングに従って追記してください。
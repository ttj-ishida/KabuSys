# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」仕様に準拠しています。  
バージョン番号はパッケージ内の __version__ に基づきます。

※ 本ドキュメントは提供されたコード内容から機能・設計を推測して作成しています。

## [Unreleased]

### Added
- （なし）

### Changed
- （なし）

### Fixed
- （なし）

---

## [0.1.0] - 2026-04-19

最初の公開リリース。自動売買システムのコアユーティリティ、実行・監視スクリプト、設定管理、ポートフォリオ構築ロジック、検証ツールなどを含む。

### Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - 複数の起動スクリプト・CLI・ユーティリティ・ライブラリを収録。

- 実行エンジン / 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db）を使用して本番 DB と分離する設計。
    - BrokerClientFactory を利用して環境に応じたブローカークライアント（モック / 実ブローカー）を生成。
    - ExecutionEngine を別スレッドで実行し、デーモン化して停止フラグ（data/stop_requested.flag）で安全に停止可能。
    - PID ファイル（data/execution.pid）サポート。
    - 実行前に監視用テーブルの初期化を行い（init_monitoring_db）、DuckDB へも接続。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを管理。
    - stop フラグ（data/stop_requested.flag）でループを終了。例外発生時もログを残して次ポーリングへ継続。
    - プロセス優先度を起動時に "high" に設定。

- 設定管理
  - config.py: Settings クラスを導入。
    - .env の自動読み込み機能（プロジェクトルートを検出して .env / .env.local を読み込み、OS 環境変数を保護）。
    - .env パース機能は export 表記、クォート、エスケープ、インラインコメントなどに対応。
    - 多数のプロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、閾値設定等）を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - env/log_level の入力検証（allowed values の検証）。

  - config_setup.py: 対話式 .env 生成ウィザードを追加。
    - 必要項目・任意項目を対話的に入力して .env を作成。
    - シークレット項目はマスク表示。既存 .env の読み込み・再利用に対応。
    - 保存前確認プロンプトを実装。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV の妥当性チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パース確認（PyYAML が存在する場合）など。
    - --strict オプションで警告も失敗として扱う。
    - live 環境向けの追加ガード（LINE トークン未設定や Kill Switch 設定などの警告）。

- ロギング / システムユーティリティ
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソール出力のみで継続。
    - ログレベルとログディレクトリの解決順を明記。

  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して nice 値や Windows 優先度を設定。
    - set_cpu_affinity で最初の N コアにプロセスを固定可能（例外や権限不足は警告でスキップ）。
    - 権限不足や未対応 OS は安全にスキップしてログ警告を出す。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択（同スコアは signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分 / スコア重みでの重み計算。スコア合計が 0 の場合は等配分へフォールバック（警告ログ）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別集中をチェックし、既存保有比率が上限を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）を提供。未知の値は警告後 1.0 フォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に基づき発注株数を計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、合計投下上限（available_cash）を考慮。
    - cost_buffer を考慮した保守的なコスト見積もりと、合計コストが available_cash を超える場合のスケールダウン実装（小数端数は lot 単位で再配分するアルゴリズムを実装）。
    - 価格欠損時はスキップする安全措置とデバッグログ。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB から各種指標を集計。
    - 集計指標: システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、レイテンシ（avg/max/P95）など。
    - P95 計算、日付フィルタ（--from / --to）、基準値を超過した場合は FAIL 判定を行う。
    - DB が存在しない / テーブルが無い場合に graceful に N/A やデフォルトを返す。

- データ解析 / リサーチ
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（モメンタム、MA200、ATR、ボリューム等）の初期実装（関数シグネチャと設計方針を含む）。（実装途中のファイルあり）

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- （該当なし）

### Notes / Design Decisions
- 設定読み込みは OS 環境変数を保護する設計（.env 読み込み時に既存 OS 変数は上書きしない／.env.local で上書き可能だが OS 変数は protected）。
- 監視（monitoring）は環境にかかわらず production 用 sqlite_path を使用する方針（運用監視は本番 DB を参照して行う）。
- Paper Trading は本番 DB から完全分離される設計（paper_sqlite_path を用いる）。
- ログ出力は stdout を基準にしつつ、ファイルローテーションを提供して運用ログ保存を容易にしている。
- process priority / CPU affinity の設定は権限不足の環境でも安全にフォールバックするような実装。

---

今後の予定（例）
- factor_research モジュールの完全実装（各ファクター計算ロジックの完成）。
- ExecutionEngine / SystemMonitor の詳細実装に関する追加の安定化／テスト。
- 銘柄ごとの lot_size を master データから参照する仕組みの導入。
- 単体テスト・CI の追加、型チェック強化、ドキュメント充実。

（以上）
# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
初回リリース (v0.1.0) の内容をコードベースから推測してまとめています。

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール類を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作する仕様を持つ。停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の管理に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用の sqlite_path を使用する実装になっている。
- 設定・環境管理
  - config.py: .env の自動読み込み機能（.env, .env.local）、.env のパースロジック（export 形式・クォート/エスケープ・インラインコメント対応）や、Settings クラスによるプロパティ型の環境変数アクセスを追加。PAPER_FILL_MODE の妥当性検査、KABUSYS_ENV / LOG_LEVEL の検証、デフォルトパス（DuckDB/SQLite 等）を提供。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。シークレット項目はマスク表示、既存 .env の読み込みと更新、保存前の確認を行う。デフォルト値や説明を提示し .env を生成する。
  - validate_config.py: 起動前の設定検証 CLI を追加。.env の必須値チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ検査、config/*.yaml の存在・パース検証（PyYAML 任意）や本番環境向けの追加ガードを実装。--strict モードで警告を失敗扱いにできる。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: アプリ共通のログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテートのファイルハンドラ（TimedRotatingFileHandler、デフォルト logs/、30日保持）をルートロガーに設定。既存ハンドラの重複防止処理（クリア）あり。ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみで継続。
  - utils/process_priority.py: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority, set_cpu_affinity）。権限不足や未対応プラットフォームでは警告を出してスキップする安全設計。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコアが全て 0 の場合はフォールバックロジックあり。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに基づく投資乗数 calc_regime_multiplier を追加（"bull"/"neutral"/"bear" に対応、未知レジームはフォールバック）。
  - portfolio/position_sizing.py: 各銘柄の発注株数を決定する calc_position_sizes を追加。allocation_method（"risk_based"/"equal"/"score"）をサポートし、単元株丸め（lot_size）、個別上限・合計キャッシュに基づくスケーリング、コストバッファ考慮、aggregate cap によるスケールダウンと残差処理を実装。
- 監視・分析ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計・判定するレポート生成スクリプトを追加。CLI オプションで期間や DB パスを指定可。デフォルト閾値（稼働率 99% など）を定義して PASS/FAIL 判定を出力。
- データ分析（着手）
  - research/factor_research.py: DuckDB 接続を前提にファクター（Momentum, Value, Volatility, Liquidity）を計算するモジュールを追加（モメンタム計算などの実装方針と定数を含む）。（実装の続きあり）

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env 読み込み周りの堅牢化
  - export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなどを考慮して .env のパースを強化。
- ログ設定の安全化
  - ログディレクトリ作成やファイルハンドラ作成に失敗してもプロセスが停止しないように処理を分岐し、標準出力のみで継続する挙動を採用。
- プロセス優先度/CPU affinity 設定の失敗は警告ログにして安全にスキップするように修正（権限不足や未対応環境での例外抑制）。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の取り扱いに関する注意
  - .env ファイルは絶対に Git にコミットしないことを README / .env ヘッダに明記している（config_setup の出力）。
  - Settings は必須トークンが未設定の場合に ValueError を送出することで起動前の誤設定を検出しやすくしている。

---

注記・運用上の重要点（コードから推測）
- 監視コンポーネント（run_monitoring）は明示的に「監視は環境にかかわらず本番 sqlite_path を使用する」とコメントにあるため、KABUSYS_ENV による分離を期待する運用者は挙動に注意する必要があります。
- run_execution は paper_trading モードで専用の DB に記録するため、本番データと完全に分離してペーパートレードを行える設計です。
- process_priority の設定は OS や権限に依存するため、設定に失敗した場合はログで警告が出力されますが処理自体は継続します。
- PyYAML がインストールされていない環境でも validate_config は動作するが、YAML の中身検証はスキップされ警告が出ます。
- これらはコードベースから推測した初期機能一覧です。実際のリリースノート作成時は実装者の意図や変更履歴（コミットログ）に基づいて調整してください。
# Changelog

すべての重要な変更点を記載します。フォーマットは「Keep a Changelog」に準拠します。

※ このファイルはコードベースの内容から推測して作成しています。

## [Unreleased]

（現時点の未リリース変更は特にありません）

## [0.1.0] - 2026-04-20

初回リリース — KabuSys の基本コンポーネントとユーティリティを追加。

### Added
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合はモックブローカを利用し、paper_trading 用 DB（data/paper_trading.db など）に記録する仕組みを備える。停止用フラグ（data/stop_requested.flag）や実行 PID ファイル（data/execution.pid）を使用。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する。
- 設定・検証・セットアップ CLI
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成/更新）。シークレット項目はマスク表示。保存前に確認を行い、.env に警告コメントを付与して出力。
  - validate_config.py: .env と config/*.yaml の起動前検証ツールを追加。必須環境変数チェック、パス存在チェック、YAML パース検証（PyYAML がインストールされている場合）、本番時の追加チェック、`--strict` モードをサポート。
- 設定管理
  - config.py: Settings クラスと自動 .env ロード機構を追加（プロジェクトルートを .git / pyproject.toml で検出）。`.env` と `.env.local` の読み込み順と上書きルール（OS 環境変数を保護）を実装。`.env` の行パーサは `export KEY=val`、クォート、エスケープ、インラインコメントを考慮。
  - Settings は各種環境変数をプロパティで提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_*、閾値系など）。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定を導入。コンソール出力は stdout、ファイル出力は日次ローテーション（TimedRotatingFileHandler）かつ 30 日分保持。既存ハンドラのクリアやログディレクトリ作成のフォールバックを実装。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS の差分を吸収し、psutil を使って安全に設定。権限不足などは警告してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等分にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）を実装。既存保有を考慮したセクター別エクスポージャー計算や、unknown セクター扱いの挙動を定義。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash でスケールダウン）、cost_buffer の導入などを実装。価格欠損時のスキップやログ出力対応。
  - portfolio/__init__.py で上記関数をエクスポート。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を集計するレポートを追加。閾値（稼働率 99%、注文成功率 90% 等）による PASS/FAIL 判定、および日付フィルタ（--from / --to）と --db オプションをサポート。
- research/factor_research.py（ファクター計算基盤）
  - DuckDB を利用してモメンタム等のファクターを計算するための基盤（モメンタム期間や ATR 期間等の定数定義）。（ファイル末尾は途中だが設計方針・用途を含む）
- DB 接続
  - run_* スクリプトや各コンポーネントで sqlite3 と duckdb の接続を使用するよう追加。monitoring 用 DB の初期化関数 init_monitoring_db を呼び出して監視テーブルの存在を保証。

### Changed
- ログ出力の標準化
  - 全アプリケーション（monitoring/execution 等）で setup_logging を呼び出すことで、出力先・フォーマット・ローテーションを統一。
  - コンソール出力は stdout を使う（cron 等で stdout/stderr を一本化して扱いやすくするため）。
- .env の読み込みポリシー
  - OS 環境変数を保護しつつ .env/.env.local を自動的にロードする実装に変更。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- run_monitoring の挙動
  - MONITOR_POLL_INTERVAL の値が不正（非整数や 0 以下）の場合は警告してデフォルト（60 秒）にフォールバックするよう改善。
  - 監視ループは stop フラグファイルを監視し、検出時にループを抜ける仕様を明示。
- 実行環境分離
  - run_execution は paper_trading 時に専用の paper_sqlite_path を使用し、本番データと分離するように設計。
- process_priority と CPU affinity の安全性強化
  - 対応 OS を限定し、権限不足や未サポート API 呼び出し時は警告して処理を続行するように変更。

### Fixed
- calc_score_weights: 全銘柄のスコア合計が 0 の場合にゼロ除算を避け、等金額配分へフォールバックして警告を出力するよう修正。
- apply_sector_cap:
  - portfolio_value <= 0 や候補なしの場合に早期リターンする安全処理を追加。
  - 売却予定銘柄（sell_codes）をエクスポージャー算出から除外できるようにした。
- position_sizing:
  - aggregate cap を適切にスケーリングし、lot_size 単位で丸めるロジックを実装。
  - cost_buffer を取り入れて約定コストを保守的に見積もるように変更。
- logging_setup: ログディレクトリ作成失敗時にファイル出力をスキップしてコンソール出力だけにフォールバックするよう修正。
- config._parse_env_line: export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理を正しく扱うよう実装。

### Security
- config_setup で生成される .env に対して「絶対に Git にコミットしないこと」を明記して出力するなど、機密情報取り扱いに関する注意喚起を追加。
- 環境変数必須項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）に対する検証を validate_config にて強化。プレースホルダ値検出時に警告を出す。

### Notes / Known limitations
- portfolio/position_sizing の価格欠損時（price が 0.0）の取り扱いは暫定的。将来的には前日終値や取得原価によるフォールバックの導入を想定（TODO コメントあり）。
- research/factor_research.py はモメンタム計算の実装が途中（ファイル末尾が切れている）であり、実装完了が必要。
- validate_config の YAML 内容検証は PyYAML 未導入時にスキップされる（警告表示）。
- process_priority の一部機能はプラットフォーム依存かつ権限が必要なため、汎用環境でエラー発生時は警告を出して処理を継続する。

---

今後の改善候補:
- ファイル単位のユニットテスト追加（特にポートフォリオ算出・position sizing 周り）。
- research/factor_research の完全実装と単体検証。
- ログの構造化（JSON 出力等）やメトリクス収集の追加。
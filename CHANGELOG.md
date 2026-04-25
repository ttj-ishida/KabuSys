# CHANGELOG

このプロジェクトは Keep a Changelog の形式に準拠しており、重要な変更点を分かりやすく記録します。

すべての変更は SemVer に従います。現在のリリースは 0.1.0 です。

## [0.1.0] - 2026-04-25
初回リリース — 基本的な自動売買フレームワークのコア機能を実装しました。

### Added
- 起動スクリプト
  - run_execution: 実行エンジン（ExecutionEngine）を起動するエントリポイントを追加。KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite DB（data/paper_trading.db）を使用し、MockBrokerClient を利用して実行を完全に分離する仕組みを提供。停止フラグ（data/stop_requested.flag）検知、PID ファイル管理、デーモンスレッドでのセッション実行をサポート。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番用 sqlite_path を使用する設計。

- 設定管理
  - config.py: .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。.env/.env.local の読み込みルール（OS 環境 > .env.local > .env）と保護キー（OS 環境変数の上書きを避ける）に対応。Settings クラスを実装し、環境変数の取得・バリデーション（env, log_level, PAPER_FILL_MODE など）を提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成／更新する CLI を追加。デフォルト値、シークレットマスク、選択肢表示等をサポート。
  - validate_config.py: 起動前に .env および config/*.yaml の存在・基本妥当性を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ存在チェック、YAML のパース確認（PyYAML 利用）、本番環境向けのガード項目を含む。--strict オプションで警告を FAIL 扱い可能。

- ロギング & プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows / POSIX（Linux, macOS, FreeBSD）に対応したプロセス優先度設定および CPU affinity 設定のヘルパーを追加。アクセス権限不足や未サポート環境では安全にフォールバックして警告を出力。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py: シグナル候補選定（スコア降順、タイブレークの signal_rank）と等金額・スコア加重の重み計算を実装。スコア総和が 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中の上限チェック（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、ログ出力によるデバッグ情報あり。
  - portfolio/position_sizing.py: 各銘柄の発注株数を計算する主要ロジックを実装。allocation_method として `"risk_based"`, `"equal"`, `"score"` をサポート。単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、総投下キャッシュ上限（max_utilization）、コストバッファを考慮した aggregate cap のスケーリング（スケールダウン + 端数処理）を行う。

- Research / ファクター計算（骨格）
  - research/factor_research.py: モメンタム等のファクター計算モジュールの骨格を追加（DuckDB 接続を受けて prices_daily/raw_financials を参照する設計）。1M/3M/6M リターン、MA200 乖離、ATR、出来高指標等の計算を想定した定数と関数（calc_momentum など）の実装を開始。

- ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 など）を集計して検証レポートを出力するスクリプトを追加。合否基準（閾値）と PASS/FAIL 判定ロジックを実装。コマンドライン引数で期間指定と DB パス指定が可能。

- パッケージ初期化
  - __init__.py: パッケージバージョンを 0.1.0 に設定し、主要サブパッケージを __all__ に列挙。

### Changed
- ログ出力のポリシー
  - logging_setup: デフォルトで stdout に出力するようにし、cron/タスクスケジューラからの起動で stdout/stderr を一本化しやすくした。

### Fixed
- .env パーサーの堅牢化
  - config._parse_env_line: export プレフィックス対応、シングル・ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォート無い場合は '#' の直前が空白ならコメント扱い）など、現実的な .env フォーマットのケースを考慮して改善。

### Notes / 内部実装上の注意
- run_monitoring は Monitoring 用 DB 接続に settings.sqlite_path（本番向け）を常に使用します。開発時の誤操作を避けるための設計意図に基づきます（監視テーブル初期化等を行うため）。
- run_execution は paper_trading モード時に paper_sqlite_path を使い、本番データベースと完全に分離することを意図しています。
- process_priority や CPU affinity の設定は権限によって失敗する可能性があり、その場合は警告に留めて処理を継続します。
- research/factor_research の一部実装は継続作業中（ファイル末尾が途中で切れている箇所があります）。

### Documentation / CLI
- 設定関連の CLI:
  - python -m kabusys.config_setup  — .env 対話ウィザード
  - python -m kabusys.validate_config — 設定検証
  - python -m kabusys.tools.paper_verification_report — ペーパートレード検証レポート生成

## Deprecated
なし

## Removed
なし

## Security
- 機密情報（API トークン等）は .env に格納し、.env を絶対に Git にコミットしない旨の注意を README / .env ヘッダコメントに記載しています（config_setup の出力に明記）。

---

将来的な改善案（予定）
- portfolio.position_sizing: 銘柄ごとの lot_size をサポートするための拡張（stocks マスタ参照）を検討中。
- research.*: DuckDB を使った完全なファクター計算の実装完了（momentum の SQL 実装など）。
- monitor および execution のユニットテスト充実化、E2E テスト用のモック整備。
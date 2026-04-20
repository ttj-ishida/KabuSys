CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠します。  
注: 以下の変更点は提供されたコードの内容から推測して記載したものです。

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

## [0.1.0] - 2026-04-20

### Added
- 初期リリースを追加。
- 実行スクリプト:
  - run_execution.py — ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading SQLite を使用（data/paper_trading.db がデフォルト）し、本番 DB と分離。  
    - ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine のデーモン実行ループを実装。停止フラグ（data/stop_requested.flag）検知時に安全に停止。PID ファイル出力機能を想定（data/execution.pid）。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - Monitoring は環境にかかわらず production 用 sqlite_path を使用する設計。停止フラグでループを終了。例外時のログを残しつつ次ポーリングへ継続。
- 設定管理:
  - config.py — 環境変数 / .env 自動読み込み機能、.env/.env.local の読み込み順、必須値チェック用の Settings クラスを実装。  
    - .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う。  
    - PAPER_FILL_MODE 等のバリデーション、パスの Path 化、env 判定プロパティ（is_live / is_paper / is_dev）を提供。
  - config_setup.py — 対話式 .env 生成ウィザードを追加（.env の初期作成・更新をサポート）。
  - validate_config.py — 起動前に .env / config/*.yaml の設定不備を検出する CLI を追加（--strict オプションあり）。
- 監視 / レポート:
  - monitoring_db 初期化呼び出しを各起動スクリプトで担保（init_monitoring_db を利用）。
  - tools/paper_verification_report.py — Paper Trading 用検証レポート生成ツールを追加。  
    - 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、API レイテンシ（平均/最大/P95）を算出し判定（PASS/FAIL）を表示。  
    - P95 計算、期間フィルタ、DB パスの解決（コマンドライン引数 / 環境変数 / デフォルト）をサポート。
- ポートフォリオ構築モジュール:
  - portfolio.portfolio_builder — シグナル選定 (select_candidates)、等重み・スコア加重 (calc_equal_weights, calc_score_weights) を実装。スコア全 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio.risk_adjustment — セクター上限適用 (apply_sector_cap)、市場レジーム乗数 (calc_regime_multiplier) を実装。未知レジームはフォールバック（1.0）して警告。
  - portfolio.position_sizing — ポジションサイズ算出 (calc_position_sizes) を実装。  
    - risk_based / equal / score の割当方式、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer（スリッページ・手数料見積り）考慮をサポート。
  - portfolio パッケージは上記関数をエクスポート。
- ユーティリティ:
  - utils.logging_setup — 統一的なログ設定ユーティリティを追加。  
    - stdout 出力用 StreamHandler と 日次ローテート（TimedRotatingFileHandler、30日分保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority — クロスプラットフォームのプロセス優先度設定と CPU affinity 設定を追加。Windows / POSIX（Linux, macOS, FreeBSD）に対応し、権限不足や未対応 OS では警告を出してスキップ。
- research:
  - research.factor_research — ファクター計算の雛形を追加（モメンタム、MA、ATR 等を計算する意図を記載）。DuckDB を使って prices_daily / raw_financials を参照する設計（未完の関数あり）。

### Changed
- ログ周り:
  - ログディレクトリ解決の優先順を整理（引数 > LOG_DIR env > デフォルト logs/）。既存ハンドラを削除して重複を防ぐ実装に。
- .env 読み込み:
  - .env のパースを堅牢化（export プレフィックス、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどに対応）。.env.local は .env を上書きする挙動（ただし OS 環境変数は保護）を実装。

### Fixed
- 設定検証:
  - validate_config にて YAML パースを試行し、PyYAML 未導入時には警告を出して検証をスキップするように調整（起動失敗を回避）。
- process_priority / CPU affinity:
  - psutil による優先度設定や affinity 設定で AccessDenied / NotImplementedError が発生した場合に警告を出して継続するようにして、起動の堅牢性を向上。

### Internal / Refactor
- モジュール設計:
  - 監視・実行・設定管理・ポートフォリオ・ユーティリティ・リサーチ・ツール群を分離し、テスト・保守性を考慮した責務分割を実施。
- DB 接続方針:
  - run_monitoring は環境にかかわらず monitoring 用 sqlite_path（Settings.sqlite_path）を使用する方針を明示。run_execution は paper_trading 環境で専用 DB を使用して本番 DB と完全分離する実装。
- 安全停止フラグ / PID:
  - 実行スクリプトはプロセス優先度を起動直後に設定し、停止フラグ（data/stop_requested.flag）を監視して安全にシャットダウンするパターンを導入。ExecutionEngine 側は PID ファイルを扱う想定。

### Notes / 注意事項
- .env ファイルは決してリポジトリにコミットしないでください（config_setup のヘッダにも記載）。
- Settings クラスの一部プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は必須であり、未設定時に ValueError を送出します。validate_config CLI で事前チェックすることを推奨します。
- PAPER_FILL_MODE に無効な値を設定すると ValueError を送出します。許容値は "instant", "partial", "never", "reject"。
- run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能です。0 以下や不正な値はデフォルト（60 秒）にフォールバックします。
- research.factor_research モジュールには未完実装（コメント末尾で切れている部分）が存在します。実際の計算ロジックを完成させる必要があります。

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
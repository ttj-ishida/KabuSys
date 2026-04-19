# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-19

### Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを提供。KABUSYS_ENV に応じて本番/ペーパートレードを切り替え、専用の paper_trading DB（data/paper_trading.db）を使用できるようにした。起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用する設計。

- 環境設定管理とウィザード
  - config.py: .env の自動読み込み機能を実装（.env, .env.local をプロジェクトルートから読み込み、OS 環境変数は保護）。必須値取得ヘルパーや各種設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 関連設定など）を追加。
  - config_setup.py: .env を対話式で生成・更新するウィザードを提供。デフォルト値表示、シークレットマスク、保存前確認、.env の書き出しを実装。
  - validate_config.py: 起動前に .env と config/*.yaml の検証を行う CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば）、本番環境向けのガードチェックを実装。--strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーを統一的に設定するユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力（logs/<app_name>.log、30日分保持）を提供。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティを追加。権限不足や未対応 OS では警告を出して安全にスキップ。

- ポートフォリオ構築関連モジュール
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等配分・スコア加重の重み計算関数を実装。スコアが全て 0 の場合は等配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限チェック（apply_sector_cap）と市場レジームに応じた投資倍率（calc_regime_multiplier）を実装。既存ポジションを考慮したセクター露出算出や unknown セクター扱いのルールを定義。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数算出ロジックを実装。単元株丸め、1銘柄上限、全体資金に対するスケールダウン（aggregate cap）、cost_buffer（手数料・スリッページ見積り）を考慮した分配ロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）からレポートを生成するスクリプトを追加。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計し PASS/FAIL を判定する機能を提供。コマンドラインで期間指定（--from / --to）や DB パス指定（--db）が可能。

- 研究用ファクタ計算基盤
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム、MA200 乖離、ATR、出来高系など）。関数 calc_momentum 等を備え、prices_daily / raw_financials テーブルのみを参照する設計。

### Changed
- 設定自動読み込みの挙動
  - config.py にてプロジェクトルート検出ロジックを導入し、.env 自動読み込みの対象をプロジェクトルート直下の .env / .env.local に限定。OS 環境変数は保護され、.env.local は .env の上書きとして適用される。自動読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。

- DB と監視の扱い
  - run_monitoring.py は監視専用でも環境にかかわらず本番用 sqlite_path を使用することを明示（監視データの一元化）。一方 run_execution.py は paper_trading モード時に paper_sqlite_path を使用して本番 DB と分離。

- ロギングの出力先と挙動
  - setup_logging() は既存ハンドラを安全に閉じてから再設定するように変更（重複ハンドラ防止）。stdout を優先して出力する設計にし、ログディレクトリ作成失敗時はファイル出力を回避して処理継続する。

### Fixed
- 環境変数パースの堅牢化
  - config.py の .env パーサーで export 構文やクォート内のバックスラッシュエスケープ、インラインコメント処理、コメント扱いのルールを改善し、より現実的な .env ファイル形式に対応。

- 実行中の安全停止処理
  - run_execution.py / run_monitoring.py で stop flag（data/stop_requested.flag）や KeyboardInterrupt による安全なシャットダウンを実装。ExecutionEngine は別スレッドで実行し、停止フラグ検知時に engine.stop() を呼ぶ流れを整備。

### Notes
- デフォルトのファイルパスや環境変数
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）
  - SQLite (monitoring): data/monitoring.db（環境変数 SQLITE_PATH で上書き可）
  - Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
  - ログ: logs/<app_name>.log（LOG_DIR 環境変数で変更可）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: Paper Trading の約定モード（instant/partial/never/reject）

- 使用例
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - .env ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

### Deprecated
- なし

### Security
- なし

---

このリリースは初期機能群（環境設定 / 起動スクリプト / ログ設定 / プロトタイプのポートフォリオ・ポジション算出・検証ツール / 研究用ファクター計算）を含みます。今後のリリースで以下を予定しています: Strategy 実装、ExecutionEngine の詳細な注文ロジック強化、監視項目の拡張、ユニットテスト充実化。
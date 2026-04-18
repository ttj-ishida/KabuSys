# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
慣例: 重大な変更 (Breaking Changes) / 新機能 (Added) / 変更 (Changed) / 修正 (Fixed) / セキュリティ (Security)。

## [0.1.0] - 2026-04-18
初回リリース。

### Added
- 基本パッケージとモジュール群を追加。
  - パッケージ概要: kabusys — 日本株自動売買システム (バージョン 0.1.0)。
- 設定管理
  - 環境変数/`.env` の自動読み込み機能を実装（プロジェクトルート探索: `.git` または `pyproject.toml` を基準）。
  - .env パーサーの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを実装。
  - OS 環境変数保護機能（protected）を導入し、`.env.local` の上書きでも OS 環境変数を保持できるようにした。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスを追加し、アプリケーション設定値をプロパティ経由で取得可能にした。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 実行環境（KABUSYS_ENV）等のプロパティを提供。
    - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の入力検証を実装（不正値時に ValueError を送出）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）と paper_fill_mode のサポートを追加。
- 起動スクリプト（CLI）
  - run_monitoring.py: SystemMonitor をポーリングする監視ループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用し、本番 DB とは完全分離。
    - Broker クライアントの Factory 経由生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立てを行い、ExecutionEngine をバックグラウンドスレッドで実行。
    - 停止フラグ・PID ファイル・安全停止処理を実装。
- 設定関連 CLI
  - config_setup.py: 対話式ウィザードで `.env` を作成・更新する CLI を追加。
    - シークレット項目はマスク表示、既存値の再利用、デフォルト提示、保存確認などを実装。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パースチェック（PyYAML 任意）など。
    - --strict オプションで警告を FAIL 扱いにする機能を実装。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を root ロガーへ設定。
    - ログディレクトリ自動作成、ファイル出力失敗時のフォールバックを実装。ログローテーションは 30 日保持。
    - ログレベル・ログディレクトリの解決優先順を明確化。
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux, macOS, FreeBSD) の差分を吸収する実装。
    - set_process_priority(level) で "high"/"normal"/"low" を指定可能（権限不足等は警告を出してスキップ）。
    - set_cpu_affinity(n) で最初の N コアに固定可能（利用不可時は警告）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を制限するフィルタ。既存ポジション評価・売却予定銘柄の除外に対応。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method (risk_based / equal / score) による発注株数決定ロジック。
      - リスクベース計算、単元株（lot_size）丸め、1銘柄上限・集計上限（available_cash）によるスケーリング、cost_buffer を考慮した保守的見積りなどを実装。
- 監視・モニタリング
  - monitoring の初期化（init_monitoring_db を利用）フックを起動時に実行して監視テーブルの存在を保証。
  - SystemMonitor の単回チェック(check_once) をループで呼び出す起動フローを提供（例外はログに残して次ポーリングへ継続）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード DB を基にレポートを生成する CLI を追加。
    - システム稼働率、注文成功率（fill/send）、リスク却下数、API レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定を出力。
    - P95 算出、日付フィルタ、DB 存在チェック、しきい値定義（稼働率 99% など）を実装。
    - CLI オプション: --from / --to / --db、環境変数 PAPER_TRADING_SQLITE_PATH の優先解決。

### Changed
- なし（初回リリースのため変更履歴はなし）。

### Fixed
- なし（初回リリースのため修正履歴はなし）。

### Security
- .env ファイルを .git にコミットしないよう README・ウィザード側で注意喚起（.env は絶対にコミットしない旨を明記）。

### Notes / Runtime behavior
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルト 60 秒にフォールバックし、警告を出力する。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用 DB（data/paper_trading.db を想定）を使用し、MockBroker を利用して本番 DB とは完全分離して動作することを想定している。
- validate_config は PyYAML が未インストールの場合、YAML の内容検証をスキップして警告を出す。必要に応じて CI で PyYAML を導入することを推奨。
- process_priority や CPU affinity は権限やプラットフォーム制約により失敗する可能性があり、その場合は警告を出して処理を継続する設計。

---

今後の予定（例）
- research モジュールのファクター計算（続き）の完成とユニットテスト追加
- ExecutionEngine / Broker クライアントの詳細実装とエンドツーエンドテスト
- config / secret 管理の改善（Vault 等の導入検討）
- 単体テスト、CI ワークフロー、ドキュメント強化

（初回リリースのため CHANGELOG は上記を記録しています）
# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション構成（初期リリース）。
- 起動スクリプト:
  - run_execution.py — ExecutionEngine 起動用。KABUSYS_ENV に応じて paper_trading 用のモックブローカを利用し、ペーパートレード時は専用 SQLite（data/paper_trading.db をデフォルト）で本番 DB と分離して動作する。停止フラグ（data/stop_requested.flag）や実行 PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py — SystemMonitor のポーリングループ起動用。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用し、停止フラグで安全にループ終了する。
- 設定・環境管理:
  - config.py — 環境変数 / .env の自動ロード、プロジェクトルート検出（.git または pyproject.toml）、堅牢な .env パーサ、Settings クラスを提供。PAPER_FILL_MODE のバリデーションや各種パス/閾値プロパティを含む。
  - config_setup.py — 対話式 .env ウィザード。既存 .env の読み込み/更新とファイル書き出しをサポート。
  - validate_config.py — 起動前の設定検証 CLI。必須環境変数や config/*.yaml の存在チェック、KABUSYS_ENV の保護チェック等を行い、--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）:
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選出。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア全体が 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限の適用（既存保有を考慮）。"unknown" セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知値はフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出。単元株（lot_size）処理、max_position_pct／max_utilization／cost_buffer を考慮した aggregate cap スケーリング、残差処理の安定化ロジックを実装。
- ユーティリティ:
  - utils.logging_setup: ルートロガーの一括設定ユーティリティ。stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/、30 日保持）を設定。既存ハンドラの二重設定を防止し、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する。
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定のユーティリティ。権限不足や未対応 OS の場合は警告を出してスキップする安全設計。
- データ分析 / ツール:
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプト。システム稼働率、注文成功率・送信率、API レイテンシ（P95 など）、リスク却下数を集計し PASS/FAIL 判定を出力。期間フィルタ（--from／--to）と DB パス（--db / 環境変数）をサポート。デフォルトの閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を備える。
  - research.factor_research（部分実装）: DuckDB 接続で価格／ファイナンステーブルから Momentum 等のファクターを計算するモジュールの骨格を追加。

### Changed
- ロギング挙動:
  - StreamHandler を stdout に固定（cron 等で stdout/stderr を一元化する運用を想定）。
  - setup_logging は既存ハンドラを安全に flush/close してから置換することで二重出力を防止。
- 実行時のプロセス優先度設定を起動直後に行うよう各起動スクリプトで統一（set_process_priority("high") を呼び出す）。
- DB の扱い:
  - 監視側（run_monitoring）は環境に依らず Settings.sqlite_path（本番監視 DB）を使用する方針を明記。
  - 実行側（run_execution）は paper_trading 環境なら専用 DB（paper_sqlite_path）を使用し、本番 DB と分離する。

### Fixed
- .env パーサの改善:
  - export プレフィックスのサポート、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなしでの # コメント認識ルールなどを実装し、実務でありがちな .env 記述差分に耐性を持たせた。
- logging_setup のディレクトリ作成失敗時の動作を改善。ファイルハンドラ作成失敗は警告に留め、コンソール出力は継続する。

### Security
- 環境変数・機密情報取り扱い:
  - config_setup のウィザードはシークレット項目をマスク表示して入力を補助。.env のテンプレートに注意書きを追加し、.env を誤ってコミットしないようドキュメント化。
  - validate_config による本番（KABUSYS_ENV=live）時の追加警告（LINE トークン未設定や Kill Flag 自動クリア設定の危険性）を実装。

### Notes / Known limitations
- research.factor_research はファクター計算の骨格を含みますが、実装の一部（関数続きの実装）は未完です（calc_momentum の実装途中）。
- 一部 TODO コメント（例: position_sizing の銘柄別 lot_size サポート、risk_adjustment の価格フォールバック等）が残っています。
- process_priority/set_cpu_affinity はプラットフォーム依存の許可（権限）により動作しないケースがあり、その場合は警告を出して安全にスキップします。
- .env 自動ロードはプロジェクトルートの自動検出に依存するため、配布パッケージ等でプロジェクトルートが検出できない場合はスキップされます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

将来のリリースでは、研究モジュールの完全実装、統合テスト、戦略・実行コンポーネントのさらなる堅牢化（エラーリカバリ、メトリクス出力強化）、および運用向けドキュメントの充実を予定しています。
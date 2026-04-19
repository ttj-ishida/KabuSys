# Changelog

すべての公開可能な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0 — 2026-04-19

## [0.1.0] - 2026-04-19

Added
- 初期リリース: KabuSys のコアユーティリティ・実行スクリプト・ポートフォリオ構築ロジックを追加。
- 環境設定管理
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - .env パーサを実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - Settings クラスを追加し、環境変数の取得とバリデーションを集約（J-Quants / kabuAPI / DB パス /ログレベル /実行環境など）。
  - PAPER_FILL_MODE（instant/partial/never/reject）等の専用設定を追加。
  - paper_trading 用 DB の分離設定（PAPER_TRADING_SQLITE_PATH）をサポート。
- 設定ウィザード CLI
  - config_setup.py に対話式 .env ウィザードを追加。既存値の再利用、シークレット入力、保存機能付き。
- 設定検証 CLI
  - validate_config.py を追加。必須環境変数・KABUSYS_ENV 値・ログレベル・DB パス・config/*.yaml の存在と YAML パース（PyYAML があれば）・本番時のガード検査を実行。
  - --strict オプションで警告を失敗扱いにできる。
- 実行 / 監視の起動スクリプト
  - run_execution.py: ExecutionEngine 起動フローを追加。BrokerClientFactory に基づくブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、スレッド実行、停止フラグ検出による安全停止、paper_trading 時の DB 分離をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループを追加。MONITOR_POLL_INTERVAL 環境変数による間隔上書き、停止フラグ検出、監視 DB 初期化を実装。
  - いずれも PID ファイル・停止フラグによる外部制御を想定。
- ログ設定ユーティリティ
  - utils/logging_setup.py を追加。root ロガーの既存ハンドラをクリアしてから、stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）を設定。LOG_DIR/LOG_LEVEL の解決順を持つ。ログディレクトリ作成失敗時はファイル出力をフォールバック。
- プロセス優先度 / CPU affinity ユーティリティ
  - utils/process_priority.py を追加。Windows / POSIX（Linux/macOS/FreeBSD）を吸収して set_process_priority を提供。権限不足や未対応 OS 時には警告を出してスキップ。
  - set_cpu_affinity でプロセスの CPU コア固定をサポート（権限・未対応環境は警告）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を追加。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を追加（未知レジームはフォールバックして警告）。
  - portfolio.position_sizing: position size 計算 calc_position_sizes を追加。risk_based / equal / score の割当手法、lot_size（単元株）丸め、1銘柄上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した安全なスケーリングロジックを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。paper_trading 用 SQLite（デフォルト data/paper_trading.db）から集計し、稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）などを出力。閾値判定（PASS/FAIL）と期間指定オプションをサポート。
- 研究用ファクター計算基盤
  - research/factor_research.py を追加。DuckDB 接続を受け取りモメンタム / ボラティリティ / Value 等の計算を行う設計。関数の骨格と定数を導入（実装途中の箇所あり）。

Changed
- ロギングの統一:
  - 全起動スクリプトは setup_logging を呼び出して統一的なログ出力を行うように統一。
- DB 初期化:
  - 監視テーブルの初期化関数 init_monitoring_db を起動時に呼び出すようにして、実行・監視が監視テーブルの存在を前提に安全に動作するように変更（冪等）。

Fixed / Robustness
- .env 読み込みの堅牢化:
  - ファイル読み込み失敗時に警告を出して続行。
  - OS 環境変数を保護する protected 引数を導入し、.env の上書きを制御（.env.local の上書き等の制御を実現）。
- ログ二重設定の防止:
  - setup_logging が既存ハンドラを削除してから再設定するようにして、複数回呼び出しによる二重ログ出力を回避。
- プロセス優先度 / CPU 固定の失敗耐性:
  - psutil での権限エラーや未実装 API を捕捉して警告にフォールバック。

Documentation / UX
- 各モジュールに docstring を追加し、使用例や設計方針、引数仕様を明記。
- config_setup の出力フォーマット・ヘッダに注意喚起（.env を絶対に Git にコミットしない等）を追加。
- validate_config の出力フォーマット（INFO/WARNING/ERROR）を整備。

Notes / Known limitations
- research/factor_research.py は骨格が追加されていますが、ファクター計算の一部が未完（ファイル末尾で途中終了）です。今後のリリースで完成予定です。
- calc_position_sizes 等は現在、単元株数 (lot_size) を全銘柄共通で扱っている。将来的に銘柄別の lot_map 対応を検討中（TODO を残しています）。
- 一部の機能（ブローカークライアントの具体的実装や ExecutionEngine 内部の詳細）はこのリリースのスコープ外であり、外部モジュール（BrokerClientFactory 等）に依存しています。

---

このリリースは KabuSys のコア基盤を揃える初期リリースです。今後は research モジュールの完成、Strategy 実装、監視指標の拡張やテストカバレッジの強化を予定しています。
# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
メジャーな追加・変更点をコードベースから推測して日本語でまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-23
最初の公開リリース相当。主要機能の追加とユーティリティ群を導入。

### Added
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。プロセス優先度設定、SQLite/ DuckDB 接続、ブローカークライアント生成、スレッド実行、停止フラグ検知、PID ファイル管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能）。停止フラグ検知、例外安全なループ、SQLite/DuckDB 閉処理を備える。
- 設定管理・ウィザード・検証
  - config.py: Settings クラスを導入。環境変数の自動読み込み（.env / .env.local の優先順位、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）、必須/任意設定や型変換、Paper trading 用 DB パスや各種監視閾値等のプロパティを提供。
  - config_setup.py: .env を対話的に作成・更新するウィザード CLI。既存値の読み込み、シークレットマスク、選択肢・デフォルト対応、保存機能を実装。
  - validate_config.py: 起動前に .env と config/*.yaml のチェックを行う CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス・YAML パース確認、--strict モードをサポート。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py:
    - select_candidates: シグナルをスコアでソートして上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等金額にフォールバックし警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有からセクターエクスポージャを計算し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック）を提供。
  - portfolio/position_sizing.py:
    - calc_position_sizes: リスクベース / equal / score の各配分方式をサポート。単元株（lot_size）丸め、max_position_pct 上限、max_utilization による集計制限、cost_buffer を用いた保守的見積り、available_cash に対するスケーリング・端数配分ロジックを実装。
  - portfolio/__init__.py: 上記関数群を公開 API としてエクスポート。
- ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティ。コンソール (stdout) と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定。LOG_LEVEL / LOG_DIR の解決順を実装し、ログディレクトリ作成失敗時はファイル出力を無効化してフォールバックする。
  - utils/process_priority.py: Windows / POSIX (Linux, macOS 等) を吸収したプロセス優先度設定と CPU affinity 設定。psutil を利用し、権限や未サポート環境でのフォールバック処理を実装。
- Paper Trading 周辺
  - run_execution.py に Paper Trading 用の DB 分離を導入（KABUSYS_ENV=paper_trading 時に settings.paper_sqlite_path を使用し、本番 DB と完全分離）。
  - BrokerClientFactory により環境に応じて MockBrokerClient の利用を想定（paper_trading 時）。
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成スクリプトを追加。稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。CLI 引数 --from / --to / --db をサポート。
- データベース関連
  - DuckDB を分析用 DB として利用（duckdb_path）するワークフローを導入。複数スクリプトで DuckDB 接続を利用。
  - monitoring 用の SQLite 初期化を行う init_monitoring_db 呼び出しを各所に追加（冪等に監視テーブルを保証）。
- 研究モジュール（骨組み）
  - research/factor_research.py: ファクター計算モジュールの骨組みを実装（Momentum, Value, Volatility, Liquidity の設計方針、DuckDB を使った計算想定）。モメンタム計算関数の開始実装あり（未完：ファイル末尾が途切れています）。

### Changed
- ログの出力ポリシー
  - StreamHandler は stdout を利用するように統一。cron/Task Scheduler 等での stdout リダイレクト運用を意識した設計に変更。
- .env 読み込みの挙動
  - OS 環境変数を保護するため、.env と .env.local の読み込みで既存の OS 環境変数を上書きしない（.env.local は override=True だが protected による保護を実施）。自動読み込みを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加。

### Fixed
- 環境変数パースの堅牢化
  - _parse_env_line にて export プレフィックス、シングル・ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などを正しく処理するように実装し、不正な .env 行による誤読を軽減。
- 例外耐性の強化
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもループ継続するように例外捕捉とログ出力を追加。
  - 起動時にログディレクトリ作成失敗やファイルハンドラ作成失敗が発生してもフォールバックしてコンソールログのみで継続できるようにした。

### Security
- .env の取り扱い注意書きを config_setup.py の生成ヘッダに追加（.env を絶対に Git にコミットしないことを明示）。

### Documentation / Comments
- 各モジュールに日本語ドキュメント文字列（docstring）と使用例を追加。PortfolioConstruction.md / StrategyModel.md 等の設計ドキュメント参照箇所を明記して実装の意図を説明。

---

注記:
- research/factor_research.py はモジュール骨格と一部関数を実装しているが、ファイル末尾が途中で途切れているため完全実装は未完と推測されます。今後のリリースで補完される可能性があります。
- 実装上の挙動（例: risk_manager のパラメータや ExecutionEngine の詳細、SystemMonitor の具体的チェック内容など）は、関連モジュール（execution/*、monitoring/*）の実装に依存します。本 CHANGELOG は提示されたコードから推測した主要変更点の要約です。
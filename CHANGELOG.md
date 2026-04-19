CHANGELOG
=========

すべての注目すべき変更は Keep a Changelog の形式に従って記載しています。

[0.1.0] - 2026-04-19
--------------------

初回リリース。KabuSys 自動売買フレームワークのコアユーティリティ、実行/監視スクリプト、ポートフォリオ構築ロジック、設定管理ツール、および検証/レポート生成ツールを含む初期実装を追加しました。

### Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を基準）。
  - .env ファイルの読み込み機能（.env, .env.local の順、OS 環境変数保護付き）を実装。自動ロードを環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - Settings クラスを導入し、環境変数を型付きプロパティで取得・検証（KABUSYS_ENV, LOG_LEVEL, 各種 DB パス、API トークン等）。
  - 環境変数パースロジックを実装（クォート/エスケープ/コメント対応）。

- 実行 & 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db）を使用、Mock ブローカーが利用され本番 DB と分離。
    - プロセス優先度を高く設定して実行（set_process_priority）。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル管理を組み込み、デーモン実行のためのスレッド管理を実装。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てロジックを追加。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を利用して監視テーブルを初期化。
    - 停止フラグ検出・例外ハンドリングを行い安全にループを終了。

- 設定ツール & 検証
  - config_setup.py: 対話式の .env 作成/更新ウィザードを実装。
    - 必要項目（J-Quants トークン、kabu API パスワード等）や選択肢をガイドして .env を生成。
    - 既存の .env 読み込み・マスク表示・保存確認をサポート。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の未設定検出、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML がある場合）。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - コンソール（stdout）出力と TimedRotatingFileHandler による日次ローテーション（30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / 引数で挙動を制御、既存ハンドラを適切に flush/close して再設定。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度（Windows/Linux/Mac 対応）と CPU affinity 設定を追加。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選定（signal_rank によるタイブレーク）を実装。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックに基づき候補を除外するロジックを実装（"unknown" セクターは無制限扱い）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数決定ロジックを実装。
    - 単元株丸め（lot_size）・1銘柄上限・aggregate cap（利用可能現金に応じたスケールダウン）・コストバッファを考慮。
    - risk_based: 損切り幅と許容リスク率からベース株数を算出。

- データ & レポート
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/max/P95）等を集計。
    - 基準値（稼働率 99%、成功率 90% 等）に基づき PASS/FAIL 判定を出力。
    - --from/--to/--db オプションで期間・DB を指定可能。
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（モメンタム等の定義・定数）。（実装途中のファイルあり）

### Changed
- N/A（初回リリースのため変更履歴はありません）。

### Fixed
- 環境変数パースの堅牢化: .env のクォート、バックスラッシュエスケープ、インラインコメントの扱い、export プレフィックス対応を実装。
- init_monitoring_db の呼び出しを冪等にして、監視テーブルが存在しない場合の初期化を安全に実行。

### Deprecated
- N/A

### Security
- N/A

Notes / 備考
- 環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development / paper_trading / live）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - DUCKDB_PATH（分析用 DB、デフォルト: data/kabusys.duckdb）
  - LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE 等

- 主要 CLI
  - 環境ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視ループ起動: python -m kabusys.run_monitoring
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

既知の制限 / 今後の改善案
- research/factor_research.py はファクター計算ロジック（SQL/集計）の実装が途中の箇所があります。実運用前に完全実装・テストが必要です。
- position_sizing の lot_size は現状グローバル固定（将来的には銘柄マスタから取得する拡張を検討）。
- apply_sector_cap の price 欠損時のフォールバック（前日終値等）実装が TODO に記載済み。
- 一部ファイルは外部ライブラリ（psutil、duckdb、PyYAML）が必要です。必要ライブラリを環境に準備してください。

過去バージョン
- なし（初回リリース）
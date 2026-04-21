# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠します。  
このファイルはコードベースの現状から推測して作成した変更履歴です（自動生成・推定を含む）。

## [Unreleased]

### Added
- （なし）

### Changed
- （なし）

### Fixed
- （なし）

---

## [0.1.0] - 2026-04-21

初回リリース（コードベースの現状に基づくまとめ）。

### Added
- 全体
  - プロジェクト初期版を公開。自動売買システム「KabuSys」のコア機能群を実装。
  - バージョン情報を `__version__ = "0.1.0"` として定義（`src/kabusys/__init__.py`）。

- 設定管理
  - 環境変数 / .env 自動ロード機能を実装（`.env`, `.env.local` をプロジェクトルートから読み込む）。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索する（`src/kabusys/config.py`）。
  - .env ファイルパースはクォート処理、`export KEY=val` 形式、インラインコメントの扱いなどを考慮した堅牢な実装を提供（`_parse_env_line`）。
  - 必須環境変数チェックユーティリティ `_require` および `Settings` クラスで環境変数をプロパティ経由で取得可能（DBパス・APIトークン等）。
  - Paper Trading 向けの `paper_sqlite_path`、`paper_fill_mode` 等の設定を追加（ペーパートレードの分離をサポート）。

- 設定ユーティリティ / CLI
  - 対話式 .env 設定ウィザード `config_setup` を追加。`.env` の新規作成／更新を支援し、機密項目はマスク表示（`python -m kabusys.config_setup`）。
  - 設定検証 CLI `validate_config` を追加。必須環境変数、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML あれば）などを検出。`--strict` オプションで警告を失敗扱いにできる（`python -m kabusys.validate_config`）。

- ロギング / プロセス管理
  - 統一的なロギング設定ユーティリティ `setup_logging` を追加。コンソール (stdout) と日次ローテーションファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定、ログディレクトリ作成のフォールバック処理を含む（`src/kabusys/utils/logging_setup.py`）。
  - プロセス優先度設定ユーティリティ `set_process_priority`、および CPU affinity を設定する `set_cpu_affinity` を追加。Windows / POSIX の差分を吸収し、権限不足等は警告でスキップ（`src/kabusys/utils/process_priority.py`）。

- 実行コンポーネント
  - ExecutionEngine 起動スクリプト `run_execution.py` を追加。Paper Trading 時は専用 SQLite（`data/paper_trading.db`）を使用し、本番 DB と分離。エンジンのスレッド駆動、停止フラグ検知、PID ファイルパス管理を実装。
  - SystemMonitor 起動スクリプト `run_monitoring.py` を追加。環境に依らず本番用 sqlite_path を監視 DB として使用し、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグでループ終了、例外ハンドリング・ログ出力を実装。

- データベース / 分析
  - DuckDB との連携を導入（`Settings.duckdb_path`）。Execution / Monitoring 両コンポーネントで DuckDB コネクションを確立する設計。

- 発注・実行サブシステム（骨格）
  - ブローカーファクトリ、OrderManager、OrderRepository、Reconciler、RiskManager、ExecutionEngine 等の組み立てを `run_execution.py` で行う（依存コンポーネントの初期化・連携フローを実装）。
  - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, max_drawdown=0.20 など）を明示。

- ポートフォリオ構築（純粋関数群）
  - 候補選定と重み生成（`select_candidates`, `calc_equal_weights`, `calc_score_weights`）を実装（`src/kabusys/portfolio/portfolio_builder.py`）。
    - スコア降順でソート、同点は signal_rank でブレーク。
    - スコア合計が 0 の場合は等分配にフォールバックして警告を出力。
  - セクター集中制限とレジーム乗数（`apply_sector_cap`, `calc_regime_multiplier`）を実装（`src/kabusys/portfolio/risk_adjustment.py`）。
    - 既存保有を基にセクター別エクスポージャを計算し、上限超過セクターの新規候補をブロック。unknown セクターは免除。
    - market regime に応じた乗数（bull=1.0, neutral=0.7, bear=0.3）を提供。未知のレジームは 1.0 でフォールバック。
  - 株数決定ロジック（`calc_position_sizes`）を実装（`src/kabusys/portfolio/position_sizing.py`）。
    - allocation_method による振る舞い（risk_based, equal, score）。
    - lot_size（単元）で丸め、1銘柄上限・総投下上限を考慮したスケーリング、コストバッファ考慮、残差配分ロジックを実装。

- ツール
  - Paper Trading 検証レポート生成スクリプト `tools/paper_verification_report.py` を追加。Paper Trading 用 SQLite から稼働率、注文成功率、送信率、P95 レイテンシ等を集計・判定し PASS/FAIL を出力。しきい値はソース内定義（稼働率 99% など）。

### Changed
- （該当なし — 初回リリースのため過去からの変更なし）

### Fixed
- （該当なし — 初回リリースのため過去からの修正なし）

### Security
- 機密値（API トークン・パスワード）は `.env` にて管理し、ウィザードや表示時はマスクする実装を追加（`config_setup`）。ただし `.env` を Git にコミットしないことを README / .env テンプレートで明示。

### Notes / Implementation details（実装上の重要点）
- 設定ファイル・YAML の検証は PyYAML がインストールされている場合のみ実行し、未インストール時は警告を出してスキップする（`validate_config`）。
- `run_monitoring` は監視 DB に対して init（冪等）を行う `init_monitoring_db` を呼び出す想定。
- `run_execution` は KABUSYS_ENV=paper_trading 時に MockBrokerClient を使う設計コメントがあり、ペーパートレード DB と完全分離する方針。
- ロギングはデフォルトで `logs/` ディレクトリに日次ローテーションログを出力。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで稼働するフォールバックがある。
- プロセス優先度 / CPU affinity の設定は権限不足や未対応 OS の場合は警告を出してスキップする安全設計。

---

この CHANGELOG は現在のソースコード構成から機能・仕様を推測して作成したものであり、実際のリリースノートとして利用する場合はプロジェクトの変更履歴・コミットログと合わせて確認・補正してください。
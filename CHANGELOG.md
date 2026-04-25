# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
（この CHANGELOG は提示されたコードベースの内容から推測して作成しています）

## [Unreleased]

### Added
- なし（初回リリース相当の状態のため、差分は v0.1.0 にて記載）

---

## [0.1.0] - 2026-04-25

初回公開リリース。日本株自動売買システム「KabuSys」の基盤的なモジュール群と CLI ツールを追加。

### Added
- 全体
  - パッケージの初期バージョンを `__version__ = "0.1.0"` として追加。
  - プロジェクトルート自動検出（.git / pyproject.toml による）を実装し、.env 自動読み込みをサポート。
  - .env の自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。

- 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数から各種設定値を取得するプロパティ群を提供（J-Quants / kabuステーション / DB パス / ログ等）。
  - `.env` と `.env.local` の読み込みロジックを実装（OS 環境変数を保護する保護リスト対応）。
  - `.env` パース機能を強化（export プレフィックス対応、クォート文字列のエスケープ処理、インラインコメント処理）。

- CLI / ユーティリティ
  - 環境設定ウィザード: `kabusys.config_setup`（`python -m kabusys.config_setup`）を追加。対話式に .env を作成・更新する機能。
  - 設定検証ツール: `kabusys.validate_config`（`python -m kabusys.validate_config`）を追加。必須環境変数や config/*.yaml 等の検証、`--strict` オプションで警告も失敗扱いにできる。
  - ログ設定ユーティリティ: `kabusys.utils.logging_setup.setup_logging` を追加。コンソール(stdout) と日次ローテートファイル出力を統一的に設定。
  - プロセス優先度ユーティリティ: `kabusys.utils.process_priority` を追加。Windows/Linux/macOS に対する優先度設定（`set_process_priority`）と CPU affinity 設定（`set_cpu_affinity`）を提供。psutil の権限エラー等は安全にスキップしてログ出力。

- ランナー / デーモン
  - 監視ループ起動スクリプト: `kabusys.run_monitoring` を追加。
    - SystemMonitor を使ったポーリングループを実装。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` でオーバーライド可能（デフォルト 60 秒）。
    - 監視用 SQLite DB は KABUSYS_ENV にかかわらずプロダクション用 `sqlite_path` を使用（意図的な分離設計）。
    - 停止フラグ（data/stop_requested.flag）検知により安全にループを終了。
    - 起動時にプロセス優先度を "high" に設定。
  - 実行エンジン起動スクリプト: `kabusys.run_execution` を追加。
    - `Settings` に基づき Paper Trading 時は専用 SQLite（`paper_sqlite_path`、デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（Paper 環境では MockBrokerClient を生成する想定）。
    - ExecutionEngine をスレッドで起動し、停止フラグ（data/stop_requested.flag）で安全停止。PID ファイルを利用（`data/execution.pid`）。
    - 実行前に監視テーブルの初期化（`init_monitoring_db`）を行い整合性を担保。
    - RiskManager / Reconciler / OrderManager 等の組み立てとデフォルト RiskConfig を追加（例: max_position_pct=0.20 等）。初期ポートフォリオ値は broker.get_available_cash() から取得。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - `select_candidates`（スコア降順で候補選定、同点は signal_rank でタイブレーク）
    - `calc_equal_weights`（等金額配分）
    - `calc_score_weights`（スコア加重、全スコアが 0 の場合は等金額にフォールバック）
  - `kabusys.portfolio.risk_adjustment`
    - `apply_sector_cap`（セクター集中上限適用。既存保有時価を基に候補を除外）
    - `calc_regime_multiplier`（市場レジームに応じた投入資金乗数。bull/neutral/bear のマッピング、未知レジームは 1.0 にフォールバック）
  - `kabusys.portfolio.position_sizing`
    - `calc_position_sizes`（allocation_method: "risk_based" / "equal" / "score" をサポート）
    - 単元株（lot_size）で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリングを実装
    - リスクベースではリスク許容率（risk_pct）と損切り率（stop_loss_pct）を利用して株数算出

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`、`PAPER_TRADING_SQLITE_PATH` で上書き可）から各種指標（稼働率 / 注文成立率 / 送信率 / レイテンシ）を集計して標準出力でレポートを生成。
    - P95 レイテンシ計算、各種閾値（稼働率 99% / 成立率 90% / 送信率 95% / P95 <= 200ms）に基づく PASS/FAIL 判定を実装。
    - 対象期間は `--from` / `--to` オプションで指定可能。

- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db`（呼び出し箇所あり）により監視テーブルを冪等に初期化する仕組みを統合（run_monitoring / run_execution から利用）。

### Changed
- ログ周りの方針
  - StreamHandler を stderr ではなく stdout に出力するように変更（cron / スケジューラ実行時のリダイレクト運用を考慮）。
  - 既存ハンドラがある場合は一度 flush/close してから再設定し、二重設定を防止。

- .env パーサーの堅牢化
  - export プレフィックス対応、クォート内エスケープ、インラインコメントの取扱等を行い現実的な .env を安全に扱えるよう改善。

### Fixed
- 環境値の妥当性チェックと誤設定対応
  - `Settings.paper_fill_mode` において許容値（instant, partial, never, reject）のバリデーションを追加し、不正な値は ValueError で明示。
  - `Settings.env` と `Settings.log_level` の値検証を追加して、無効な値時に明示的なエラーを発生させるようにした。

### Documentation / UX
- CLI ヘルプや docstring を充実化。各モジュールに利用方法と設計意図を明示。
- config_setup のウィザードにおいてシークレットはマスク表示、確認の上で .env を書き込むワークフローを提供。
- validate_config で config/*.yaml の有無確認と PyYAML 未インストール時の挙動（スキップして警告）を扱う。

### Security
- .env に関する注意書きを追加（.env を絶対にリポジトリにコミットしない旨を config_setup の出力に記載）。

### Known limitations / Notes
- research/factor_research モジュールはモメンタムなどのファクター計算設計を含むが、ファイル末尾が途中で切れているため完全実装は要確認（DuckDB 接続を想定した設計）。
- 一部の機能は外部モジュール（psutil / PyYAML / duckdb）に依存しており、環境にない場合は警告や機能制限が発生する。
- run_monitoring は監視用 DB にプロダクション sqlite_path を使うため、paper_trading と完全に分離したい運用では注意が必要。

---

今後の予定（推測）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity 等の出力）
- 戦略（strategy）やデータ取得（data）モジュールの追加・連携
- 単体テスト・統合テストの追加、CI 設定
- ドキュメント（運用手順・デプロイ手順・設計ドキュメント）の整備

---

参考: 主な環境変数・デフォルトパス（本リリースの実装から抜粋）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — paper_trading 用の約定モード（instant | partial | never | reject）
# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 全体
  - 初回リリース。自動売買システム KabuSys の基本モジュール群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定・環境
  - Settings クラスを実装し、環境変数経由で各種設定を取得する機能を追加。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - `PAPER_FILL_MODE`、`PAPER_TRADING_SQLITE_PATH`、監視閾値（CPU/MEM/DISK）など多数のプロパティを追加。
  - 環境変数パーサー（_parse_env_line）を強化：`export ` プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの処理に対応。

- CLI / ユーティリティ
  - 環境設定ウィザード `kabusys.config_setup` を追加（対話式で .env を作成/更新、シークレットはマスク表示）。
  - 設定検証 CLI `kabusys.validate_config` を追加（必須環境変数チェック、config/*.yaml の存在と YAML パース検証、`--strict` オプションをサポート）。
  - ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加：
    - コンソール (stdout) と日次ローテーション（TimedRotatingFileHandler、デフォルト30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装。
  - プロセス優先度ユーティリティ `kabusys.utils.process_priority` を追加：
    - Windows / POSIX の差分を吸収して優先度(nice/HIGH_PRIORITY_CLASS) を設定。
    - CPU affinity を設定する `set_cpu_affinity` を追加（利用可能コアの先頭 N コアに固定）。

- 実行スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード専用 DB を使用（`data/paper_trading.db` を既定）。
    - BrokerClientFactory により実運用 / モックブローカーを切り替え。
    - 停止制御: `data/stop_requested.flag` を監視し、検出時にエンジンを停止。
    - 実行中の PID を `data/execution.pid` に保存するための PID ファイル指定に対応。
  - 監視ポーリングスクリプト `run_monitoring.py` を追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。無効値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番の `sqlite_path` を使用して監視テーブルを初期化。
    - 停止フラグ `data/stop_requested.flag` を検知してループを終了。

- DB / 分析
  - DuckDB 用のパス設定 (`DUCKDB_PATH`) を追加し、各コンポーネントで DuckDB 接続を受け取る設計を採用。
  - 監視 DB 初期化ユーティリティ（`init_monitoring_db` の利用）を導入して冪等に監視テーブルを保証。

- ポートフォリオ構築（純関数群）
  - 銘柄選定・重み計算モジュール（kabusys.portfolio.portfolio_builder）を追加:
    - select_candidates: スコア降順 (+ タイブレークで signal_rank) による候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - リスク調整モジュール（kabusys.portfolio.risk_adjustment）を追加:
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に新規候補を除外（unknown セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - ポジションサイジング（kabusys.portfolio.position_sizing）を追加:
    - risk_based / equal / score の各配分方式に対応。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金に合わせたスケールダウン）を実装。
    - コストバッファ（手数料・スリッページ見積り）を加味する仕組みを実装。

- 研究（research）
  - ファクター計算モジュール開始（kabusys.research.factor_research）を追加（Momentum / Value / Volatility / Liquidity 設計、DuckDB 経由で計算）。（計算ロジック途中まで実装）

- ツール
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは `data/paper_trading.db`、`--from/--to/--db` オプションをサポート。
    - P95 計算、欠測データ時の安全処理、しきい値定義（稼働率 99% など）を実装。

### 変更 (Changed)
- 設定ロードの優先順位を明確化:
  - OS 環境変数 > .env.local > .env の順で読み込み。既存 OS 環境変数は保護され上書きされない。
- ログ出力:
  - StreamHandler を stdout に固定（cron 等のログ一元化を考慮）。
  - ファイル出力の失敗時にコンソールのみで継続するフォールトトレラントな実装。

### 修正 (Fixed)
- 環境変数パーサーの堅牢化:
  - クォート内でのバックスラッシュエスケープ処理、コメント判定の改善により `.env` ファイル中の特殊文字やコメントの取り扱いを修正。
- run_execution / run_monitoring のリソースクリーンアップを確実化:
  - finally ブロックで SQLite / DuckDB 接続を確実にクローズするように修正。

### 注意事項 (Notes)
- validate_config は PyYAML が未インストールの場合、YAML のパース検証をスキップして警告を出力します。
- run_monitoring は監視用 DB の初期化・記録に関して KABUSYS_ENV の影響を受けず常に `sqlite_path`（運用監視 DB）を使用します。監視データを隔離したい場合は適切に `SQLITE_PATH` を設定してください。
- `PAPER_FILL_MODE` は "instant" | "partial" | "never" | "reject" のいずれかを指定する必要があります。無効値は ValueError を送出します。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存して動作しない場合があり、その場合は警告を出してスキップします。

---

今後の予定（例）
- factor_research の完全実装（ファクター計算の SQL/アルゴリズム完成）
- strategy モジュール・発注ロジックの統合テスト
- 単体テスト・CI の追加、Docker イメージ化の整備

もし特定のファイル／機能に絞った差分説明や、Changelog の英訳が必要であればお知らせください。
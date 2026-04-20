# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-20

### 追加 (Added)
- 基本パッケージ初期実装を追加
  - パッケージバージョン: `kabusys` `0.1.0`
- 環境設定・読み込み
  - `.env` 自動読み込み機能（プロジェクトルートを `.git` または `pyproject.toml` から探索）。
  - `.env` ファイルのパース機能を実装（コメント、クォート、`export KEY=val` 形式に対応）。
  - OS環境変数を保護する仕組みを導入（`.env` 上書き時に保護）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
- 設定管理 API
  - `kabusys.config.Settings`：環境変数経由の設定取得を提供（必須項目チェック、デフォルト値、型変換）。
  - 主要な環境変数をサポート（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `KABUSYS_ENV`, `LOG_LEVEL`, `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`, `PAPER_FILL_MODE`, 等）。
- 対話式設定ウィザード
  - `kabusys.config_setup`：`.env` の初期作成 / 更新を対話式で行う CLI を追加。
  - 秘密値のマスク、デフォルト値提示、保存前確認機能を実装。
- 設定検証 CLI
  - `kabusys.validate_config`：起動前に環境変数や `config/*.yaml` を検証する CLI を追加。
  - `--strict` オプションで警告を FAIL 扱いにする機能を実装。
  - PyYAML がない場合は YAML 検証をスキップして警告。
  - 本番 (`KABUSYS_ENV=live`) 向けのガードチェック（LINE 設定や Kill Switch の注意喚起）を追加。
- 起動スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用 DB を使用し、Mock ブローカーを選択可能（本番 DB と完全分離）。
    - 停止フラグ（`data/stop_requested.flag`）および PID ファイル管理（`data/execution.pid`）をサポート。
    - 起動時にプロセス優先度を `high` に設定。
    - Execution 各コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）を組み立てて実行。
    - RiskManager のデフォルト構成（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, 等）を提供。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の `sqlite_path` を使用する仕様。
    - 停止フラグ検知時にループを安全に終了、例外をログに出力して次ポーリングへフォールバック。
- ロギング・プロセスユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：stdout ストリームハンドラと日次ローテーションするファイルハンドラ（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - ログレベルは引数 > 環境変数 `LOG_LEVEL` > デフォルトの順で解決。
  - `kabusys.utils.process_priority`：
    - Windows / POSIX（Linux/macOS 等）を吸収したプロセス優先度設定（`high`/`normal`/`low`）を提供。
    - CPU affinity 固定用 `set_cpu_affinity` を実装（first N cores に固定）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ポートフォリオ構築モジュール（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定 (`select_candidates`)：スコア降順、同点は `signal_rank` 昇順で上位 N を選択。
    - 重み計算：`calc_equal_weights`（等金額）、`calc_score_weights`（スコア加重。全スコアが 0 の場合は等金額にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中制限 (`apply_sector_cap`)：既存保有比率が閾値超過のセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - レジーム乗数 (`calc_regime_multiplier`)：`bull`/`neutral`/`bear` に対応（デフォルトフォールバックあり）。
  - `kabusys.portfolio.position_sizing`：
    - 発注株数計算 (`calc_position_sizes`)：`risk_based` / `equal` / `score` の配分方式をサポート。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、コストバッファ適用、残差の lot 単位での再配分ロジックを実装。
- リサーチ（ファクター計算）スケルトン
  - `kabusys.research.factor_research`：モメンタム等のファクター計算の骨組みを追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。
- ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレード検証レポート生成スクリプトを追加。
    - デフォルト DB: `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` で上書き可）。
    - 出力指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）など。
    - 判定基準（デフォルト閾値）: 稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms。
    - コマンドライン引数: `--from` / `--to` / `--db` をサポート。

### 変更 (Changed)
- 一貫したログ管理とプロセス優先度設定を全起動スクリプトで使用するように統一（`setup_logging`, `set_process_priority` を導入）。
- SQLite / DuckDB の利用方針を明確化
  - Execution は環境が `paper_trading` の場合に専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用。
  - Monitoring は環境にかかわらず監視用 SQLite（`SQLITE_PATH`）を使用。

### 修正 (Fixed)
- .env パースの堅牢化（クォート内のエスケープ処理、インラインコメントの適切な無視、`export` プレフィックス対応）。
- 日次ログローテーション設定での存在しないログディレクトリ作成失敗時のフォールバック処理を改善。

### 注意点 / 既知の制限 (Notes / Known issues)
- `.env` ファイルは機密情報を含むため、絶対に Git にコミットしないでください（config_setup にも注意書きを記載）。
- `set_process_priority` / `set_cpu_affinity` は権限や OS により失敗する可能性があります（失敗時は警告を出してスキップ）。
- `apply_sector_cap` / 位置決定アルゴリズムは銘柄価格が欠損（0.0）だとエクスポージャーを過小見積もりする恐れがあり、将来的にフォールバック価格の導入を検討する旨を TODO として残しています。
- `kabusys.research.factor_research` はファクター計算の主要ロジック（続き）が存在します（リポジトリ内の実装状況に依存）。

### マイグレーション / アップグレード情報 (Migration)
- 新規パッケージの初期リリースのため移行は不要です。既存環境へ導入する際は以下を確認してください:
  - 必須環境変数 `JQUANTS_REFRESH_TOKEN` および `KABU_API_PASSWORD` を設定すること。
  - `KABUSYS_ENV` を適切に設定（`development` / `paper_trading` / `live`）。
  - ログディレクトリ (`LOG_DIR`) や DB パス（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`）の親ディレクトリが存在するか確認。存在しない場合は警告が出ますが、起動時に自動作成される場合があります。
  - 本番運用時は `KILL_FLAG_CLEAR_ON_START` を `0` にすることを推奨（`1` にすると Kill Switch が自動クリアされます）。

---

今後の予定（例）
- ファクター計算・リサーチモジュールの拡充（ファクター正規化、パイプライン化）。
- Execution / Monitoring のユニットテスト強化と起動スクリプトの安全性向上。
- 銘柄ごとの lot_size 管理（マスタ追加）およびフォールバック価格ロジックの導入。
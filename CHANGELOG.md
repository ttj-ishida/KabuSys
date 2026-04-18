# CHANGELOG

すべての注目すべき変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-18

Added
- パッケージ初版を公開
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`

- 設定・環境変数管理
  - .env 自動読み込み機能を実装（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。OS 環境変数を保護して `.env.local` の上書き制御を行う。
  - .env パーサーは `export KEY=...`、クォート文字列、エスケープ、インラインコメント処理をサポート。
  - `kabusys.config.Settings` を提供し、主要な設定値（J-Quants トークン、kabu API パスワード、DB パス、ペーパートレード用設定、監視閾値、環境種別など）をプロパティとして安全に取得可能に。
  - `PAPER_FILL_MODE` のバリデーションと `PAPER_TRADING_SQLITE_PATH` の設定をサポート。

- 起動支援 CLI / ユーティリティ
  - `kabusys.config_setup`：対話式ウィザードで `.env` を作成・更新する CLI を追加。主要設定項目のプロンプト、シークレット値のマスク表示、保存確認を実装。
  - `kabusys.validate_config`：起動前の設定検証 CLI を追加。必須環境変数の確認、`KABUSYS_ENV`/`LOG_LEVEL` の検証、DB パスの親ディレクトリチェック、`config/*.yaml` の存在・パースチェック（PyYAML 未導入時はスキップ）。`--strict` オプションで警告を失敗扱いにできる。

- 実行 / 監視プロセス起動スクリプト
  - `run_execution.py`
    - `ExecutionEngine` 起動スクリプトを提供。起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と分離。
    - ブローカークライアント生成は `BrokerClientFactory.create(settings)` に集約。
    - `RiskManager` を初期化するためのデフォルト `RiskConfig` を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_* 等）。`initial_portfolio_value` はブローカーの利用可能現金から取得。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動・停止制御、デーモンスレッドで Engine を実行し安全にシャットダウンを行う。

  - `run_monitoring.py`
    - `SystemMonitor` のポーリングループ起動スクリプトを提供。起動時にプロセス優先度を "high" に設定。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、0 以下は警告してデフォルトにフォールバック）。
    - 監視用 DB 初期化（`init_monitoring_db`）を行い、Monitoring は環境にかかわらず本番用 `sqlite_path` を使用する設計。
    - 停止フラグの検出、`check_once()` 実行時の例外ログ記録、KeyboardInterrupt での正常終了処理を実装。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（date ローテーション・30 日保持）を設定するユーティリティを追加。
    - ログレベル/ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ有効化。
    - 既存ハンドラを安全に flush/close してから再設定することで多重設定を防止。

  - `kabusys.utils.process_priority`
    - Windows と POSIX(Linux/macOS/FreeBSD) を吸収するプロセス優先度設定 (`set_process_priority`) を追加。`psutil` を利用しプラットフォームごとの適切な優先度／nice 値を適用、失敗時は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を追加（アクセス権限や未サポート環境では警告を出してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank によるタイブレーク）。
    - 重み算出 `calc_equal_weights`, `calc_score_weights`（全スコアが 0 の場合は等金額配分にフォールバックして警告）。

  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 `apply_sector_cap`：既存保有のセクターエクスポージャーを計算して閾値超過セクターの新規候補を除外するロジックを実装（"unknown" セクターは除外対象外）。
    - レジーム乗数 `calc_regime_multiplier`：`bull`/`neutral`/`bear` に対応し、未知レジームは 1.0 でフォールバック（警告あり）。

  - `kabusys.portfolio.position_sizing`
    - 発注株数決定 `calc_position_sizes` を実装。サポートする配分方法:
      - `risk_based`: 許容リスク率（risk_pct）と stop_loss_pct に基づく計算。
      - `equal` / `score`: 重みを元に配分。
    - 単元株（lot_size）丸め、1 銘柄上限・アグリゲートキャップ（available_cash）に応じたスケーリング、cost_buffer による保守的なコスト見積り、スケールダウン時の残差処理（小数端数の優先配分）を実装。
    - 価格欠損時のログ出力や TODO コメントによる将来的な改善案を明示（フォールバック価格など）。

- リサーチ / ファクター計算（下地）
  - `kabusys.research.factor_research` にモメンタム／ボラティリティ等のファクター計算基盤を追加（DuckDB 接続を受け prices_daily / raw_financials テーブルを参照して計算）。
  - モメンタム計算のための定数（1M/3M/6M、MA200、ATR など）と P95 等の補助処理を導入。設計は外部 API 非依存、結果は (date, code) 単位の dict リストを返す想定。

- ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレード結果の検証レポートを生成する CLI を追加。
    - 指定期間の system_status / trade_logs / risk_logs を参照して、稼働率、注文成功率、送信率、P95 レイテンシ等を集計。
    - 基準値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）に基づいて PASS/FAIL 判定を行う。
    - DB パスはコマンドライン引数 `--db`、環境変数 `PAPER_TRADING_SQLITE_PATH`、デフォルト順で解決。

Notes
- デフォルトの DB/ログパス:
  - DuckDB: `data/kabusys.duckdb`
  - SQLite (監視用): `data/monitoring.db`
  - Paper Trading SQLite: `data/paper_trading.db`
  - ログディレクトリ: `logs/`（環境変数 `LOG_DIR` で上書き可能）
- 停止制御はプロジェクト内の `data/stop_requested.flag`（および実行用 PID ファイルパス）で行われる設計。
- 本リリースは初期実装のため、いくつかの箇所で将来的な改善（例: 価格フォールバック、銘柄ごとの lot_size 管理、より詳細なエラーハンドリングなど）を TODO コメントで残しています。

著記
- 主要な依存ライブラリ: psutil, duckdb, sqlite3（標準ライブラリ）、PyYAML（YAML 検証に任意）
- CLI 起動例:
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視起動: python -m kabusys.run_monitoring
  - ペーパートレード検証: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---
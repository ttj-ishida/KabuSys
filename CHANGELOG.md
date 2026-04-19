# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このリポジトリはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初期リリース。自動売買システム KabuSys のコア機能群を追加。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数から各種設定を取得する統一 API を提供（J-Quants / kabuAPI / DB パス / ログレベル / 環境フラグ等）。
  - 自動 `.env` ロード機能を実装（プロジェクトルートの検出は .git / pyproject.toml を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - `.env` のパース強化：
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの取り扱い。
  - 環境変数取得ヘルパー `_require` による必須値チェックとエラーメッセージ整備。
  - `paper_fill_mode` の有効値チェック（"instant" / "partial" / "never" / "reject"）。

- 設定ユーティリティ CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を生成/更新する CLI を追加。
    - 各種設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークンなど）を対話的に入力可。
    - シークレット値はマスク表示、既存値の再利用対応、保存前の確認プロンプトを実装。
    - `.env` ファイル生成時に注意書きを含め、Git へのコミットを避けるようコメントを出力。

  - `kabusys.validate_config`：起動前チェック用 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML が入っていれば）パース検証を実施。
    - `--strict` オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定（`kabusys.utils.process_priority.set_process_priority` を使用）。
    - `KABUSYS_ENV=paper_trading` の場合、paper 用の専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離（MockBroker を利用する設計を想定）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行、stop flag（`data/stop_requested.flag`）検出による停止制御、PID ファイルサポートを実装。
    - `RiskConfig` のデフォルトパラメータを設定（max_position_pct, max_utilization, rate_limit_per_sec 等）。

  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告のうえデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の `sqlite_path` を使用する設計（監視用テーブルの初期化も行う）。
    - stop flag（`data/stop_requested.flag`）検出でループ終了、KeyboardInterrupt による終了処理、DB（sqlite3/duckdb）コネクションのクローズを確実に行う。

- ログ / プロセスユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - ルートロガー設定を統一（コンソール出力は stdout、日次ローテートのファイルハンドラを追加、既存ハンドラを一旦クリアして二重設定を回避）。
    - `LOG_DIR` / 引数 `log_dir` によるログディレクトリ解決、作成失敗時はファイル出力をスキップして警告を出す。
    - デフォルトで 30 日保持の TimedRotatingFileHandler を利用。

  - `kabusys.utils.process_priority` を追加。
    - Windows（psutil の priority クラス）と POSIX（nice 値）を吸収して `set_process_priority(level)` を提供（"high"/"normal"/"low"）。
    - CPU 固定用 `set_cpu_affinity(cpu_count)` を提供（アクセス権限や未対応 OS は警告でスキップ）。
    - 権限不足や未実装機能に対する安全なフォールバックとログ出力を実装。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を返す（タイブレークに signal_rank を使用）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化による重み付け。全スコアが 0.0 の場合は等金額配分にフォールバック（警告ログ）。

  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: セクター集中上限（max_sector_pct）を既存保有から計算し、新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知のレジームは警告して 1.0 にフォールバック）。

  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") による発注株数計算、単元（lot_size）丸め、per-position 上限・aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケールダウン処理、残余分の配分アルゴリズムを実装。

  - `kabusys.portfolio.__init__` で主要関数をエクスポート。

- 分析 / リサーチ
  - `kabusys.research.factor_research`（ファクター計算モジュール）の骨格を追加。
    - Momentum / Value / Volatility / Liquidity の設計方針を記載し、DuckDB 接続経由で prices_daily / raw_financials を参照する方針を示す。
    - モメンタム計算（calc_momentum）の実装を開始（ファイル末尾で途中まで実装）。

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - paper_trading 用 SQLite（デフォルト `data/paper_trading.db`、`PAPER_TRADING_SQLITE_PATH` で上書き可）から各種指標（稼働率 / 注文成功率 / 送信率 / リスク却下数 / レイテンシ）を集計し、閾値に基づいて PASS/FAIL を判定する CLI。
    - P95 計算、P95 レイテンシ閾値 (200 ms)、稼働率閾値 (99%) などの定義と出力フォーマットを実装。
    - コマンドライン引数 `--from` / `--to` / `--db` をサポート。

- その他
  - 監視用 DB 初期化呼び出し `init_monitoring_db` が複数起動スクリプトから冪等に呼ばれるよう統一。
  - stop/kill フラグファイル（`data/stop_requested.flag` / `data/kill.flag`）を用いた外部制御設計。

### Changed
- （初版につき該当なし）

### Fixed
- （初版につき該当なし）

---

注記:
- 一部モジュール（例: ExecutionEngine / BrokerClientFactory / SystemMonitor 等）は本 CHANGELOG に示した起動フローや API で利用されるが、ここに含まれるコード群の外部に実装されている可能性があります。  
- `reasearch.factor_research` は実装途中の箇所があり、今後のリリースで完成・検証が予定されています。
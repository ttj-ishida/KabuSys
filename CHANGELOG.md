# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

[0.1.0] - 2026-04-18
--------------------

### Added
- 初回リリース (0.1.0)。
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。
  - パッケージ公開用の `__all__` を定義。

- 環境設定 / 設定読み込み
  - Settings クラスを導入し、環境変数からアプリ全体の設定を取得可能に（`kabusys.config`）。
  - 自動 `.env` 読み込み機能を実装（プロジェクトルート検出：`.git` または `pyproject.toml` を基準）。`.env` と `.env.local` の読み込み順を考慮し、OS 環境変数は保護される。
  - `.env` のパース強化：`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなどに対応。
  - 必須値チェック用の `_require()` を追加し、未設定時にわかりやすい例外を投げる。

- 設定関連 CLI
  - 対話式設定ウィザード `kabusys.config_setup` を追加（`.env` の初期作成・更新を支援）。デフォルト値、選択肢、シークレット入力のサポート、保存確認を実装。
  - 設定検証ツール `kabusys.validate_config` を追加。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、`config/*.yaml` の存在と YAML パース（PyYAML が存在する場合）を検査。`--strict` オプションで警告を FAIL 扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - `KABUSYS_ENV=paper_trading` 時は専用の paper trading SQLite を使用して本番 DB と分離（`PAPER_TRADING_SQLITE_PATH` 環境変数で上書き可能、デフォルト: `data/paper_trading.db`）。
    - Broker クライアントは `BrokerClientFactory.create(settings)` で生成（Paper 環境では MockBrokerClient 等が想定）。
    - `ExecutionEngine` 起動、スレッド管理、停止フラグ（`data/stop_requested.flag`）検出、PID ファイルサポートあり。
    - RiskManager の初期構成（デフォルト値）を設定し、初期現金はブローカーから取得する。
  - 監視モジュール起動スクリプト `run_monitoring.py` を追加。
    - `SystemMonitor` のポーリングループを実装。`MONITOR_POLL_INTERVAL` 環境変数で間隔上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番向けの `sqlite_path` を使用する（監視 DB の分離ポリシー）。
    - 停止フラグ検出、例外発生時のログ出力と継続動作、KeyboardInterrupt の取り扱いを実装。

- ログ・プロセスユーティリティ
  - 統一的なログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト `logs/`、`<app_name>.log`）をルートロガーに設定。
    - 既存ハンドラをクリアして再設定するため二重設定を防止。ログディレクトリ作成失敗時にはファイルハンドラをスキップして stdout のみで継続。
  - プロセス優先度 / CPU affinity ユーティリティ `kabusys.utils.process_priority` を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）双方に対応した `set_process_priority(level)`（`high|normal|low`）を実装。
    - `set_cpu_affinity(cpu_count)` によるコアピンニング機能を追加。
    - 権限不足や未対応機能は警告で安全にスキップする。

- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - `select_candidates(buy_signals, max_positions)`：スコア降順かつ tie-breaker に signal_rank を使用して候補選定。
    - `calc_equal_weights(candidates)`：等金額配分。
    - `calc_score_weights(candidates)`：スコア比率に基づく配分。全銘柄スコアが 0 の場合は等金額にフォールバックし警告。
  - `kabusys.portfolio.risk_adjustment`
    - `apply_sector_cap(...)`：同一セクターの既存保有比率が上限を超える場合に新規候補を除外（"unknown" セクターは上限適用外）。
    - `calc_regime_multiplier(regime)`：レジームに応じた投下資金乗数（`bull`/`neutral`/`bear`）を返す。未知レジームは 1.0 にフォールバックして警告。
  - `kabusys.portfolio.position_sizing`
    - `calc_position_sizes(...)`：allocation_method（`risk_based`/`equal`/`score`）に応じた発注株数計算を実装。
      - リスクベースの計算、1 銘柄上限（max_position_pct）、aggregate cap（available_cash によるスケールダウン）、単元株（lot_size）丸め、cost_buffer を加味した保守的見積り、残差配分ロジック等を含む。
  - これらは全て副作用のない純粋関数（DB 参照なし）として設計。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research` を追加（DuckDB 接続を受け prices_daily / raw_financials を参照してモメンタム等のファクターを計算する設計）。
    - モメンタム計算の入出力仕様（mom_1m / mom_3m / mom_6m / ma200_dev 等）を定義。大きな設計方針と計算ウィンドウの定数を含む。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading 用 SQLite から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計してレポート出力。
    - P95 計算ユーティリティ、日付フィルタ、閾値に基づく PASS/FAIL 判定、デフォルト DB パスは `data/paper_trading.db`。CLI フラグ `--from`/`--to`/`--db` をサポート。

- DB / 分析
  - 実行系・監視系で DuckDB を利用するための接続ポイントを追加（`duckdb.connect` を使用）。ログや分析用 DB として `DUCKDB_PATH` を設定可能。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数・ `.env` の取り扱いにおいて、シークレットはウィザードや書き出し時にマスクする等、誤コミット防止を意識した実装を追加。

Notes
- 重要な実行時動作
  - 監視プロセスはプロセス優先度を "high" に設定してから動作を開始します（`set_process_priority("high")`）。
  - `run_execution` は paper_trading の場合に本番 DB と完全分離された SQLite を使用することで、本番資産に影響を与えないよう設計されています。
  - `.env` 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途等）。

今後の予定（未実装/検討事項）
- stocks マスタに銘柄別の lot_size を持たせる等、position sizing のさらなる拡張。
- `apply_sector_cap` における価格欠損時のフォールバック処理（前日終値等）。
- factor_research の完全実装およびユニットテスト強化。
- `monitoring_db` や `SystemMonitor`、`ExecutionEngine` 等の詳細モジュールに対するドキュメント・テスト追加。
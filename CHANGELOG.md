# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
https://keepachangelog.com/ja/1.0.0/

なお、このリポジトリの初回リリースとしてバージョン 0.1.0 を記録しています。

## [Unreleased]

（未リリースの変更はここに記載してください）

## [0.1.0] - 2026-04-17

初回公開リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` に設定。

- 設定管理
  - `kabusys.config.Settings` クラスを実装。環境変数から各種設定（J-Quants / kabuAPI / DB パス /監視閾値 /動作環境 等）を取得するプロパティを提供。
  - 自動 .env ロード機能を実装（プロジェクトルートに基づき `.env`、`.env.local` を読み込む）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - `.env` のパースは export 構文、引用付き値、インラインコメント等に対応。

- 環境設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを追加。`.env` の初期作成・更新を支援。
  - `python -m kabusys.config_setup` で実行可能。多数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）に対応。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。環境変数や `config/*.yaml` の存在・簡易検証を実行。
  - `python -m kabusys.validate_config`（`--strict` で警告を FAIL 扱い）で使用可能。PyYAML がない場合は YAML 検証をスキップし警告を出す。

- 実行用ランナースクリプト
  - `kabusys.run_execution` を追加。ExecutionEngine 起動のためのセットアップ（プロセス優先度設定、DB 接続、ブローカ生成、OrderManager / RiskManager / Reconciler の組み立て）を行う。
    - KABUSYS_ENV が `paper_trading` の場合は専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - 起動時に `data/stop_requested.flag` を検知して起動を中止する仕組みを実装。
    - 実行中は停止フラグを監視し、検知時に Engine を停止してスレッド終了を待機する。
    - ExecutionEngine の構成例（RiskConfig のデフォルト値など）をコード内に定義。

  - `kabusys.run_monitoring` を追加。SystemMonitor のポーリングループ起動用スクリプトを提供。
    - デフォルトポーリング間隔は 60 秒。`MONITOR_POLL_INTERVAL` 環境変数で上書き可能。無効値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の `sqlite_path` を利用する仕様（監視 DB は本番追跡目的）。
    - 停止フラグ `data/stop_requested.flag` の検出でループ終了。

- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を呼び出して監視テーブルの存在を保証（冪等に初期化）。

- ブローカクライアント抽象化
  - `BrokerClientFactory.create(settings)` で環境に応じた BrokerClient を生成（paper_trading 用モック等を想定）。

- プロセス設定ユーティリティ
  - `kabusys.utils.process_priority` を追加。Windows / POSIX の違いを吸収してプロセス優先度（high/normal/low）の設定を行う `set_process_priority` を提供。
  - CPU affinity を設定する `set_cpu_affinity` 関数を追加（指定コア数に固定、対応できない環境では警告を出して無視）。

- ポートフォリオ構成（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 (select_candidates)
    - 等配分 (calc_equal_weights)
    - スコア重み配分 (calc_score_weights) — 全スコアが 0 の場合は等分へフォールバック（WARNING）
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限の適用 (apply_sector_cap)。既存保有額に基づき上限超過セクターをブロック（"unknown" セクターは無視）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバックしてログ警告）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数計算 calc_position_sizes を実装。`risk_based`、`equal`、`score` の allocation_method に対応。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウンと残差処理を実装。
    - cost_buffer により手数料・スリッページを保守的に見積もれる設計。

- リサーチ（ファクター計算）
  - `kabusys.research.factor_research` を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照して各種ファクターを算出。
    - Momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）
    - Volatility: ATR(20), 相対ATR, 20日平均売買代金、出来高比率 等（部分窓にも対応）
    - 内部でのスキャン範囲や窓長は定数化（例: MA200, ATR20 等）
    - SQL + Python で実装し、結果は (date, code) ベースの dict リストで返す設計。

- Paper Trading 検証レポートツール
  - `kabusys.tools.paper_verification_report` を追加。paper_trading の SQLite を読み取り、稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL 判定を出力する CLI。
    - 閾値はソース内で定義（稼働率 99% など）。
    - P95 計算、日付フィルタ（--from / --to）、DB パスの CLI 指定/環境変数に対応。
    - DB スキーマが不足する場合（テーブルがない等）でも例外を握りつぶして N/A 扱いでレポートを継続。

- ドキュメント的なコードコメント・使用例
  - 各モジュールに用途・設計方針・使用方法（例: python -m kabusys.tools.paper_verification_report）を記載。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Notes / Implementation details / 注意事項
- 監視用（monitoring）DB は環境に依らず `Settings.sqlite_path`（本番想定）を使用する点に注意。ペーパートレードの監視を分離したい場合は環境に応じた設定の見直しが必要。
- `PAPER_FILL_MODE`、`PAPER_TRADING_SQLITE_PATH` など Paper Trading 関連の設定を用意。`paper_trading` 環境では実際の発注を行わない設計。
- `.env` の自動ロードはプロジェクトルート検出に基づくため、パッケージ配布後もカレントディレクトリに依存せず動作するよう配慮。
- `process_priority` / `set_cpu_affinity` は権限不足や未対応プラットフォームで失敗する可能性があるため、失敗時は警告を出して処理を継続する設計。
- いくつかの TODO や将来的な拡張ポイント（銘柄ごとの lot_size マスタ追加、価格フォールバックなど）をコード内コメントで記載。

---

署名: KabuSys コードベース（初期実装）
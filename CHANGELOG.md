# Changelog

すべての注目すべき変更を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-19

### Added
- パッケージ初期リリース（バージョン情報: `kabusys.__version__ = "0.1.0"`）。
- 環境設定 / 設定管理
  - robust な .env 自動読み込み機構を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - .env 解析器を追加し、`export KEY=val`、シングル/ダブルクォート、インラインコメント、エスケープに対応。
  - Settings クラスを追加し、環境変数からアプリ設定を安全に取得:
    - J-Quants / kabu API / LINE トークン等の取得メソッド
    - DB パス（`DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH`）
    - 運用環境判定 (`KABUSYS_ENV`: development / paper_trading / live) と `is_live` / `is_paper` / `is_dev`
    - `PAPER_FILL_MODE`（"instant" | "partial" | "never" | "reject"）のバリデーション
    - 各種監視閾値や PID / kill flag パスの取得
  - `settings` の単一インスタンスを提供。

- 環境設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装。`.env` の初期作成・更新を支援。
  - シークレット項目はマスク表示、選択肢・デフォルト値の提示、既存 .env の読み込み・再利用に対応。
  - `.env` のテンプレート書き込み機能を提供（Git にコミットしない旨のヘッダを付与）。

- 設定検証 CLI
  - `kabusys.validate_config` を実装。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パースを検査。
  - `--strict` オプションで警告を失敗扱いにできる。PyYAML 未インストール時は YAML 検証をスキップして警告出力。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。全起動スクリプトから共通で使用する設定を提供:
    - StreamHandler を stdout に設定（cron 等で stdout/stderr を統一しやすくするため）
    - 日次ローテーションの TimedRotatingFileHandler（デフォルト `logs/`、30 日分保持）
    - 既存ハンドラの二重設定を防止するためハンドラ再設定ロジック
    - `LOG_DIR` / `LOG_LEVEL` 環境変数との連携、ファイルハンドラ作成失敗時のフォールバック動作
- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を追加。Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
  - `set_cpu_affinity` を提供し、最初の N コアへの固定をサポート（アクセス権限や未対応 OS は安全に無視）。

- 実行・監視エントリポイント
  - `kabusys.run_execution`:
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は paper 用の専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（テスト用 Mock を含む想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - デフォルト RiskConfig を提供（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル管理。
  - `kabusys.run_monitoring`:
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告のうえデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB の一貫性重視）。
    - 停止フラグによるループ終了、例外時のログ出力、DB 接続クローズ処理を実装。

- Portfolio コンポーネント（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - select_candidates (スコア降順、同点時は signal_rank でタイブレーク)
    - calc_equal_weights
    - calc_score_weights（全スコアが 0 の場合は等配分にフォールバックし WARNING を出力）
  - `kabusys.portfolio.risk_adjustment`:
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックし超過セクターの新規候補を除外。売却予定銘柄 (sell_codes) をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返却（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは 1.0 にフォールバックし警告ログ。
  - `kabusys.portfolio.position_sizing`:
    - calc_position_sizes: allocation_method (`"risk_based"` / `"equal"` / `"score"`) に応じた株数算出、単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash） のスケーリングロジック、cost_buffer を加味した保守的見積り、残差配分アルゴリズムを実装。
    - 設計により将来的に銘柄別 lot_size 等への拡張を想定（TODO コメントあり）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / `--db`）からメトリクスを集計しレポートを出力:
    - 指標: 稼働率 (uptime_pct), 注文成功率 (fill_rate), 送信率 (send_rate), P95 レイテンシ 等
    - デフォルト閾値を定義: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from / --to）に対応

- Research（着手）
  - `kabusys.research.factor_research` を追加（モメンタム等ファクター計算の骨組み）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。モメンタム期間や ATR/VOLUME 日数等の定数を定義。※ 実装は継続中（ファイル末尾で未完の箇所あり）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Known issues / Notes
- validate_config の YAML 検証は PyYAML がインストールされていない場合にスキップされ、警告が出ます（必須ライブラリチェックは行わず、フォールバック処理を採用）。
- `process_priority` と `set_cpu_affinity` は psutil に依存して動作します。権限不足や未対応プラットフォームでは警告ログを出力して安全にスキップします。
- position_sizing / apply_sector_cap の一部ロジックは価格データ欠損時に保守的に動作しますが、将来的に前日終値や取得原価等のフォールバック価格導入が望まれます（コード内に TODO コメントあり）。
- research.factor_research はまだ実装が途中の箇所があります（今後のリリースで完成予定）。

### Migration notes
- 監視プロセスは常に本番の SQLite パス（`SQLITE_PATH`）を参照します。テスト目的で監視を分離したい場合は環境変数を適切に設定してください。
- Paper Trading 実行時は `KABUSYS_ENV=paper_trading` を設定し、`PAPER_TRADING_SQLITE_PATH` を指定すると本番データベースと分離できます。

---

今後の予定: factor_research の完成、ExecutionEngine / Broker クライアントのインターフェース拡充、単体テスト・E2E テストの追加、ドキュメント整備（API レベルの使用例・設定項目リファレンス）。
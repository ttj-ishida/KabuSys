# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
重大度: Added / Changed / Fixed / Removed / Deprecated / Security

## [Unreleased]

### Added
- ドキュメント化およびユーティリティ類の整備
  - プロジェクト全体の設定管理クラス `kabusys.config.Settings` を追加。環境変数から設定を取得し、バリデーション（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行う。
  - 自動 .env ロード機能を追加（プロジェクトルートが検出される場合、`.env` → `.env.local` の順に読み込み）。自動ロードを無効にするための `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入。
  - `.env` のパース機能を強化（`export KEY=val`、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱いをサポート）。
  - `kabusys.config_setup` に対話式ウィザードを追加し、`.env` の初期作成・更新を支援。
  - `kabusys.validate_config` CLI を追加し、起動前に必須環境変数や設定ファイル（`config/*.yaml`）の存在・簡易パース検証を実行可能にした。
- 実行・監視用スクリプト
  - `run_execution.py` を追加。ExecutionEngine の起動スクリプトを提供。`KABUSYS_ENV=paper_trading` 時は paper_trading 用専用 SQLite（`data/paper_trading.db`）を使用して本番 DB と分離する。
  - `run_monitoring.py` を追加。SystemMonitor のポーリングループ起動スクリプトを提供。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視 DB は環境にかかわらず本番の sqlite_path を使用する旨を明記。
  - 停止制御用にプロジェクト内の `data/stop_requested.flag`（および実行用の `execution.pid`）を参照する仕組みを導入。
- 実行時ユーティリティ
  - 統一ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。コンソール（stdout）出力と日次ローテーションするファイルハンドラを設定。ログディレクトリ作成失敗時のフォールバック処理を実装。
  - プロセス優先度/CPU affinity 設定ユーティリティ `kabusys.utils.process_priority` を追加。Windows と POSIX (Linux/Mac/FreeBSD) に対応する優先度設定と CPU ピン留めを提供。権限不足時は警告を出してスキップ。
- ポートフォリオ構築関連（純粋関数として実装）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`（スコア降順、同点時の tie-break）を追加。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights` を追加（全スコアが 0 の場合は等金額にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 `apply_sector_cap` を実装。既存保有のセクター比率が閾値を超える場合に候補を除外する。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を追加（bull/neutral/bear をマップ、未知のレジームはフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 注文株数算出 `calc_position_sizes` を実装。`risk_based`（リスクベース）、`equal`、`score` をサポート。単元株（lot_size）で丸め、ポジション上限・利用可能現金に応じたスケールダウン（aggregate cap）を行う。手数料/スリッページ見積り（cost_buffer）を考慮。
- 研究・ファクター計算
  - `kabusys.research.factor_research` の骨組みを追加（Momentum/Value/Volatility/Liquidity に関する設計方針と定数を定義）。DuckDB を用いた prices_daily / raw_financials の解析を想定した実装方針を記載（モメンタム計算関数のインターフェースが含まれるが、一部実装は継続中）。
- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading 用の SQLite DB（`PAPER_TRADING_SQLITE_PATH`）から稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計し、PASS/FAIL 判定付きのレポートを生成。
  - レポートの判定基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を定義。
- パッケージメタ
  - パッケージのバージョンを `__version__ = "0.1.0"` として設定。

### Changed
- ログ出力: StreamHandler を stdout に固定（cron/Task Scheduler などからのリダイレクト運用を考慮）。
- `.env` のロード順と振る舞いを明文化（OS 環境変数を保護して `.env.local` で上書き可能）。

### Fixed
- 環境変数パースの不整合対応（引用符・エスケープ・コメントの扱いを改善し、想定外の .env 表記による誤読を軽減）。

---

## [0.1.0] - 2026-04-19

### Added
- 初回リリース（上記 Unreleased の内容を含む）。
  - 実行・監視スクリプト、設定管理、設定ウィザード、設定検証ツール、ログ・プロセス優先度ユーティリティ、ポートフォリオ構築モジュール、position sizing、risk adjustment、research 基盤、paper trading レポートツール 等を公開。

### Known issues / Notes
- research/factor_research の一部関数は未完（設計と定数は定義済みで、実装継続中）。
- position_sizing の価格欠損（price が 0.0 や未設定）の扱いに関しては TODO コメントあり（将来的に前日終値や取得原価でのフォールバックを検討）。
- `set_cpu_affinity` / `set_process_priority` は権限や OS に依存し、失敗した場合は警告を出してスキップする設計です。
- `.env` はセキュリティ上 Git 管理下に置かないことを README 等で強く推奨してください（config_setup でも注意文を出力）。

---

タグ:
- [Unreleased] と [0.1.0] の差分は、今後の機能追加やバグ修正で更新してください。
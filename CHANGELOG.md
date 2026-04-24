# Changelog

すべての注記は Keep a Changelog の形式に従っています。  
この CHANGELOG は、提示されたコードベースから推測して作成したものであり、実際のコミット履歴と厳密には一致しない可能性があります。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-24

初回公開リリース。以下の主要コンポーネントと機能を実装／追加しました。

### Added

- 実行エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV により paper_trading（ペーパートレード）用 DB と MockBroker を使用するモードをサポート（本番 DB と完全分離）。
    - プロセス優先度を "high" に設定する処理を起動時に実行。
    - stop flag（data/stop_requested.flag）を監視し安全に停止可能。
    - execution PID を data/execution.pid に記録し制御可能。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop flag による停止検知および KeyboardInterrupt ハンドリングを実装。

- 設定管理・検証・ウィザード
  - config.py
    - Settings クラスを実装し、環境変数から各種設定（API トークン、DB パス、モード、しきい値など）を取得。
    - .env の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。.env / .env.local の読み込み順を考慮。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パースは export プレフィックス、単一/二重クォート、エスケープ、インラインコメントの扱いに対応。
    - PAPER_FILL_MODE（ペーパートレードの約定モード）、paper_sqlite_path 等のプロパティを提供。
    - ログレベル、KABUSYS_ENV（development/paper_trading/live） の検証を実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース（PyYAML があれば内容も検証）などを実行。
    - --strict オプションで警告を失敗扱いにできる。

  - config_setup.py
    - .env を対話式に生成／更新するウィザードを実装。
    - J-Quants / kabu API / DB パス / LINE 通知設定等の入力項目を用意。
    - 既存 .env の読み込み・参照、シークレット項目のマスク表示、保存確認をサポート。

- ロギング／プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / app_name を利用した柔軟な設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。

  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応プラットフォームでは安全にスキップする挙動。

- ポートフォリオ構築・ポジション決定ロジック（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル候補選定（score によるソート）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全銘柄スコアが 0 の場合は等金額にフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - セクター集中の上限適用 apply_sector_cap（当日売却予定銘柄の除外に対応）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear マッピング。未知時はフォールバック警告）。

  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に応じた発注株数計算 calc_position_sizes を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer（手数料／スリッページ見積り）などを考慮した安全な配分ロジックを実装。
    - price 欠損時のスキップやログ出力、残余キャッシュを用いた端数配分の再配分ロジックを実装。

- 分析 / ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計。
    - PASS/FAIL 判定基準（稼働率 >= 99%, 成功率 >= 90%, 送信率 >= 95%, P95 レイテンシ <= 200ms）を定義し判定結果を表示。
    - --from / --to / --db オプションをサポート。

- 研究用モジュール（骨組み）
  - research/factor_research.py
    - ファクター計算用の基礎を追加（モメンタム／MA200／ATR／出来高等の仕様・定数を定義）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。関数インターフェースと仕様コメントを整備（実装継続を想定）。

- パッケージ情報
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed

- （初回リリースのため特別な変更履歴は無し）

### Fixed

- （初回リリースのため特別な修正履歴は無し）

### Notes / Operational details

- 環境変数およびデフォルトパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db（monitoring は本番 DB を使用）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード専用）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレード約定モード（instant|partial|never|reject、デフォルト instant）
  - KILL_FLAG_CLEAR_ON_START: 本番での自動クリアは危険（validate_config に警告ロジックあり）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

- ロギング
  - コンソール出力は stdout を利用（cron / scheduler での扱いを想定）
  - 日次ローテーションで最大 30 日保持

- 安全策
  - process priority / cpu affinity 設定は権限不足や未対応 OS では警告を出してスキップ
  - run_execution / run_monitoring は data/stop_requested.flag により安全に停止可能

### Known limitations / TODOs（コードからの推測）

- research/factor_research.py はファイル末尾が途中で終わっている（実装継続が必要）。
- position_sizing の lot_size は全銘柄共通の想定。将来的に銘柄別 lot_map への拡張を検討。
- apply_sector_cap の price 欠損時（0.0）による露出過小見積りに関する TODO コメントあり：前日終値や取得原価でのフォールバック検討が必要。
- 一部の外部パッケージ（PyYAML, psutil, duckdb 等）に依存。インストール環境の整備が必要。

---

この CHANGELOG はコードの内容とコメントから推測して作成しています。必要であれば実際のコミット／リリース履歴に基づく調整や日付修正を行います。
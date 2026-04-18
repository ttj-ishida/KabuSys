# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
慣例: 破壊的変更 (Breaking Changes)、追加 (Added)、変更 (Changed)、修正 (Fixed)、既知の問題 (Known Issues) をセクションに分けています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18
初回リリース。日本株自動売買システムのコア機能群と運用ユーティリティを提供します。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する動作を実装。
    - BrokerClientFactory を通じてブローカークライアントを生成。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による停止検出、data/execution.pid に PID を記録して運用可能。
  - run_monitoring.py
    - SystemMonitor をポーリングで定期実行するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - data/stop_requested.flag ファイルで停止検知。

- 環境設定 / 検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新するユーティリティ。
    - J-Quants / kabu API / DuckDB / SQLite / LINE などの主要設定を項目として用意。
  - validate_config.py
    - .env と config/*.yaml の検証ツール。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや YAML ファイルの存在・パースチェックを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数アクセスを集中管理。
    - 自動 .env ロード機能: プロジェクトルート (.git または pyproject.toml を基準) が見つかれば .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 各種プロパティ: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, 各閾値（CPU/MEM/DISK）や env/log_level のバリデーションを実装。
    - PAPER_FILL_MODE の妥当性検証（instant/partial/never/reject）。

- ログ / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通ユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決順を明確化し、ログディレクトリ作成に失敗した場合にファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - psutil を使ってプラットフォーム非依存でプロセス優先度（high/normal/low）を設定する関数を追加。
    - Windows / POSIX(nice) の違いを吸収し、設定失敗時には警告を出してスキップする。
    - set_cpu_affinity() を実装し、プロセスを先頭 N コアにピン留め可能（失敗時は警告）。
  - 起動スクリプトは起動直後に set_process_priority("high") を呼び出し、重要プロセスの優先度を上げる動作を採用。

- ポートフォリオ構築関連（pure 関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選別（タイブレークに signal_rank を採用）。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分。全スコアが 0 の場合は警告を出して等分配にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑制するフィルタ。既存保有のセクター比率に基づき新規候補を除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマップ、未知レジームは警告の上 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限 (max_position_pct)、aggregate cap（available_cash）に応じたスケールダウン、cost_buffer を用いた保守的見積り、残差分の優先配分ロジックを実装。

- 研究 / ファクター計算（出発点）
  - research/factor_research.py
    - Momentum 等ファクター計算の枠組みを実装（モメンタム・MA200乖離・ATR・出来高などの定義と計算方針）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算する設計（実装途中の関数あり）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計してレポートを標準出力へ出力。
    - 指標: 稼働率(uptime)、注文成功率(fill_rate)、送信率(send_rate)、レイテンシ（平均/最大/P95）。
    - Pass/Fail の閾値を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - 日付フィルタと --db オプションをサポート。

- DB / 分析エンジン
  - DuckDB 接続サポートを全体で採用（Settings.duckdb_path）。
  - 監視用 DB 初期化関数 init_monitoring_db を run_* スクリプトで呼び出してテーブル存在を保証（冪等）。

### Changed
- なし（初回リリースのため変更履歴はなし）

### Fixed
- なし（初回リリースのため修正履歴はなし）

### Breaking Changes
- なし（初回リリースのため互換性破壊はなし）

### Known Issues / Notes
- research/factor_research.py は実装途中（ファイル末尾が切れている / 未完成の関数あり）。今後のリリースで完全実装予定。
- apply_sector_cap の価格欠損時の扱いについて注釈あり（price が欠損の場合、エクスポージャーの過小評価につながる可能性があるため将来的にフォールバック価格を導入予定）。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム非対応でスキップされることがある（ログで警告）。運用環境によっては適切な権限設定が必要。
- .env の自動ロードはプロジェクトルート検出に依存する。配布パッケージ化後の動作を考慮して、KABUSYS_DISABLE_AUTO_ENV_LOAD を用いた制御が可能。
- logging_setup のファイル出力はログディレクトリ作成に失敗すると無効化され、コンソール出力のみになる。

---

参照:
- バージョンはパッケージ定義 (src/kabusys/__init__.py) の __version__ = "0.1.0" に基づく初版リリースです。
# Changelog

すべての注目すべき変更点はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。  

注: この CHANGELOG はリポジトリ内のコードを元に作成した初回リリース向けの要約です。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回公開リリース

### Added
- 実行・監視ランナー
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド起動と停止フラグ検知（data/stop_requested.flag）。
    - 実行 PID を data/execution.pid に書き出す仕組み（Engine に渡す pid_file）。
  - run_monitoring.py
    - SystemMonitor を定期的にポーリングする監視ループ。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログ警告のうえデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用（data/monitoring.db 等）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。

- 設定 / 環境管理
  - config.py
    - Settings クラスによる環境変数ラッパー（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境など）。
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。.env と .env.local の読み込み順と上書きルール（OS 環境変数保護）。
    - PAPER_FILL_MODE の検証（instant / partial / never / reject）。
    - KABUSYS_ENV, LOG_LEVEL 等の妥当性チェック。
  - config_setup.py
    - .env を対話式に生成・更新するウィザード。デフォルト値・選択肢・シークレットマスク対応。結果を .env に保存する機能。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML のパースチェック（PyYAML が無ければスキップ）、本番環境時の追加ガード等。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルから候補選定（スコア降順、signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等分にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用（既存保有のセクター時価に基づき候補を除外、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。未知レジームは 1.0 でフォールバック（警告を出力）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
    - リスクベース計算、1銘柄上限・aggregate cap（available_cash）・単元（lot_size, デフォルト 100）丸め処理、cost_buffer による保守的見積り、スケールダウンと端数配分のアルゴリズムを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティ。
    - stdout 出力の StreamHandler（stderr ではなく stdout を使用）と、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR /引数での上書き対応。ログディレクトリ作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）設定と CPU affinity 設定ユーティリティ。
    - Windows と POSIX（Linux, Darwin, FreeBSD）で差分を吸収。psutil を利用し、権限不足などは警告を出してスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から指標を集計して検証レポートを標準出力に出力。
    - 集計指標: 稼働率（system_status）、注文成功率 / 送信率（trade_logs）、リスク却下数（risk_logs）、レイテンシ統計（avg/max/P95）。P95 計算ユーティリティを実装。
    - デフォルト基準値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200 ms）を用いた PASS/FAIL 判定。
    - --from/--to/--db オプションをサポート。

- リサーチ / ファクター計算（着手）
  - research/factor_research.py
    - DuckDB 接続を受け、prices_daily / raw_financials テーブルを参照してモメンタム・バリュー・ボラティリティ・流動性などのファクターを計算する設計。モメンタム計算などの定数・方針が定義されている（関数実装はファイル内で進められている）。

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Removed
- 初回リリースのため該当なし

### Security
- 現時点で特記すべきセキュリティ修正はなし

---

補足メモ（実装上の重要ポイント）
- .env の自動読み込みはプロジェクトルートを探索して行われるため、CWD に依存しない挙動。
- run_monitoring は監視 DB に対して常に本番 sqlite_path を使う設計で、モニタリング結果は環境に関係なく同一 DB に集約される点に注意。
- run_execution は paper_trading モードで DB を分離するため、実運用と検証のデータ混在を避けられる。
- ログはデフォルトで logs/ 下に保存され、ファイル出力に失敗してもコンソールログは保証されるよう設計されている。
- process_priority は権限やプラットフォームに依存する操作を行うため、失敗時は警告ログにとどめて処理を継続する設計。

もし CHANGELOG の粒度（より細かいコミット単位や機能別の分割）を変更したい場合は指示してください。
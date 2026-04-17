# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。
リリース日付は 2026-04-17 （ソース内参照日付に合わせています）。

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージの初期実装を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 起動用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はリポジトリルートの `data/stop_requested.flag` を利用。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring 用 DB は環境に依らず本番向けの sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用 DB（`data/paper_trading.db`）と MockBrokerClient を使用し、本番 DB と分離。
    - 実行時にプロセス優先度を "high" に設定。停止フラグ検知でエンジン停止。
    - 実行時 PID ファイル（`data/execution.pid` 等）管理に対応。

- 設定管理・ウィザード・検証
  - config.py
    - .env ファイルおよび環境変数の読み込みを自動化（プロジェクトルート検出: `.git` または `pyproject.toml` をベースに探索）。
    - .env パーサを実装（`export KEY=val`、クォート、エスケープ、インラインコメント処理に対応）。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス /監視閾値などのプロパティを型付きで取得可能。
    - `PAPER_FILL_MODE` のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - 環境（KABUSYS_ENV）/ログレベルの検証ロジックを内包。
  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを追加。
    - シークレット項目のマスキング表示、デフォルト値・選択肢対応、保存前の確認を実装。
  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース検査（PyYAML が存在する場合）、本番環境向けの追加警告等を実装。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を取得。
    - calc_equal_weights / calc_score_weights: 等重配分・スコア加重配分の実装（スコア合計が 0 の場合は等重へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限に基づき新規候補をフィルタ（既存保有のセクター別エクスポージャ計算、sell_codes による除外対応）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に対する投下資金乗数を提供（未知レジームは 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer（手数料/スリッページ推定）を考慮したスケールダウンロジック。
    - リスクベース計算（risk_pct, stop_loss_pct）による株数算出を実装。
    - 将来の拡張点（銘柄別 lot_size 等）をコメントで明示。

- 研究（ファクター計算）
  - research.factor_research
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照してモメンタム / ボラティリティ等のファクターを計算するユーティリティを追加。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率算出（必要データ不足時は None）。
    - calc_volatility: ATR、相対 ATR、20日平均売買代金、出来高比等の計算（コード中にスキャン窓や欠損取り扱いの設計あり）。
    - 全関数は副作用なしで (date, code) 単位の辞書リストを返却する設計。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX の差分を吸収してプロセス優先度を設定する関数を追加（level: "high"|"normal"|"low"）。
    - set_cpu_affinity(cpu_count): カレントプロセスを先頭 N コアにピン留めする関数を実装。
    - psutil の権限エラーや未対応プラットフォームを安全にハンドリングし、失敗時は警告を出力してスキップ。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を参照して、起動時に監視用テーブルが存在することを保証（冪等処理）。

- Execution / Risk / Reconciler の既定設定
  - run_execution で組み立てられる RiskManager のデフォルトパラメータをコードに明記（max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - ExecutionEngine は Reconciler/OrderManager/OrderRepository 等のコンポーネントと連携して起動する設計。

- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成ツールを追加（SQLite DB を読み、稼働率・注文成功率・送信率・レイテンシ等を集計）。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - コマンドライン引数で期間（--from/--to）や DB パス（--db）を指定可能。
    - 空データやテーブル欠如に対する耐性あり（OperationalError を捕捉して N/A 表示）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Known issues / TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャが過少見積りとなりブロックが外れる可能性がある。コメントに将来の価格フォールバック戦略を示している。
- position_sizing:
  - 将来的に銘柄ごとの lot_size を持たせる等の拡張を想定（現状は全銘柄共通単元）。
- 設定や YAML 検証は PyYAML のインストール状況に依存して一部機能がスキップされる（validate_config の挙動）。
- 権限不足等によりプロセス優先度/CPU affinity の設定が失敗する場合は警告を出してスキップする設計。

---

このリリースは、ローカル開発・ペーパートレード・本番運用を見据えた初期基盤を提供します。設定ウィザード・検証ツール・監視・実行エンジンの起動フロー、ポートフォリオ構築とサイズ決定、ファクター計算ユーティリティ、ペーパートレード検証レポートといった主要機能を含みます。今後はテストカバレッジ、エラーハンドリングの強化、銘柄ごとの細かな取扱い（lot_size 等）や監視/アラートの充実を予定しています。
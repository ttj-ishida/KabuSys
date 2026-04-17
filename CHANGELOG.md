# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、慣例的に重要度別（Added / Changed / Fixed / Removed / Security）で記載しています。

## [Unreleased]
- (なし)

## [0.1.0] - 2026-04-17
初回リリース — KabuSys のコア機能を実装しました。以下はコードベースから推測される主要な追加点と挙動のまとめです。

### Added
- 全体
  - パッケージ初版をリリース（__version__ = 0.1.0）。
  - プロジェクトルート検出に基づく .env 自動ロード機能を追加。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
    - .env / .env.local の読み込み順序をサポートし、OS 環境変数は保護（上書き禁止）される。
    - export KEY=val, クォート文字列、インラインコメントなどの .env 構文を堅牢にパース。
  - Settings クラスでアプリケーション設定を一元管理。
    - DB パス (DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH)、KABUSYS_ENV の検証、LOG_LEVEL 検証、paper_trading の fill mode (PAPER_FILL_MODE) の検証など多数のプロパティを提供。
    - is_live / is_paper / is_dev の補助プロパティを提供。

- CLI / ユーティリティ
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 必須項目（J-Quants トークン、kabu API パスワード等）や任意項目、選択肢を対話的に扱える。
  - validate_config: 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML のパース検証（PyYAML が存在する場合）、本番(=live)用の安全ガード警告等を実行。
    - --strict オプションで警告をエラー扱いにできる。
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率 / 送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）などを集計し PASS/FAIL を判定する基準値を持つ。
    - 日付フィルタ (--from / --to) および --db オプションをサポート。

- 実行用スクリプト
  - run_execution:
    - ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは専用（分離された）SQLite を使用してペーパートレードを完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立てを行い、ExecutionEngine を別スレッドで実行。
    - 停止フラグ（data/stop_requested.flag）監視、PID ファイル保存、thread.join ベースの安全停止処理を実装。
    - RiskManager に対する既定設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を初期化。initial_portfolio_value は broker.get_available_cash() を使用。
  - run_monitoring:
    - SystemMonitor のポーリングループを開始するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視 DB 初期化（init_monitoring_db）と duckdb 接続を行う。Monitoring は環境にかかわらず本番 sqlite_path を使用する点に注意。
    - 停止フラグの検知でループを終了、例外はログ出力後に次回まで継続。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点時は signal_rank 昇順）でソートして上位 N を返す。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を提供。全スコアが 0 の場合は警告を出して等金額にフォールバック。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限(max_sector_pct) を評価し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: マーケットレジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を提供（未定義レジームは 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method("risk_based","equal","score") に基づいて発注株数を計算。
      - risk_based: risk_pct / stop_loss_pct ベースで株数を算出。
      - equal/score: weight に基づく配分、per-position および aggregate 上限を考慮。
      - lot_size（単元）丸め、cost_buffer を考慮した保守的なコスト見積り、available_cash を超える場合のスケールダウンロジック（残差を lot 単位で再配分）を実装。
      - 価格欠損（<=0）時は銘柄をスキップし、ログを出す。

- リサーチ
  - research.factor_research:
    - calc_momentum: DuckDB の prices_daily を用いて mom_1m/3m/6m と ma200 乖離を算出。必要なウィンドウが不足する場合は None を返す。
    - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比率などを計算するクエリを実装（途中実装あり）。Pandas等を使わず DuckDB SQL とウィンドウ関数で計算。

- OS / プロセス制御
  - utils.process_priority:
    - set_process_priority(level): Windows と POSIX(Linux/Mac/FreeBSD) を吸収してプロセス優先度を設定。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数で CPU affinity を固定するユーティリティ（未指定はスキップ）。不正値は例外。

### Changed
- (初回リリースのため該当なし)

### Fixed
- (初回リリースのため該当なし)

### Removed
- (初回リリースのため該当なし)

### Security
- 環境変数やシークレット値（.env 内の J-Quants / KABU API パスワード等）について、config_setup の出力で明示的に機密扱い（表示をマスク）するなど、秘匿に配慮した実装を導入。

---

補足・注意事項（実装から推測）
- 監視モジュールは本番 sqlite_path を使うため、本番/ペーパーの DB 分離は run_execution 側でのみ担保されています。監視 DB に誤って本番データを書きたくない場合は設定を確認してください。
- .env の自動読み込みはプロジェクトルートが検出できない場合にスキップされます。配布後やコンテナ環境では意図通り動作するか確認してください。
- process priority / cpu affinity の設定は権限に依存します。特に Linux で負の nice 値を設定するには権限が必要です。
- Paper Trading の検証レポートはデータベースのスキーマ（system_status / trade_logs / risk_logs 等）存在に依存します。存在しない場合は N/A / 0 を扱うように実装されています。

（必要なら変更内容を英語版に翻訳したり、個別ファイルごとの詳細な変更差分を追加できます。ご希望があれば指示してください。）
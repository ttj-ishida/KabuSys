# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ初期実装を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 SQLite パスを使用する設計（Settings.sqlite_path）。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）を検知してループ終了。
    - sqlite3 と DuckDB の接続管理を実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を用いて paper_trading 専用 DB（デフォルト: data/paper_trading.db）に記録することで本番 DB と分離。
    - プロセス優先度を "high" に設定。
    - PID ファイル管理、停止フラグ検知、デーモンスレッドでの ExecutionEngine 実行/停止制御を実装。
    - RiskManager / OrderManager / Reconciler 等の依存コンポーネントを組み立てる起動処理を追加。
- 設定管理
  - config.py
    - Settings クラスを導入。環境変数をラップして利用するプロパティ群を提供（J-Quants、kabu API、DB パス、監視閾値、環境判定など）。
    - `.env` 自動ロード機能を実装（プロジェクトルートの判定: .git または pyproject.toml を基準）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパース機能で `export KEY=val`、クォート付き値、インラインコメント等に対応。
    - 各種入力値の検証（`PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL` など）を実装。
  - config_setup.py
    - 対話式ウィザードで `.env` を作成 / 更新する CLI を追加（項目の説明、シークレット取り扱い、既存値の再利用などをサポート）。
  - validate_config.py
    - 起動前検証 CLI を追加。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在（および PyYAML がある場合はパース検証）・本番環境向けのガードチェックを実行。
    - `--strict` オプションで警告を失敗扱いにできる。
- モニタリング DB 初期化
  - monitoring.monitoring_db:init_monitoring_db を呼び出して監視テーブルの存在を保証する処理を各起動処理に組み込み（冪等）。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを実装。
    - `LOG_DIR` / `LOG_LEVEL` / 引数による上書きをサポート。既存ハンドラの二重登録防止処理を実装。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows と POSIX を吸収）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を追加。
    - アクセス権限不足などの失敗を警告してスキップする堅牢化。
- Portfolio（ポートフォリオ構築）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全て 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用（apply_sector_cap）を実装。既存保有のセクター別エクスポージャを計算し、上限を超えるセクターの新規候補を除外する挙動。
    - 市場レジームに応じた乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマップ、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）、コストバッファを考慮した aggregate cap（スケールダウン）を実装。
    - スケールダウン時に残差を lot_size 単位で再配分するロジックを実装。
- Tools
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率（Fill Rate）、送信率（Send Rate）、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH`（または data/paper_trading.db）。`--from` / `--to` / `--db` CLI オプションを提供。
    - P95 算出、各種 SQL 集計クエリ、閾値（稼働率 99%、注文成立率 90% など）を定義。
- Research
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（モメンタム、MA200乖離、ATR、ボリューム等の設計と定数）。DuckDB 接続を受けて prices_daily / raw_financials を参照する方針。calc_momentum 関数の実装開始（モジュールは今後拡張予定）。
- パッケージエクスポート
  - portfolio モジュールのトップレベルから主要関数をエクスポートする __init__ を追加。

### Changed
- N/A（初回リリースにつき互換性破壊はなし）

### Fixed
- N/A（初回リリースにつき修正履歴なし）

### Security
- N/A

### Notes / Known limitations
- .env の自動読み込みはプロジェクトルートの自動検出に依存する（.git または pyproject.toml）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャが過少見積りされる可能性があり、コード内に将来的なフォールバック値採用の TODO コメントがあります。
- research/factor_research.py はモジュールの骨子を実装中で、完全なファクター群の実装は今後の作業です（ファイル末尾が未完の箇所あり）。
- process_priority/set_cpu_affinity やプロセス優先度設定は環境によって権限が必要となる場合があり、権限不足時はロギングで警告を出してスキップします。
- run_monitoring/run_execution は実行環境の設定（各種環境変数、kabu API や J-Quants のトークン等）に依存します。validate_config を先に実行して設定を確認してください。

---

今後の予定（例）
- factor_research の完成（モメンタム、Value、Volatility、Liquidity の実装とテスト）
- ExecutionEngine / BrokerClient の追加テストとモック実装の充実
- 監視・アラート周りの LINE 通知連携や監視 DB のスキーマ強化

（必要であれば、上記項目ごとの差分やコミット参照をもとにさらに詳細な CHANGELOG を作成します。）
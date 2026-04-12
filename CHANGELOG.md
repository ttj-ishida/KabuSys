# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-12

### Added
- 初期リリース。KabuSys 自動売買フレームワークのコア機能を追加。
- アプリケーション設定:
  - kabusys.config.Settings クラスを導入し、環境変数/.env/.env.local からの設定読み込みを提供。
  - 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行い、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須環境変数を検出してエラーを投げる _require() を提供。
  - 多数の設定プロパティを実装（J-Quants / kabu API / LINE トークン / DB パス /監視閾値 /環境区分 等）。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を実装。
  - 環境区分 KABUSYS_ENV のバリデーション（development/paper_trading/live）。

- 実行スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成（paper_trading 向け Mock の利用を想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、ExecutionEngine を起動するワークフローを実装。
    - duckdb 接続の利用と監視テーブル初期化（init_monitoring_db）を実行。
    - RiskManager のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定し、初期ポートフォリオ値を broker.get_available_cash() で取得して設定。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視処理は常に本番 sqlite_path を参照して監視 DB を初期化する仕様。
    - プロセス優先度を起動時に "high" に設定（utils.process_priority.set_process_priority を使用）。

- 監視 DB ユーティリティ:
  - monitoring.monitoring_db.init_monitoring_db（呼び出し箇所有り）で監視用テーブルの存在を保証（冪等性）。

- ユーティリティ:
  - utils.process_priority:
    - set_process_priority(level) — Windows/POSIX の差を吸収してプロセス優先度 (high/normal/low) を設定（権限不足時は警告でスキップ）。
    - set_cpu_affinity(cpu_count) — カレントプロセスを先頭 N コアに固定する機能（未指定なら何もしない）。不許可や未対応プラットフォームでは警告でスキップ。

- ポートフォリオ構築（純粋関数群、DB非依存）:
  - portfolio.portfolio_builder:
    - select_candidates(buy_signals, max_positions) — スコア降順で上位を選択（同点は signal_rank でブレーク）。
    - calc_equal_weights(candidates) — 等金額配分を計算。
    - calc_score_weights(candidates) — スコア加重配分を計算。全スコアが 0 の場合は等金額にフォールバックして警告。
  - portfolio.risk_adjustment:
    - apply_sector_cap(...) — セクター集中上限(max_sector_pct)に基づき新規候補を除外するロジック（"unknown" セクターは除外対象外）。売却予定銘柄を除外してエクスポージャーを計算。
    - calc_regime_multiplier(regime) — レジームに応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3）。未知レジームは 1.0 にフォールバックして警告。
  - portfolio.position_sizing:
    - calc_position_sizes(...) — allocation_method（risk_based / equal / score）に基づき発注株数を計算。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）でスケーリング、cost_buffer による保守的見積り、スケールダウン時の端数処理（残差順で追加配分）を実装。
    - risk_based ではリスク・損切り率ベースで株数を算出。

- リサーチ / ファクター計算:
  - research.factor_research:
    - calc_momentum(conn, target_date) — 1M/3M/6M リターン、MA200乖離率を計算（データ不足時は None）。
    - calc_volatility(conn, target_date) — ATR20、相対ATR、20日平均売買代金、出来高比率を計算（NULL伝播の扱いに注意）。
    - calc_value(conn, target_date) — raw_financials から最新財務を取得し PER / ROE を計算（EPS=0 や欠損は None）。
    - DuckDB を前提とした SQL 実装で、prices_daily / raw_financials を参照。
  - research.feature_exploration:
    - calc_forward_returns(conn, target_date, horizons) — LEAD を用いて複数ホライズンの将来リターンを一度に計算（horizons の妥当性チェックあり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンランク相関（IC）を計算。3 件未満・分散ゼロ等では None を返す。
    - rank(values) — 同順位は平均ランクで扱うランク付けユーティリティ（丸めで ties 検出漏れを防止）。
    - factor_summary(records, columns) — count/mean/std/min/max/median を計算する統計サマリ。

- AI ニュース NLP:
  - ai.news_nlp:
    - ニュース記事を OpenAI (gpt-4o-mini) にバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB を検索）。
    - 最大 20 銘柄/API コール、1銘柄あたり最大記事数・文字数でトリム（記事肥大化対策）。
    - 429/ネットワーク/5xx に対する指数バックオフリトライ（最大リトライ回数指定）。
    - レスポンスのバリデーションとスコアクリッピング（±1.0）。部分失敗時に既存スコア保護のため対象コードに絞って更新を行う設計（DELETE/INSERT の手順記載）。
    - API キー未設定時は ValueError を送出。

- ツール:
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成 CLI を追加。コマンドライン引数で期間指定可（--from / --to / --db）。
    - 報告内容: システム稼働率（system_status）、注文成功率/送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（avg/max/P95）。
    - Pass/Fail 基準を定義（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 <=200ms）。集計クエリは sqlite を使用。
    - P95 は全値を収集して計算。DB 存在チェックおよび OperationalError に対するフォールバック実装。

- パッケージメタ:
  - kabusys.__init__.__version__ を "0.1.0" に設定。
  - research パッケージで公開 API を整理（zscore_normalize の re-export 等）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- OpenAI API キーは明示的に無ければ例外を出すことで誤設定を検出する実装を追加（ai.news_nlp）。

### Notes / Known limitations
- .env パーサはクォート内のバックスラッシュエスケープやコメントの扱いに独自実装をしているため、複雑な .env 行が存在する場合には注意が必要。
- position_sizing の lot_size は全銘柄共通で固定（将来的な銘柄別単元対応は TODO）。
- apply_sector_cap のエクスポージャー計算は price_map に依存しており、price が欠損（0.0）の場合は過少見積りになる可能性がある（TODO コメントあり）。
- ai.news_nlp の実行は OpenAI API 利用料が発生するため、本番実行時のコストに注意。
- run_monitoring / run_execution は起動時にプロセス優先度を "high" に設定しようとするが、権限やプラットフォームにより設定に失敗する場合がある（警告でスキップ）。

---

今後のリリースでは、テストカバレッジ、エラー処理の強化、個別銘柄の lot_size 対応、外部依存の抽象化（API クライアントのインターフェース化）などを予定しています。
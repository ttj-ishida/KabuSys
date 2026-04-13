# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョンは [0.1.0]（初回公開）です。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-13
初回リリース。以下の主要機能・ユーティリティ・ツールを実装しました。

### Added
- 全体
  - パッケージ初期化とバージョン設定を追加（kabusys.__version__ = "0.1.0"）。
  - モジュール分割により、実運用（execution/monitoring）、ポートフォリオ構築、リサーチ、AIニューススコアリング、ユーティリティ、検証ツールを提供。

- 実行・監視ランナー
  - run_execution: ExecutionEngine の起動スクリプトを追加。
    - プロセス優先度を "high" に設定する機能を呼び出す。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite DB（PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory を使ってブローカークライアントを取得し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、initial_portfolio_value をブローカーから取得。
    - 監視テーブルの存在を保証するため init_monitoring_db を呼び出す（冪等）。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックし警告を出力。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を "high" に設定、SQLite/DuckDB 接続を初期化、例外発生時はログを残して次のポーリングに継続。KeyboardInterrupt を受けてグレースフル終了。

- 設定管理
  - config.Settings を追加して環境変数から設定を取得する一元化。
  - .env 自動ロード機構:
    - プロジェクトルートを .git または pyproject.toml から探索して自動的に .env / .env.local を読み込む。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env 解析で `export KEY=val`、クォート、エスケープ、インラインコメントに対応。
    - 読み込み時に既存 OS 環境変数を保護するための protected キー扱い。
  - Settings に多数のプロパティ（パス、API トークン、PID/KILL フラグ、閾値、環境検証、PAPER_FILL_MODE の検証等）を実装。値検証により不正値で例外を送出する箇所を用意。

- ユーティリティ
  - process_priority ユーティリティを追加。
    - set_process_priority(level) で Windows / POSIX（Linux, Darwin, FreeBSD）に対して優先度（nice / HIGH_PRIORITY_CLASS 等）を設定（未対応 OS は警告でスキップ）。
    - set_cpu_affinity(cpu_count) でプロセスを先頭 N コアにピン固定（アクセス権限や未実装時は警告でスキップ）。
    - 設定失敗時に AccessDenied 等を捕捉して安全にスキップする挙動。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順、同点時は signal_rank でタイブレークして上位 N を返す。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全スコアが 0 の場合は等配分にフォールバックして警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有と価格からセクターエクスポージャーを計算し、1 セクター上限超過時に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた乗数を返す（bull=1.0, neutral=0.7, bear=0.3、未知は警告の上 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき各銘柄の発注株数を算出。lot_size（単元株）丸め、max_position_pct による per-stock cap、available_cash による aggregate cap、cost_buffer を考慮した保守的見積り、スケールダウン時の再配分（端数処理を考慮）を実装。

- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離率（ma200_dev）を DuckDB のウィンドウ関数で計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高変化率等を計算。高/低/前日終値の欠損を考慮して true_range を正しく扱う。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算。
  - research.feature_exploration:
    - calc_forward_returns: 1/5/21 日等の将来リターンを LEAD を使って一括取得。horizons の検証あり。
    - calc_ic: Spearman（ランク相関）による IC 計算を実装（データ不足時は None）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を算出。
  - research.__init__ で主要関数をエクスポート（zscore_normalize は kabusys.data.stats から再利用）。

- AI ニュース NLP
  - ai.news_nlp:
    - raw_news / news_symbols を集約し、OpenAI API（デフォルト gpt-4o-mini）にバッチ送信して銘柄別のセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込むロジックを実装。
    - ニュース収集ウィンドウを JST 基準で定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較）。
    - 1 銘柄あたり記事数・文字数を制限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）してトークン膨張を抑制。
    - バッチサイズ _BATCH_SIZE（20）で最大 20 銘柄ずつ送信、429/ネットワークエラー/5xx に対する指数バックオフ（最大リトライ回数設定）。
    - レスポンスの厳密な JSON 検証、スコアの ±1.0 クリップ、部分成功時の DB 書き換え戦略（対象コードに絞った置換）等、フェイルセーフ設計。
    - API キーが未設定の場合は ValueError を送出。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite DB を解析して検証レポートを生成する CLI（--from / --to / --db オプション対応）。
    - システム稼働率（system_status）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、レイテンシ（平均/最大/P95）を計算して表示。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）し、Pass/Fail 判定を行う。
    - DB が存在しない場合やテーブルが無い場合に備えた例外処理（sqlite3.OperationalError の捕捉）を実装。

### Changed
- なし（初回リリースのため変更一覧なし）。

### Fixed
- なし（初回リリースのため修正一覧なし）。

### Security
- OpenAI API キーの扱いは引数優先、環境変数 OPENAI_API_KEY の使用。未設定時は明示的なエラーを返す。

---

注意:
- 多くのモジュールは「DB 参照なし（純粋関数）」として設計されていますが、実運用モジュール（execution/monitoring/ai/news_nlp/research）は DuckDB や SQLite、外部 API、ブローカークライアントへ接続します。実行時に適切な環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）およびディレクトリ・ファイル権限が必要です。
- .env 自動読み込みはプロジェクトルート検出を行うため、配布形態やテスト環境に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して無効化できます。
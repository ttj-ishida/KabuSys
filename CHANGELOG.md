# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（現時点なし）

## [0.1.0] - 2026-04-12

初期リリース。KabuSys のコア機能を実装しました。以下はコードベースから推定した主な追加点・設計方針・既知制限のまとめです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期版（__version__ = 0.1.0）。
  - 明確なモジュール分割：execution / monitoring / portfolio / research / ai / utils / tools。

- 実行関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を設定（set_process_priority("high")）。
    - 環境に応じて本番 DB / paper_trading 用 DB を使い分け（KABUSYS_ENV = `paper_trading` の場合は専用 SQLite を使用）。
    - BrokerClientFactory を用いブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskConfig のデフォルトパラメータを設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。initial_portfolio_value は broker.get_available_cash() を使用。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告を出力）。
    - 監視（monitoring）処理は環境にかかわらず本番 sqlite_path を使用する意図の実装。
    - 監視ループ中の例外はログに残して次のポーリングへ継続するフェイルセーフ。

- 設定管理
  - config.Settings クラスを導入。
    - .env / .env.local の自動読み込み（プロジェクトルート判定: .git または pyproject.toml を探索）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 各種環境変数のプロパティ化（J-Quants / kabu API / LINE / データベースパス / 監視閾値 / PID/KILL ファイルパス / 環境種別 / ログレベル判定等）。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL などの値チェックを実装。
    - デフォルトパス（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など）を定義。

  - .env ローダー（_load_env_file / _parse_env_line）
    - export プレフィックス対応、クォート文字列内のバックスラッシュエスケープ対応、インラインコメント処理などを実装。
    - override/protected のオプションで OS 環境変数を保護。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level) を実装（Windows / POSIX を吸収）。
    - set_cpu_affinity(cpu_count) による CPU 固定機能。
    - 権限不足や未サポート環境では警告を出してスキップする堅牢性。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順（同点は signal_rank）で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。全スコアが 0 の場合は等分にフォールバックして警告。

  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有を考慮したセクター上限（max_sector_pct）適用。unknown セクターは上限適用除外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた資金乗数を返す（未定義レジームは 1.0 にフォールバックして警告）。

  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
    - 単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料/スリッページ見積）を考慮。
    - スケールダウン時は残差を lot 単位で再分配するアルゴリズムを実装。

- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB を用いた SQL＋ウィンドウ関数で計算（200 日 MA、ATR20、各種モメンタム等）。
    - データ不足時は None を返すよう設計。

  - research.feature_exploration:
    - calc_forward_returns（任意ホライズン対応）、calc_ic（Spearman ランク相関）、rank（平均ランク tie 処理）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等外部依存なしで実装。horizons の検証あり（1〜252）。

- AI / ニューススコアリング
  - ai.news_nlp:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出・ai_scores テーブルへ書き込み。
    - バッチサイズ、トークン肥大対策（記事数/文字数トリム）、最大リトライ、指数バックオフ、レスポンスバリデーション、スコアクリップ実装。
    - API キー未設定時は ValueError を投げる（api_key 引数または OPENAI_API_KEY 環境変数）。
    - タイムウィンドウ計算（calc_news_window）を実装（JST 前日 15:00 〜 当日 08:30 に対応する UTC 範囲を返す）。
    - 部分失敗時にも既存スコアを保護するために対象コードのみ置換する書き込み戦略。

- ツール
  - tools.paper_verification_report:
    - paper trading の検証レポート生成スクリプトを追加（コマンドライン: --from / --to / --db）。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を行う。
    - DB が存在しない、またはテーブルが不足する場合に堅牢に N/A を扱う。

- DB 初期化
  - monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- （初期リリースのため特に互換性破壊や移行項目は無し）

### Fixed / Hardening
- 環境変数の検証強化や堅牢化を多数実施（例: MONITOR_POLL_INTERVAL の不正値検出とフォールバック、PAPER_FILL_MODE の許容値チェック、calc_forward_returns の horizons 検証）。
- 外部リソース操作時の例外ハンドリング強化（DB 接続クローズ、psutil の権限エラー時の警告、監視ループ内の例外ログと継続）。

### Known issues / Notes / TODO
- apply_sector_cap のエクスポージャー計算は price が欠損（0.0）だと過少見積りになる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO が残る。
- news_nlp は外部 API（OpenAI）に依存するため、API レート制限や料金、キー管理に注意が必要。部分失敗時の挙動は保護を入れているが、完全冪等性は状況依存。
- DuckDB 側の制約（executemany の空パラメータ等）に注意する実装上の考慮がコメントで示されている。
- run_monitoring はコード上「監視は環境にかかわらず本番 sqlite_path を使用する」設計になっているため、開発環境で監視用データを分離したい場合は設定（SQLITE_PATH 等）に注意が必要。
- set_cpu_affinity はプラットフォームや権限によって未サポートの場合がある（警告を出してスキップ）。

### Security
- OpenAI API キーや各種シークレットは環境変数経由で扱う設計。.env 自動読み込みはデフォルトで有効だが、テスト等で自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを用意。
- .env 読み込み時に OS 環境変数は protected として上書きを防ぐ仕組みを導入。

---

（注）本 CHANGELOG は提示されたソースコードの内容・コメントから推測して作成したものであり、実際のコミット履歴ではありません。実際の変更履歴を生成する際は git の履歴やリリースノートを参照してください。
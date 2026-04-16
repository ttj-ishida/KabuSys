# CHANGELOG

すべての変更は Keep a Changelog に準拠しています。  
日付はコードベースから推測して付与しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-16

初回公開リリース。自動売買システム「KabuSys」のコア機能群を実装。

### 追加 (Added)
- 全体
  - パッケージ初期版を公開（__version__ = 0.1.0）。
  - パッケージ API エクスポートを定義（portfolio / research / ai 等）。

- 実行 / 監視
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine をスレッドで実行。PID 管理・停止フラグ (data/stop_requested.flag) をサポート。
    - デフォルトの RiskConfig を提供（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）。初期 available_cash は broker.get_available_cash() から取得。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（安全に本番データを参照）。
    - プロセス優先度を起動時に "high" に設定する処理を共通化して呼び出し。

- 設定関連
  - config.py
    - .env/.env.local の自動ロード機構を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - .env パーサは export 宣言、シングル/ダブルクォート、エスケープ、インラインコメントを適切に扱う。
    - Settings クラスを実装し、JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須値チェック、各種パス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH)・閾値 (CPU/MEM/DISK)・ログレベル・環境種別 (development/paper_trading/live) をプロパティ経由で提供。
    - PAPER_FILL_MODE の検証（valid: "instant" | "partial" | "never" | "reject"）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア合計が 0 の場合は等配分にフォールバックして警告を出す挙動を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有を除外してセクター別時価総額から上限判定）。"unknown" セクターは上限除外（緩和）扱い。
    - レジームに応じた乗数 calc_regime_multiplier を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株 (lot_size)、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング、aggregate cap 超過時のスケールダウンと端数処理（lot 単位で再配分）を実装。
    - 価格欠損時にはスキップし、ログ出力で通知。

- リサーチ / ファクター計算
  - research/factor_research.py
    - モメンタム（1M/3M/6M, MA200偏差）、ボラティリティ（ATR20, ATR%, 平均出来高, 出来高比率）、バリュー（PER, ROE）を DuckDB に対する SQL + Python で実装。
    - ウィンドウサイズやデータ不足時の None 戻し、SQL 内でのウィンドウ関数利用など工夫。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（複数ホライズン対応）、Spearman ランク相関による IC 計算 calc_ic、ランク関数 rank、ファクター統計 summary を実装。
    - 入力検証（horizons の範囲制約）や ties の平均ランク処理を実装。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出する処理の実装。
    - ニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 換算）を calc_news_window で提供。
    - バッチサイズ（最大 20 銘柄）、1 銘柄あたりの記事数・文字数上限 (_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）、スコアの ±1.0 クリップ、エクスポネンシャルバックオフによるリトライ（429/ネットワーク/5xx/タイムアウト）等をサポート。
    - API キー未設定時は ValueError。処理はルックアヘッドバイアスを避けるため date.today() を使わない設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを計算して PASS/FAIL 判定を行う（閾値はコード内定義）。
    - SQLite DB を直接参照して集計、期間指定（--from/--to）、DB パス指定 (--db / env PAPER_TRADING_SQLITE_PATH) をサポート。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差（Windows / POSIX）を吸収してプロセス優先度設定（high/normal/low）と CPU affinity 設定を提供（psutil ベース）。
    - 権限不足や未対応プラットフォーム時は警告して安全にスキップ。

### 変更 (Changed)
- .env の読み込み優先順位を明確化（OS 環境 > .env.local > .env）。OS 環境変数は protected として上書きを防止。
- Monitoring 周りの設計:
  - 監視は環境にかかわらず本番 sqlite_path を使用する仕様を明示。
  - MONITOR_POLL_INTERVAL の無効値チェックを追加し、ログで警告してデフォルトにフォールバック。

### 修正 (Fixed)
- 無効な環境変数 / 設定値に対するフォールバックとログ出力を多数実装。
  - PAPER_FILL_MODE の不正値検出。
  - LOG_LEVEL / KABUSYS_ENV の不正値検出。
  - MONITOR_POLL_INTERVAL が負・ゼロまたは非整数の時に ValueError を防ぐ処理を追加。

### 注意事項 / 既知の制限 (Known issues / Notes)
- price_map に価格が欠損（0.0）だと sector_exposure が過少見積もられる旨の TODO コメントあり。前日終値や取得原価でのフォールバックは未実装。
- DuckDB の executemany に関する制約への対応をコードコメントで言及（空パラメータのチェックなど）。
- ai/news_nlp.py の一部（記事フェッチ／API 呼び出し後の処理）は実装途中（ソースの末尾が切れている可能性あり）。実行時は未実装箇所に注意。
- CPU affinity の設定は OS/権限によっては失敗する可能性があり、その場合は警告ログを出してスキップする。

### セキュリティ (Security)
- OpenAI API キーや各種機密情報は環境変数で管理。Settings._require により必須値未設定時は早期にエラーを出す設計。

---

今後のリリースでは以下を想定しています（コード内コメント・TODO に基づく）:
- price のフォールバック戦略実装（前日終値や取得原価による補完）。
- ai/news_nlp の完全実装とエンドツーエンドの検証（API レスポンス検証・DB 書き込みの堅牢化）。
- execution / risk 周りの追加ユニットテストとシミュレーション用モード拡張。
- 単体テスト・CI の追加とドキュメント充実。
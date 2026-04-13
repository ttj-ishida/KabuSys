# Changelog

すべての変更点は Keep a Changelog の形式に準拠しています。  
日付はリリース推定日（コードベースの最終更新に基づく）です。

現在のバージョン: 0.1.0

## [Unreleased]
- なし

## [0.1.0] - 2026-04-13
初回リリース。自動売買システム KabuSys のコア機能群を実装しました。

### Added
- 基本情報
  - パッケージのバージョンを `kabusys.__version__ = "0.1.0"` として設定。

- 設定管理
  - kabusys.config.Settings クラスを実装。
    - .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 環境変数のパース処理（引用符、エスケープ、コメントの取り扱いに対応）。
    - 必須環境変数チェック（_require）。
    - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視設定, システム種別判定等）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 入力検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- 実行エントリ / デーモン化関連
  - run_monitoring.py
    - SystemMonitor ポーリングループの起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite / DuckDB 接続を取得し、init_monitoring_db を呼び出して監視テーブルの存在を保証。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskConfig のデフォルト値を実装（例: max_position_pct=0.20, max_utilization=0.80 等）。
    - ExecutionEngine.run_session の呼び出し。

- ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority(level): Windows と POSIX (Linux/Mac/FreeBSD) を吸収して nice / priority を設定。失敗時は警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留め。未サポート・権限不足時は警告でスキップ。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順選定（同点時 signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights（スコア全0 の場合は等配分へフォールバック）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限に基づく候補フィルタリング（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームは警告の上 1.0 をフォールバック）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: 等配分 / スコア配分 / リスクベース配分を実装。lot_size（単元）丸め、per-stock 上限・aggregate cap、cost_buffer を考慮したスケーリング。

- 研究・ファクター計算
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M のリターン、MA200 乖離率を DuckDB 上で計算。
    - calc_volatility: ATR20, 相対 ATR, 20日平均売買代金, 出来高比を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（target_date 以前の最新レコードを参照）。
    - 実装は DuckDB に対する SQL を中心にし、prices_daily/raw_financials を参照。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）を実装（レコード数 < 3 の場合は None）。
    - factor_summary / rank: ファクター列の統計量とランク変換ユーティリティ。
    - 標準ライブラリのみで実装（pandas 等非依存）。

- AI（ニュース NLP）
  - kabusys.ai.news_nlp
    - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化し ai_scores に書き込む処理（score_news）。
    - 日時ウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部は UTC に変換して扱う）。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事上限・文字数上限（デフォルト: 10 件, 3000 文字）。
    - 429/ネットワーク/5xx に対する指数的バックオフリトライ（最大 3 回）。
    - レスポンス検証・スコアの ±1.0 クリッピング、部分成功でも既存スコアを保護するために更新対象コードを限定して DELETE→INSERT で置換。
    - OPENAI_API_KEY 必須（引数 / 環境変数から解決）。未設定時は ValueError。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用検証レポート生成 CLI（python -m kabusys.tools.paper_verification_report）。
    - DB パスは --db / PAPER_TRADING_SQLITE_PATH / data/paper_trading.db の優先順位で解決。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定。
    - レポートは標準出力にフォーマット出力。
    - P95 の算出、SQL の存在チェックや sqlite3.OperationalError のフォールバック処理を含む。

- パッケージエクスポート
  - kabusys.research と kabusys.portfolio の __all__ を整備し、主要関数をトップレベルから import 可能に。

### Security / Requirements
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings にて必須。
  - OPENAI_API_KEY は news_nlp.score_news 実行時に必須（明示的引数または環境変数）。
- .env 読み込みの挙動:
  - OS 環境変数が優先され、.env.local は .env を上書き可能。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

### Notes / Breaking changes
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するため、監視データは paper_trading とは分離されない点に注意。
- Execution (run_execution) は paper_trading 環境で paper_sqlite_path を使用して本番 DB と分離する設計。
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。不正値は ValueError。
- process_priority の操作は権限や OS に依存するため、権限不足時は警告を出力してスキップする挙動。

### Fixed
- なし（初回リリース）

### Removed / Deprecated
- なし

---

この CHANGELOG はコードベースから機能・挙動を推測して作成しています。実際のリリースノート作成時は各コミット / PR の履歴やドキュメントと照合してください。
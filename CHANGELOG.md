# CHANGELOG

すべての重要な変更は本ファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

- 概要: 初期リリース（0.1.0）として、実運用向けの実行エンジン・監視・ポートフォリオ構築・リサーチ・ニュースNLP 等の主要機能を実装しました。環境変数／.env 読み込み、DuckDB/SQLite を用いたデータ処理、Paper Trading 用分離 DB、OpenAI を用いたニュースセンチメント集計などを含みます。

## [0.1.0] - 2026-04-12

### Added
- 全般
  - パッケージ初期バージョンを追加（kabusys.__version__ = "0.1.0"）。
  - プロジェクトルート検出を行い .env / .env.local を自動ロードする仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。.env のパースは export 形式やクォート・インラインコメント等に対応。

- 実行／監視
  - 実行エントリ:
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
    - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。プロセス優先度を高く設定して監視を開始し、監視は環境に依らず本番用 sqlite_path を使用。
  - 実行環境分離:
    - Paper Trading モード (KABUSYS_ENV=paper_trading) 時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する仕組みを追加。

- 設定管理
  - config.Settings クラスを実装。各種環境変数に対するプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / PID/KILL フラグ / ログレベル等）。
  - PAPER_FILL_MODE の入力検証を実装（有効値: instant/partial/never/reject）。
  - KABUSYS_ENV の入力検証を実装（development / paper_trading / live のみ有効）。
  - ログレベルの検証を実装。

- データベース・ユーティリティ
  - monitoring_db.init_monitoring_db を使って監視テーブルの初期化（冪等）を実行する仕組みを run_* スクリプトに組み込み。
  - DuckDB / SQLite の接続管理を追加。

- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順、同点時は signal_rank でタイブレークして候補抽出。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。スコア合計が 0 の場合は等配分にフォールバックし WARNING を出力。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別エクスポージャを元にセクター上限を超える候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: レジームに応じた資金乗数を返す（bull/neutral/bear をマップし、未知のレジームでは警告とともに 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方法をサポート。lot_size（単元）で丸め、per-position 上限・aggregate cap（available_cash）を考慮してスケールダウン・残余の配分ロジックを実装。cost_buffer による保守的コスト見積りを考慮。

- リサーチ（DuckDB ベース）
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを計算（ウィンドウ不足時は None を返す設計）。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターンを複数ホライズンで計算（ホライズン検証あり）。
    - calc_ic: Spearman ランク相関（IC）計算。データ不足（有効レコード < 3）の場合は None。
    - factor_summary / rank: 基本統計量とランク付けユーティリティを提供。
  - research パッケージは kabusys.data.stats.zscore_normalize を再エクスポート。

- ニュース NLP（OpenAI）
  - ai.news_nlp:
    - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメントを算出し、ai_scores に書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（1銘柄あたり最大記事数／最大文字数）、リトライ（429 / network / 5xx 用の指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードで DELETE→INSERT）などの堅牢設計を導入。
    - API キーが未設定の場合は ValueError を送出。
    - calc_news_window ユーティリティを実装（JST ベースのニュースウィンドウを UTC naive datetime で返す）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成 CLI を追加。--from / --to / --db オプションをサポート。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算して PASS/FAIL 判定を行う。DB が存在しない場合やテーブル欠損時に適切にメッセージ/デフォルトを出力する。
    - P95 計算やフォーマットユーティリティを実装（空データ時は "N/A" 表示）。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）で優先度を設定するユーティリティを実装。未対応 OS はスキップし警告を出力。アクセス権限不足等は警告で無視してフォールバック。
    - set_cpu_affinity: 最初の N コアにプロセスを固定する関数を追加。None の場合は何もしない。引数検証とエラーハンドリングあり。

### Changed
- なし（初回リリースのため差分履歴なし）。

### Fixed
- なし（初回リリースのためバグ修正履歴なし）。

### Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で供給する形にし、未設定時は明示的な例外を発生させることで誤った無認証呼び出しを防止。

### Notes / Breaking changes（注意点）
- Settings の各プロパティは環境変数の検証を行い、不正な値が設定されていると ValueError を送出します。特に KABUSYS_ENV と PAPER_FILL_MODE、LOG_LEVEL は有効な値に制限されています。自動ロードされる .env ファイルの仕様（export 形式やクォート処理）に依存するため、既存の .env と互換性の問題がある場合は確認してください。
- run_monitoring は「監視用 DB」として Settings.sqlite_path（本番想定）を環境にかかわらず使用します。開発や paper_trading 向けに監視データを別 DB にしたい場合は実装を拡張する必要があります。
- ai.news_nlp の実装では OpenAI への API 呼び出しが含まれるため、API 利用に伴うコストやレート制限を考慮してください。429/ネットワークエラー等はリトライで扱いますが、完全な成功を保証するものではありません。
- DuckDB / SQLite を利用するクエリ群（research.* や ai.news_nlp、tools.*）は期待されるテーブル（prices_daily, raw_financials, raw_news, news_symbols, trade_logs, risk_logs, system_status など）が存在することを前提としています。テーブルが無い場合は一部機能がデフォルト値や N/A を返す設計ですが、実運用ではスキーマ準備が必要です。

---

今後の予定（例）
- テストカバレッジの追加（ユニット / 統合テスト）
- ExecutionEngine の監視・監督機能の強化（ウォッチドッグ・自動再起動）
- ニュースNLP の非同期化・バッチ最適化、およびレスポンス検証の強化
- ファクター計算のパフォーマンス最適化（DuckDB クエリ改善）

最新の変更はこのファイルに随時追記します。
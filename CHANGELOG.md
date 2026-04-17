Keep a Changelog
=================

すべての重要な変更はこのファイルに記載します。本ファイルは「Keep a Changelog」形式に準拠します。

0.1.0 - 2026-04-17
-----------------

Added
- 基本リリース: KabuSys v0.1.0 を初版公開。
- エントリポイント / 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（デフォルト: data/paper_trading.db）を使用することで本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止制御: data/stop_requested.flag による停止検知、実行中エンジンへの安全な停止指示、実行 PID を data/execution.pid に保存する仕組みを用意。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告ログを出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を参照（監視データの永続化を一元化）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py: Settings クラスを導入し、環境変数経由で設定を取得する共通 API を提供。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等のデフォルト値を含むプロパティを備える。
    - PAPER_FILL_MODE のバリデーション（"instant", "partial", "never", "reject"）を実装。
    - KABUSYS_ENV のバリデーション（"development", "paper_trading", "live"）を実装。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込む。OS 環境変数を保護しつつ上書き制御が可能（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - .env パーサは export 形式・クォート・バックスラッシュエスケープ・インラインコメント等に対応する堅牢な実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: score 降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等重・スコア加重の重み計算（全スコア 0 の場合は等重にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）で候補を除外。既存保有のセクター別時価計算に対応。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告を出して 1.0 でフォールバック。
    - 実装内に price 欠損時のフォールバックを将来改善する旨の TODO を注記。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じて発注株数を決定。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的コスト見積りと残差処理を実装。
    - 将来的な銘柄別 lot_size マッピング対応の TODO を注記。
- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターンおよび MA200 乖離を計算（データ不足は None）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算（データ不足は None）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（最新財務レコードの選定ロジックを実装）。
    - DuckDB を用いた SQL ベースの実装で、スキャン範囲にバッファを置きパフォーマンスを配慮。
  - research.feature_exploration
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons のバリデーションあり。
    - calc_ic: スピアマンのランク相関（IC）計算。有効レコードが 3 未満の場合は None。
    - factor_summary / rank: 基本統計量・ランク付けユーティリティを標準ライブラリのみで実装（pandas 等に依存しない設計）。
- AI ニュース NLP
  - ai.news_nlp (ニュースを OpenAI に送って銘柄ごとにスコア化するモジュール)
    - タイムウィンドウの厳密計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）を実装。
    - 記事を銘柄ごとに集約して文字数・記事数でトリムする仕組み（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - OpenAI API（gpt-4o-mini）へ最大 20 銘柄ずつバッチ送信。429/ネットワーク/5xx に対する指数バックオフのリトライ実装案とレスポンス検証、スコアを ±1.0 にクリップする設計を記載。
    - API キー未設定時の ValueError を実装。
    - （注）モジュールの末尾はスニペット切断により未完の可能性あり（処理フロー・DB 書き込み部分は実装途中の可能性を示唆）。
- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・P95 レイテンシなどを算出して PASS/FAIL 判定を出力。
    - デフォルトの DB パスは data/paper_trading.db。--db オプションで上書き可能。
    - 各種クエリは存在しないテーブルに備えて sqlite3.OperationalError を捕捉してフォールバックする堅牢性を備える。
- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定（"high","normal","low"）。権限不足や未サポート OS の場合は警告でスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能を提供。引数バリデーション・権限エラー時のフォールバックあり。
- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定。
  - パッケージ公開用に portfolio / research / tools / ai / monitoring / execution 等の主要 API を __all__ でエクスポート。

Changed
- （初版）特記事項なし。

Fixed
- （初版）特記事項なし。

Deprecated
- （初版）特記事項なし。

Removed
- （初版）特記事項なし。

セキュリティ注記
- OpenAI API キーは環境変数 OPENAI_API_KEY または明示的な引数で渡す必要がある。キーの管理・漏洩防止は運用上の注意が必要。

既知の制限・TODO
- ai.news_nlp モジュールはスニペットが途中で切れているため、最終的な DB 書き込み処理やエラーハンドリングの完全実装を確認する必要あり。
- portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題を将来的に前日終値や取得原価でフォールバックする旨の TODO を残している。
- position_sizing: 銘柄別の単元株数 (lot_size) を将来対応するための拡張 TODO がある。
- run_monitoring/run_execution の停止フラグはファイルベース（data/stop_requested.flag）に依存しているため、複数ノード間の同期やより洗練されたオーケストレーションが必要な場合は別途仕組みを導入すること。

補足（運用メモ）
- 環境変数関連:
  - KABUSYS_ENV: development | paper_trading | live（正しい値でない場合は起動時に例外）。
  - MONITOR_POLL_INTERVAL: 正の整数（秒）。不正値は警告して 60 秒にフォールバック。
  - PAPER_FILL_MODE: instant | partial | never | reject（不正値は例外）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードをスキップ可能（テスト向け）。
- DB:
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を参照。
  - Paper Trading は settings.paper_sqlite_path（デフォルト data/paper_trading.db）で本番 DB から完全に分離。

今後のリリースで追加検討する項目（例）
- ai.news_nlp の完全実装・ユニットテスト・API レート制御の改善。
- position_sizing の銘柄別 lot_map と単元サイズの DB マスター連携。
- 分散実行環境向けの停止/制御手段（ファイルフラグからメッセージキュー等へ）。
- DuckDB クエリのパフォーマンス監視とインデックス（マテリアライズ）導入検討。

--- 
記載内容はソースコードの実装・コメントから推測してまとめたものです。実際の変更履歴（コミット履歴等）がある場合はそちらを正として合わせて更新してください。
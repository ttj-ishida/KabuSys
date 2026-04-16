# Changelog

すべての変更は Keep a Changelog に準拠しています。  
記載日: 2026-04-16

## [0.1.0] - 2026-04-16

Added
- 初期リリースとしてコア機能を実装。
- 実行/監視用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - Engine をスレッドで実行し、プロジェクトルート配下の data/stop_requested.flag を検知して安全に停止可能。
    - 実行中の PID を data/execution.pid に記録する仕組み（pid_file 指定）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きをサポート（デフォルト 60 秒、1秒未満や不正値はデフォルトへフォールバック）。
    - 監視は環境に関係なく本番用 sqlite_path を使用して監視テーブルを管理。
    - data/stop_requested.flag による停止制御をサポート。
- 設定管理（Settings / .env 自動読み込み）
  - Settings クラスで環境変数を型変換・バリデーション付きで提供（env 判定、log_level、各 DB パス等）。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を基準）し、.env / .env.local を自動ロード（OS 環境変数を保護、.env.local は上書き）。
  - .env パーサーは export 形式やクォート／エスケープ、インラインコメントを考慮して安全に読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能（テスト用）。
  - PAPER_FILL_MODE の検証（有効値: "instant"|"partial"|"never"|"reject"）を追加。
  - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）のデフォルトと expanduser 処理を追加。
- ポートフォリオ構築ライブラリ（pure function 群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順＋signal_rank によるタイブレークで候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター別上限（max_sector_pct）に基づく候補除外ロジック。既存ポジションの時価を集計して超過セクターをブロック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio.position_sizing
    - calc_position_sizes: 複数の配分方式（"risk_based", "equal", "score"）に対応した発注株数決定ロジックを実装。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）超過時のスケーリングと端数配分アルゴリズムを実装。
    - cost_buffer によりスリッページ／手数料を保守的に見積もる扱いをサポート。
- 監視用 DB 初期化ユーティリティ
  - monitoring.monitoring_db の初期化呼び出しを Execution/Monitoring スクリプトで行い、監視テーブルの存在を保証（冪等）。
- utils/process_priority
  - プロセス優先度設定ユーティリティを追加（Windows と POSIX を吸収）。
  - set_process_priority(level) による優先度設定（"high"|"normal"|"low"）、set_cpu_affinity(cpu_count) による CPU 固定を提供。
  - 権限不足や未サポートプラットフォームでは警告を出して安全にスキップ。
- 研究・リサーチモジュール
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を DuckDB 上で計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金等を計算（true_range の NULL 伝播を正しく扱う）。
    - calc_value: raw_financials から直近財務を取得して PER/ROE を計算。
  - research.feature_exploration
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic / rank / factor_summary: スピアマンによる IC 計算、ランク付け、基本統計量計算を実装。外部依存なしで実行可能。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加（--from / --to / --db オプション）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - P95 計算、各種 SQL クエリで欠損やテーブル未存在に対するフォールバックを実装。
- AI ニュース NLP（下書き/主要処理を追加）
  - ai/news_nlp.py
    - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込む処理を実装（バッチ処理、トークン肥大化対策、スコアクリップ、リトライ戦略、レスポンス検証、部分置換による原子性の確保など設計方針を実装）。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算を追加（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - （注）ファイル末尾で処理が途中で切れている箇所あり（実装継続の余地あり）。
- パッケージ初期化
  - kabusys.__init__.py に __version__ = "0.1.0" を追加。主要モジュールの __all__ 定義。

Changed
- DB 接続ポリシー
  - run_monitoring は環境（KABUSYS_ENV）に関係なく常に production 用 sqlite_path を使用（監視データは本番 DB に記録する想定）。
  - run_execution は KABUSYS_ENV が paper_trading の場合に paper_sqlite_path を使用して本番 DB と明確に分離。
- .env ロードの優先順位と保護
  - OS 環境変数を保護しつつ .env/.env.local をロードする仕様を導入（.env.local が上書き）。自動ロード無効化オプションを追加。

Fixed
- .env のパースの堅牢性向上
  - export プレフィックス、クォート内のエスケープ、インラインコメントの扱いなどを正しく処理するよう改善。
- レポート/集計処理の欠損ハンドリング強化
  - paper_verification_report: テーブル未作成やデータ不足時に OperationalError を捕捉してフォールバックするように修正。
  - research モジュール、position_sizing などで price 欠損時のスキップやログ出力を追加して安全性を向上。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キー取り扱い
  - ai/news_nlp の API キーは明示的に引数または環境変数 OPENAI_API_KEY で提供する必要がある旨を明記（未設定時はエラー）。API キー管理は運用で適切に行ってください。

Notes / Migration
- MONITOR_POLL_INTERVAL
  - 環境変数に設定する場合は整数（1 以上）を指定してください。不正値や 0/負数は 60 秒（デフォルト）にフォールバックします。
- PAPER_FILL_MODE
  - Paper Trading の振る舞いを切り替える環境変数は "instant"|"partial"|"never"|"reject" のいずれかでなければなりません。不正値は ValueError を発生させます。
- .env 自動ロード
  - デフォルトでプロジェクトルートの .env / .env.local を自動読み込みします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境等で有用）。
- AI モジュール
  - ai/news_nlp は設計上リトライ・バリデーション等を組み込んでいますが、ネットワークや API のレイテンシによる挙動は運用での検証が必要です。またファイルの一部が未完了の箇所があるため、使用前に実装の完了確認を推奨します。
- lot_size 将来的拡張
  - position_sizing は現在全銘柄共通の lot_size を受け取る実装。将来的に銘柄別 lot_map を受け取る拡張を想定した TODO コメントがあります。

今後の予定（短期）
- ai/news_nlp の残り処理（記事フェッチ、OpenAI 送信、DB 書き込みロジック）の完成とテスト追加。
- E2E テスト／ユニットテストの整備（research, portfolio, execution 等）。
- DuckDB の操作に関するパフォーマンスチューニングとメモリ使用量監視。
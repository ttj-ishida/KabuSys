Keep a Changelog に準拠した CHANGELOG.md（日本語）
（コードベースから実装内容を推測して作成しています）

すべての注目すべき変更をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-13
-------------------

### Added
- 基本パッケージ初期実装: kabusys ライブラリ（__version__ = 0.1.0）。
  - パッケージ構成: data, strategy, execution, monitoring 等のモジュールをエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）による .env 自動読み込み（.env → .env.local。OS 環境変数は保護）。
  - .env パーサー実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォート無しでは '#' の直前が空白またはタブのときコメントと判定）
  - 必須環境変数取得用の _require() と各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
  - 各種検証ロジックを実装:
    - KABUSYS_ENV の有効値チェック（development, paper_trading, live）
    - LOG_LEVEL の有効値チェック
    - PAPER_FILL_MODE の有効値チェック（instant, partial, never, reject）
  - DB パスや PID / kill flag 等の設定プロパティを提供。

- 実行エントリ / 実運用監視
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用して本番 DB と分離。
    - ExecutionEngine 組み立て: BrokerClientFactory、OrderRepository、OrderManager、RiskManager（RiskConfig）、Reconciler、ExecutionEngine を統合してセッション実行。
    - duckdb 接続を渡して分析用ストアを利用。
  - 監視ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下・非整数）は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - SystemMonitor の初期化（SQLite/ DuckDB 接続、pid_file 指定）と check_once() の周期実行、例外時のログ／継続処理、KeyboardInterrupt による終了処理を実装。

- 監視 DB 初期化ユーティリティ（monitoring_db 初期化呼び出しを起動スクリプトで実行）により監視テーブルの存在を冪等に保証。

- プロセス優先度 / CPU アフィニティユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収して set_process_priority(level) を実装。アクセス権や非対応環境では警告を出して安全にスキップ。
  - set_cpu_affinity(cpu_count) を追加（None は何もしない）。利用可能コア数を超える指定は全コア使用へフォールバック。権限不足や未実装 API の場合は警告を出してスキップ。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 銘柄選定 / 重み計算（portfolio_builder）
    - select_candidates(): score 降順、同点は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights(): 等金額配分。
    - calc_score_weights(): スコア正規化（全銘柄のスコアが 0 の場合は等金額へフォールバック、警告あり）。
  - セクター集中制限・レジーム乗数（risk_adjustment）
    - apply_sector_cap(): 既存保有のセクター別時価を計算し、max_sector_pct を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier(): market regime に応じた乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - ポジションサイジング（position_sizing）
    - calc_position_sizes(): allocation_method に応じた発注株数計算を実装（risk_based / equal / score）。
    - risk_based: risk_pct, stop_loss_pct を使って単銘柄ごとのベース株数算出。
    - equal/score: 重みに基づく割当、max_position_pct（1 銘柄上限）を考慮。
    - lot_size（デフォルト 100）で丸め、cost_buffer を考慮して保守的に見積もり、available_cash 超過時はスケールダウンして再配分（端数は lot 単位で残差順に配分）。
    - 価格欠損（price <= 0）時はスキップして安全に動作。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum(): mom_1m/3m/6m と 200 日移動平均乖離率を計算。データ不足時に None を返す。
    - calc_volatility(): 20 日 ATR（true range 実装）、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range は high/low/prev_close のいずれかが NULL の場合 NULL とする。
    - calc_value(): raw_financials から最新財務データを結合して PER（EPS 有効時）と ROE を計算。
    - DuckDB（prices_daily / raw_financials）を SQL で効率的に参照して実装。
  - feature_exploration:
    - calc_forward_returns(): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。horizons の妥当性チェック（正の整数かつ <=252）。
    - calc_ic(): factor と forward return を code で結合して Spearman ランク相関（IC）を計算。有効レコード < 3 の場合は None。
    - rank(), factor_summary(): ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を実装。外部ライブラリ非依存（標準ライブラリのみ）。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news テーブルを OpenAI（gpt-4o-mini）に渡して銘柄別センチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込むワークフローを実装。
  - 実装の主な仕様:
    - ニュース収集ウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（内部は UTC で前日 06:00 ～ 23:30）。
    - 1 銘柄あたり最大記事数と文字数でトリム（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - 最大 20 銘柄ごとのバッチ送信（_BATCH_SIZE=20）。
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフで最大 _MAX_RETRIES 回リトライ。
    - レスポンスは厳密な JSON（{"results":[{"code":"XXXX","score":0.0},...]}）で検証、スコアを ±1.0 にクリップ。
    - 部分失敗時のデータ保護のため、書き込みは対象コードだけを削除して置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決し、未設定時は ValueError。
    - 処理はフェイルセーフで、API 失敗時はスキップして継続可能な設計。

- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から統計を集計して標準出力にレポートを生成。
  - 指標:
    - 稼働率（system_status）: THRESHOLD_UPTIME_PCT = 99.0%（PASS 条件）
    - 注文成功率（trade_logs の Created/Filled）: THRESHOLD_FILL_RATE_PCT = 90.0%
    - 送信率（Created/Sent）: THRESHOLD_SEND_RATE_PCT = 95.0%
    - レイテンシ P95: THRESHOLD_P95_LATENCY_MS = 200 ms
    - リスク却下数（risk_logs）
  - P95 計算実装（空リストは None）、各種 SQL クエリは日付フィルタ対応（ISO8601 UTC 文字列に変換）。
  - コマンドライン引数 --from / --to / --db をサポート。

### Fixed
- 起動時の監視ループおよび ExecutionEngine 起動において、使用中の SQLite/DuckDB 接続のクローズ処理を finally 節で確実に行うように実装（リソースリーク防止）。

### Known issues / TODO
- position_sizing の apply_sector_cap で price が欠損（0.0）の場合、エクスポージャーが過小見積もりされる可能性がある（コメントで将来的に前日終値や取得原価等のフォールバックを検討）。
- AI ニュース処理の続きを示すコード断片が途中で切れている（提示されたスナップショットの終端）。本番運用に向けてはレスポンスバリデーション周りや DB 書き込みトランザクションの詳細実装を確認すること。
- process_priority の権限不足時の挙動はログでスキップするが、ユーザへ明示的な回復策のドキュメント（例えば setcap 等）を追加する余地あり。

その他
-----
- この CHANGELOG はコードベースの内容から実装意図・仕様を推測して作成しています。実際のコミット履歴や PR 単位の粒度での記録（追加・変更・修正の詳細）はバージョン管理履歴に基づいて作成することを推奨します。
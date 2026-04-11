Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは、"Keep a Changelog" の慣習に従います。  

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

変更履歴
-------

### [0.1.0] - 2026-04-11

追加 (Added)
- 基本パッケージ情報を追加
  - パッケージバージョンを __version__ = "0.1.0" として導入。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実稼働用の sqlite_path を常に使用する設計。
    - プロセス優先度を起動時に "high" に設定する処理を追加。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組立て後に ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
- 設定管理
  - config.py: 環境変数と .env 自動読み込み機能を実装。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサーは export 形式、クォート付き値、インラインコメントの扱いに対応。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視閾値、環境種別等）をプロパティで取得。値検証を実施（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
    - デフォルト DB パス: DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db、PAPER_TRADING_SQLITE_PATH=data/paper_trading.db。
    - 各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）は必須チェックを提供（未設定時に ValueError）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択（signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分の重み計算（スコア全体が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限による候補除外ロジック（売却予定銘柄をエクスポージャー計算から除外可能）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。損切り率・リスク率・単元株（lot_size）丸め・コストバッファ・aggregate cap によるスケールダウンに対応。価格欠損時の扱いや端数再配分ロジックを実装。
  - portfolio/__init__.py: 上記関数群をパブリック API としてエクスポート。
- 研究（Research）モジュール
  - research/factor_research.py
    - calc_momentum: 1m/3m/6m リターン、MA200 乖離（必要行数未満は None）を DuckDB の prices_daily 参照で計算。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、当日出来高比を計算（データ不足時は None）。
    - calc_value: raw_financials と prices_daily を組合せて PER / ROE を計算（EPS が 0／欠損時は None）。
    - いずれも DuckDB 接続を受け、外部 API に依存しない実装。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターン（fwd_1d / fwd_5d / fwd_21d 等）を計算。horizons のバリデーションあり。
    - calc_ic / rank / factor_summary: スピアマンランク相関（IC）の計算、ランク変換、ファクター統計サマリを提供。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research/__init__.py: 主要ユーティリティをエクスポート（zscore_normalize を含む）。
- AI 関連
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を行い、銘柄ごとに記事を集約。1 銘柄あたりの最大記事数／文字数を制限してトークン肥大化に対応。
    - 1 リクエストで最大 20 銘柄をバッチ処理。429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフで再試行。その他エラーはフェイルセーフでスキップ。
    - レスポンス検証を厳格に行い、スコアを ±1.0 にクリップ。書き込みは該当コードのみ DELETE → INSERT で置換（部分失敗で既存データを保護）。
    - OPENAI_API_KEY が未設定の場合は ValueError を送出。
  - ai/regime_detector.py
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等的に書き込む。
    - prices_daily クエリは target_date 未満データのみを使用しルックアヘッドを防止。マクロ記事がない場合は macro_sentiment=0.0 で継続。
    - OPENAI_API_KEY が必要（api_key 引数または環境変数）。
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX（Linux, macOS, FreeBSD）を吸収してプロセス優先度（high/normal/low）を設定。権限不足や未対応環境では警告ログを出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 固定。引数検証・例外ハンドリングあり。
- DB 初期化ユーティリティ
  - monitoring/monitoring_db.init_monitoring_db を run_execution/run_monitoring 起動時に呼び出し、監視用テーブルが存在することを保証（冪等）。
- ロギング
  - 起動スクリプトは logging.basicConfig(level=logging.INFO) をデフォルトで設定し、各モジュールは適切な情報／警告／例外ログ出力を行う設計。
- 依存
  - DuckDB（duckdb）、psutil、openai クライアント、sqlite3 を利用。

変更 (Changed)
- なし（初回リリース）。

修正 (Fixed)
- なし（初回リリース）。

削除 (Removed)
- なし（初回リリース）。

注記 (Notes)
- 環境変数の重要な一覧（主なもの）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY
  - KABUSYS_ENV（development / paper_trading / live）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60。無効値はデフォルトにフォールバック）
  - PAPER_FILL_MODE（paper_trading の MockBrokerClient 動作モード: instant | partial | never | reject）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（=1 で .env 自動ロードを無効化）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- AI 機能（news_nlp / regime_detector）は OpenAI API を利用するため API キーが必要。API 呼び出しに失敗してもフェイルセーフで継続するよう設計されているが、スコア未取得となる可能性あり。
- DuckDB の executemany に関する注意点: 空パラメータの executemany は互換性のため事前チェックを行っている。
- Research / AI モジュールはルックアヘッドバイアス対策として date.today()/datetime.today() を直接参照しない設計になっている（target_date を明示的に渡す）。

移行 / 利用ガイド（簡易）
- 開発環境で .env/.env.local を利用する場合、プロジェクトルートに配置すると自動で読み込まれる（ただし OS 環境変数が優先される）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading 環境で実行するには KABUSYS_ENV=paper_trading を設定。実際の発注はモックブローカーに切り替わり、専用 DB に記録されます。
- AI 関連処理を利用する場合は OPENAI_API_KEY を設定してください。設定がない場合は score_news や regime 判定の API 呼び出しが失敗します（score_news は例外を投げる設計）。
- 監視ループのポーリング間隔を調整したい場合は MONITOR_POLL_INTERVAL を設定（整数秒）。1 未満や不正な値はログ警告の上でデフォルト 60 秒にフォールバックします。
- システム優先度設定は起動直後に行われます。環境により権限が必要な場合があるため、権限不足時はログに警告が出ますが処理は継続します。

開発上の注目点（設計・拡張の余地）
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map を受け取る拡張を想定。
- sector_exposure 計算で価格が欠損した場合のフォールバック（前日終値や取得原価）の扱いは TODO コメントあり。
- OpenAI 呼び出しはニュース NLP とレジーム判定で似たリトライロジックを持つため、将来的に共通ユーティリティへ抽出可能。

---

このリリースは初回の主要機能群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助機能、設定管理、プロセスユーティリティ）を含みます。今後のリリースではテストカバレッジ強化、個別単元株サイズ対応、外部データのフォールバック処理などを予定しています。
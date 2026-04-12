KEEP A CHANGELOG — 変更履歴
すべての注目すべき変更はここに記載します。  

フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-12

Added
- 基本アプリケーションの初期リリース（バージョン 0.1.0）。
- 起動スクリプト
  - run_monitoring.py を追加。
    - SystemMonitor のポーリングループを起動する実行スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や数値以外）はデフォルトにフォールバックし、警告を出力。
    - 監視は環境にかかわらず本番の sqlite_path を使用する（Settings.sqlite_path）。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py を追加。
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - kabusys.config.Settings を導入。
    - .env 自動読み込み機能（プロジェクトルート探索: .git or pyproject.toml 基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env と .env.local の読み込み順序、OS 環境変数保護（protected）に対応。
    - .env パーサの強化: export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いを実装。
    - 各種環境変数プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH 等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）。
    - ログレベル検証（LOG_LEVEL）。
    - 監視用ファイルパス（PID_FILE_PATH / KILL_FLAG_PATH）や各種しきい値（CPU/MEMORY/DISK）をプロパティ化。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates(): BUY シグナルのスコア降順ソート（タイブレーク: signal_rank 昇順）。
    - calc_equal_weights(), calc_score_weights(): 等配分およびスコア加重配分。スコア全てが 0 の場合は等金額配分にフォールバックして WARNING を出力。
  - risk_adjustment.py
    - apply_sector_cap(): セクター集中上限チェック（既存保有のエクスポージャー計算、売却予定銘柄の除外、"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier(): market レジームに応じた投下資金乗数（bull/neutral/bear）。
  - position_sizing.py
    - calc_position_sizes(): allocation_method に応じた発注株数計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）スケールダウン、cost_buffer による保守的見積り等を実装。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research.py
    - calc_momentum(): 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily から計算。
    - calc_volatility(): ATR20、相対 ATR、20日平均売買代金、出来高指標を計算。
    - calc_value(): raw_financials から EPS/ROE を取得して PER/ROE を計算。
    - DuckDB を用いる設計、営業日（連続レコード）ベースでの窓処理を採用。
  - feature_exploration.py
    - calc_forward_returns(): 将来リターン（指定ホライズン）を計算。horizons バリデーションあり（1〜252 範囲）。
    - calc_ic(): スピアマンのランク相関（IC）を計算。レコード不足（<3）で None を返す。
    - rank(), factor_summary(): ランク変換（同順位は平均ランク）、基本統計量サマリー（count/mean/std/min/max/median）。外部依存（pandas 等）を使わない実装。
  - research パッケージの __all__ を整備（zscore_normalize のエクスポート含む）。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を追加。
    - ニュース集計ウィンドウ（JST 前日 15:00 〜 当日 08:30）を計算する calc_news_window() 実装。
    - target_date に対する raw_news と news_symbols を集約し、銘柄ごとに記事トリム（最大記事数・最大文字数）を実行。
    - バッチサイズ (_BATCH_SIZE=20)、最大リトライ回数、指数バックオフ等の仕組みを実装。
    - API レスポンスのバリデーション、スコアを ±1.0 にクリップ、DuckDB の ai_scores テーブルへの安全な書き込み（部分失敗時に他銘柄を保護する方式）を想定。
    - API キー未設定時は ValueError を発生。
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX（Linux, Darwin, FreeBSD）で抽象化された優先度設定を実装（psutil ベース）。対応しない OS はログでスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン止めする機能。引数検証とアクセス拒否時の警告ハンドリングあり。
- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を実装。
    - --from / --to / --db オプションで期間・DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数も併用可。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどを計算して PASS/FAIL を出力する。
    - デフォルトの合格基準（しきい値）を定義（稼働率 99%、成功率 90%、送信率 95%、P95 200 ms）。
    - DB が存在しない場合・テーブルがない場合に適切に N/A や 0 を扱うフェールセーフ実装。

Changed
- パッケージ初期化
  - kabusys.__init__.py にバージョン情報 __version__ = "0.1.0" を追加。
- DB 初期化
  - run_execution.py と run_monitoring.py は起動時に init_monitoring_db() を呼び出して監視テーブルの存在を保証（冪等）。

Fixed
- .env パース周りの堅牢化
  - export キーワード対応、クォート内のバックスラッシュエスケープ対応、インラインコメント判定の改善などを行い、実運用時の .env 設定に耐える仕様に。

Notes / Important behavioral details
- run_monitoring は環境（KABUSYS_ENV）によらず Settings.sqlite_path（本番 sqlite_path）を使用して監視情報を記録します。開発や paper_trading 実行時に監視データを分離したい場合は注意してください。
- run_execution は paper_trading の場合、paper_sqlite_path（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して発注ログ等を本番 DB と分離します。
- OpenAI 連携機能（ai.news_nlp）は API キーを必須とします（api_key 引数または OPENAI_API_KEY 環境変数）。API コールの失敗時はリトライ・フェイルセーフを行う設計ですが、API 使用料・レート制限に注意してください。
- research モジュールは DuckDB の prices_daily/raw_financials テーブルに依存します。足りないデータは None として扱われるため、事前に DuckDB に必要データをロードしてください。
- process_priority/set_cpu_affinity は権限やプラットフォームにより動作しない場合があり、その場合は警告ログを出してスキップします。

Security
- 重要なシークレットは .env ファイルまたは OS 環境変数で管理すること。自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入しています。

Acknowledgements
- 本リリースは初期実装群のまとめです。今後はテスト・ドキュメント・細かなエラーハンドリング・部分的な API 応答検証の強化を予定しています。

（この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリース日付はプロジェクト管理者の記録に従って調整してください。）
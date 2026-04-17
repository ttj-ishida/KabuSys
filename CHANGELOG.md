Keep a Changelog に準拠した CHANGELOG.md を以下に作成しました。コードベースの実装内容から推測して記載しています。必要なら項目の追加・修正を行います。

CHANGELOG.md
=============
すべての注記は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に従っています。

Unreleased
----------
- なし

0.1.0 — YYYY-MM-DD
------------------
（初回リリース想定。パッケージ __version__ = 0.1.0 に対応）

Added
- 基本アプリケーション構成
  - パッケージ初期化とバージョン設定（kabusys.__version__ = "0.1.0"）。

- 設定管理（kabusys.config）
  - .env / .env.local 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml）。
  - 行パーサ実装によりクォート付き値、export プレフィックス、インラインコメントの扱いに対応。
  - Settings クラスを提供し、各種環境変数（J-Quants / kabu API / LINE / DB パス /監視閾値 等）をプロパティとして取得・検証。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化の対応。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等のバリデーション。

- 実行系スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト。BrokerClientFactory によるブローカクライアント生成。
    - paper_trading 環境向けに paper_sqlite_path を使用して本番 DB と分離。
    - OrderRepository、OrderManager、RiskManager（RiskConfig）、Reconciler 組立て。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）による停止制御。
    - スレッド化されたエンジン実行と安全な停止処理。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB 初期化（init_monitoring_db）、duckdb 接続。
    - 停止フラグ検知によるループ終了、例外時のログ保護。

- 監視・運用ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI。
    - 稼働率（system_status）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、レイテンシ（P95 を含む）等を集計して標準出力に判定（PASS/FAIL）を出力。
    - 日付フィルタ (--from/--to)、DB パス (--db または PAPER_TRADING_SQLITE_PATH) を指定可能。
    - テーブルが存在しない場合に備え sqlite3.OperationalError をキャッチして耐性を持たせている。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順の候補選定（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。全スコアが 0 の場合は等分配へフォールバックし警告を出す。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター別エクスポージャー算出と候補除外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") による資金乗数。未知レジームはログを出してフォールバック。
  - position_sizing:
    - calc_position_sizes: 重み・候補・口座情報から発注株数計算（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリング処理を実装。スケールダウン時に残余キャッシュでの端数調整ロジックあり。

- リサーチモジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（DuckDB SQL ベース）。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 扱いに注意。
    - calc_value: 最新財務データ（raw_financials）と当日株価から PER / ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンをまとめて取得。入力検証（horizons の範囲等）あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算し、データ不足時に None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量サマリー（count/mean/std/min/max/median）を実装。
  - DuckDB 接続を受け取り prices_daily / raw_financials のみ参照する設計（本番 API への依存なし）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメントを -1.0〜1.0 でスコア化して ai_scores に書き込む処理を実装。
  - 処理の要点:
    - ニュース収集ウィンドウの計算（JST ベースを UTC に変換）。
    - 1 銘柄あたりの記事数・文字数上限（トリム）を設定してトークン増大を抑制。
    - バッチ送信（最大 20 銘柄 / リクエスト）、429/タイムアウト/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ。
    - 失敗しても他銘柄の既存スコアを保護するため、書き込みは対象コードを絞って置換。
    - ルックアヘッドバイアス防止のため datetime.today() 等を参照しない実装方針。

- ユーティリティ（kabusys.utils）
  - process_priority:
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）を吸収してプロセス優先度（high/normal/low）を設定。権限不足や未対応 OS は警告ログでスキップ。
    - set_cpu_affinity: 最初の N コアに固定（利用可能コア数より大きい指定は全コア利用にフォールバック）。引数検証あり。

Changed
- ログとデフォルト設定
  - run_* スクリプトで起動時に logging.basicConfig(level=logging.INFO) を設定し、起動環境（KABUSYS_ENV）を INFO ログで出力するようにした。

Fixed / Hardening
- run_monitoring のポーリング間隔取得処理で MONITOR_POLL_INTERVAL の不正値（0 以下や非数）を検出してデフォルトにフォールバックし、time.sleep に渡してクラッシュすることを防止。
- DuckDB / SQLite を使う各処理で DB 初期化や接続後にテーブル未存在による例外に耐性を持たせ、ツールが存在しない DB でも致命的にならないようにした（paper_verification_report の例外ハンドリングなど）。
- portfolio.calc_score_weights: 全銘柄スコアが 0 の場合のフォールバックと警告を実装（数値ゼロ割り回避）。
- factor_research / feature_exploration: パーセンタイル・ランク計算等での丸め・同順位処理を考慮して数値精度の問題に対処。
- process_priority: 未対応 OS や権限エラー時にスキップしてプロセスが落ちないように改善。

Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）から解決。未設定時には ValueError を投げて安全に失敗させる設計。

Notes / Known issues
- ai/news_nlp.py の実装は堅牢化を意図した設計が記載されているが、ファイル末尾が断片的に見えるため（本 CHANGELOG はソースから推測して作成）、実運用前に以下を確認してください:
  - API レスポンスのスキーマ検証・例外処理の完全性
  - DuckDB への安全な書き込みフロー（DELETE/INSERT のトランザクション等）
- apply_sector_cap のエクスポージャー計算で price が欠損（0.0）の場合にエクスポージャーが過少見積もられる点は TODO コメントとして残されている。将来的に価格フォールバックを導入することが推奨される。
- position_sizing の将来的拡張として lot_size を銘柄別にする設計がコメントされている（現状は全銘柄共通での単元処理）。

参考
- 各モジュールは「DB 参照のみ（DuckDB / SQLite）」「本番発注 API へ依存しない」ことを設計方針としている箇所が多く、安全にローカル検証や Research 環境での再現が可能です。
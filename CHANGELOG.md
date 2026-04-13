# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。主にコードベースの初期リリース相当の追加・実装内容を、ソースコードから推測してまとめています。

全体方針:
- DuckDB / SQLite を用いたデータ処理、実運用向けの監視・実行スクリプト、ポートフォリオ構築ロジック、リサーチユーティリティ、そして OpenAI を用いたニュース NLP スコアリング機能を含むモジュール群を実装。
- 環境変数読み込み、プロセス優先度・CPU affinity 設定、Paper Trading 用のサンドボックス化など、実運用を意識した設計がなされています。

Unreleased
- （該当なし）

0.1.0 - 初回リリース
----------------------------------------

Added
- パッケージ情報
  - 初期バージョンを設定（kabusys.__version__ = "0.1.0"）。 (src/kabusys/__init__.py)

- 環境設定管理（堅牢な .env 自動読み込みと検証）
  - プロジェクトルート自動検出ロジックを実装 (.git または pyproject.toml を探索)。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。 (src/kabusys/config.py)
  - .env / .env.local の読み込み機構を実装し、export prefix、引用符付き値、インラインコメント、上書き制御（protected set による OS 環境変数保護）に対応。 (src/kabusys/config.py)
  - アプリ設定を Settings クラスとして整理。主要な設定はプロパティ経由で取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, PAPER_FILL_MODE 等）。値検証・デフォルトの提供を行う。 (src/kabusys/config.py)
  - 主要な環境変数:
    - KABUSYS_ENV (development / paper_trading / live)
    - MONITOR_POLL_INTERVAL（監視ポーリング間隔を上書き可能, デフォルト60秒）
    - PAPER_FILL_MODE（paper_trading 用の fill 動作検証モード）
    - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 SQLite パス）
    - SQLITE_PATH / DUCKDB_PATH / PID_FILE_PATH / KILL_FLAG_PATH / その他

- 実行系起動スクリプト
  - ExecutionEngine 起動スクリプトを実装。Paper Trading 環境（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、Paper 専用 SQLite（data/paper_trading.db など）に記録することで本番 DB と分離。 (src/kabusys/run_execution.py)
  - 起動時にプロセス優先度を "high" に設定する処理を追加。 (src/kabusys/run_execution.py)

- 監視（Monitoring）起動スクリプト
  - SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用して記録。 (src/kabusys/run_monitoring.py)
  - _get_poll_interval 関数で不正な値（0 以下や非数字）を検出した際にログ警告を出しデフォルトへフォールバック。

- プロセス関連ユーティリティ
  - set_process_priority(level) を実装。Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収し、プラットフォーム非依存の呼び出しインターフェイスを提供。アクセス権限や未対応 OS の場合は警告を出してスキップ。 (src/kabusys/utils/process_priority.py)
  - set_cpu_affinity(cpu_count) を追加し、カレントプロセスの CPU affinity を最初の N コアに固定できる。制限超過や権限エラーはログに記録してスキップ。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定 / 重み計算
    - select_candidates: スコア降順で候補選定（同点は signal_rank でブレーク）。 (src/kabusys/portfolio/portfolio_builder.py)
    - calc_equal_weights / calc_score_weights: 等分配・スコア比率配分。スコア合計が 0 の場合に等配分へフォールバックし警告を出す。 (src/kabusys/portfolio/portfolio_builder.py)
  - セクター制約・レジーム乗数
    - apply_sector_cap: 既存ポジションのセクター比率が指定上限を超えるセクターの新規候補を除外。unknown セクターは制約対象外。売却予定銘柄（sell_codes）をエクスポージャー計算から除外。 (src/kabusys/portfolio/risk_adjustment.py)
    - calc_regime_multiplier: 市場レジーム（"bull" / "neutral" / "bear"）に応じた投下資金乗数を返す。未知レジームは 1.0 にフォールバックし警告。 (src/kabusys/portfolio/risk_adjustment.py)
  - 株数決定・リスク制限・単元丸め
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応。単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）を考慮してスケーリングする。コストバッファ(cost_buffer)を用いて保守的に見積もりスケールダウンを行うアルゴリズムを実装。 (src/kabusys/portfolio/position_sizing.py)
  - 上記関数群を package export に追加。 (src/kabusys/portfolio/__init__.py)

- リサーチ / ファクター計算
  - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily から計算。ウィンドウ不足時は None を返す。 (src/kabusys/research/factor_research.py)
  - calc_volatility: 20日 ATR（true_range を正しく扱う）、20日平均売買代金、出来高比を計算。データ不足は None。 (src/kabusys/research/factor_research.py)
  - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0 または NULL の場合は PER を None）。 (src/kabusys/research/factor_research.py)
  - calc_forward_returns: 任意ホライズンの将来リターンを一度のクエリで取得。horizons のバリデーションあり。 (src/kabusys/research/feature_exploration.py)
  - calc_ic / rank / factor_summary: IC（スピアマンのランク相関）計算、ランク化（同順位は平均ランク）、および各ファクターの統計サマリー（count/mean/std/min/max/median）を実装。浮動小数の丸め誤差対策あり。 (src/kabusys/research/feature_exploration.py)
  - research パッケージの public API を整備（zscore_normalize を含む）。 (src/kabusys/research/__init__.py)

- Paper Trading 検証ツール
  - paper_verification_report: Paper Trading DB を読み、システム稼働率・注文成功率・送信率・P95 レイテンシなどを集計して人間向けの検証レポートを CLI で出力。日付フィルタ（--from / --to）対応、閾値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を実装。P95 は簡易的にパーセンタイルを計算。DB テーブルが存在しない場合は N/A を扱う。 (src/kabusys/tools/paper_verification_report.py)

- ニュース NLP（AI）モジュール
  - ai/news_nlp.py: raw_news と news_symbols を集約し、OpenAI API（gpt-4o-mini を想定）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（target_date に対し、前日 15:00 JST 〜 当日 08:30 JST を対象）を提供（calc_news_window）。 (src/kabusys/ai/news_nlp.py)
    - 1 銘柄あたりの記事数 / 文字数のトリム（トークン肥大化対策）、1 回に最大 20 銘柄でチャンク処理、429/ネットワーク/5xx 等に対する指数バックオフリトライ、レスポンスの厳密な JSON 検証、スコアを ±1.0 にクリップする等のフェールセーフを実装。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。 (src/kabusys/ai/news_nlp.py)

Changed
- なし（初回リリースに伴う新規実装が主）

Fixed / Robustness improvements
- env パーサーの堅牢性向上:
  - export プレフィックス対応、引用符内でのバックスラッシュエスケープ処理、インラインコメントの扱い（引用符外かつ '#' の直前が空白またはタブのときのみ）など、実運用でありがちな .env 記法の変化に耐えうる実装に。 (src/kabusys/config.py)
- ポーリング間隔取得の堅牢化:
  - MONITOR_POLL_INTERVAL が非整数または 0 以下の場合に警告ログを出してデフォルト値にフォールバック。time.sleep に渡せる整数を保証。 (src/kabusys/run_monitoring.py)
- DuckDB/SQLite 接続周り:
  - 各起動スクリプトでの DB 初期化呼び出し（init_monitoring_db）を冪等に行い、監視テーブルの存在を保証するようにした。 (src/kabusys/run_execution.py, src/kabusys/run_monitoring.py)

Notes / Migration / 使用上の注意
- Monitoring と Execution の DB の分離:
  - run_monitoring は常に Settings.sqlite_path（本番監視 DB）を使用する設計になっています。一方 run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用して本番 DB と完全に分離します。 (src/kabusys/run_monitoring.py, src/kabusys/run_execution.py)
- .env 自動読み込み:
  - デフォルトでプロジェクトルートの .env / .env.local を読み込みますが、テストか CI 等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。 (src/kabusys/config.py)
- OpenAI の利用:
  - ai/news_nlp.score_news は OPENAI_API_KEY（または api_key 引数）必須。API 呼び出しにはレート制限やネットワーク障害が発生するため、リトライ・バックオフの挙動が組み込まれているものの、実運用では API キー管理とコスト管理に注意してください。 (src/kabusys/ai/news_nlp.py)
- 実行時優先度:
  - run_monitoring/run_execution 起動時にプロセス優先度を "high" に設定しようとします。権限不足の場合は警告が出て処理は継続されます。 (src/kabusys/run_monitoring.py, src/kabusys/run_execution.py, src/kabusys/utils/process_priority.py)
- Paper Trading の挙動:
  - PAPER_FILL_MODE（instant/partial/never/reject）を環境変数で制御できます。無効値が設定された場合は ValueError が発生します。 (src/kabusys/config.py)
- CLI:
  - Paper 検証レポートは python -m kabusys.tools.paper_verification_report で起動できます。--from / --to / --db オプションに対応しています。 (src/kabusys/tools/paper_verification_report.py)

Known limitations / TODO（ソース内コメントより）
- position_sizing の価格欠損時のフォールバック:
  - price が欠損 (0.0) の場合、エクスポージャーが過少見積りされてブロックが外れる可能性がある旨の注意がある。将来的に前日終値や取得原価等のフォールバック価格の導入を検討。 (src/kabusys/portfolio/risk_adjustment.py)
- position_sizing の lot_size の銘柄別対応:
  - 現状は全銘柄共通の lot_size を想定しているが、将来的には銘柄別 lot_map を受け取る設計への拡張予定。 (src/kabusys/portfolio/position_sizing.py)
- ai/news_nlp に関しては OpenAI レスポンスの整合性検証や部分失敗時の局所更新ロジックなど、運用上重要な配慮が多数実装されているが、実稼働前には十分な試験が必要。 (src/kabusys/ai/news_nlp.py)

作者注
- この CHANGELOG は提供されたソースコードを基に推測して作成した初版のリリースノートです。実際の開発履歴（コミット履歴や issue tracker）と異なる可能性があります。必要に応じて項目の追加・修正を行ってください。
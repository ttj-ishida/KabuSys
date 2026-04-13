# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。慣例に従い SemVer を想定しています。

## [0.1.0] - 2026-04-13

### Added
- 全体
  - プロジェクト初期リリース。自動売買／リサーチ／モニタリング周りのコア機能をまとめて追加。
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。

- 設定・環境読み込み (kabusys.config)
  - .env ファイルの自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env/.env.local の読み込み順序とオプション（override/protected）を実装。
  - .env 行パーサ `_parse_env_line` を実装し、export プレフィックス、クォート、エスケープ、インラインコメント等を正しく処理。
  - 必須環境変数取得ヘルパ `_require` を追加。
  - Settings クラスを導入し、各種環境設定（J-Quants / kabu API / LINE / DB パス /監視閾値 /動作環境判定 等）をプロパティ化。
  - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を追加。
  - KABUSYS_ENV の許容値を限定（development, paper_trading, live）し、無効値は ValueError。

- 実行用スクリプト
  - run_execution.py を追加
    - ExecutionEngine 起動スクリプト。起動時にプロセス優先度を設定し、SQLite / DuckDB に接続してエンジンを組み立てて実行する。
    - paper_trading 環境 (`KABUSYS_ENV=paper_trading`) 時は paper 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB から分離。
    - BrokerClientFactory によるブローカー切替、OrderRepository/OrderManager/Reconciler/RiskManager 等の組み立てを行う。
    - RiskConfig 初期値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装し、初期 portfolio value を broker.get_available_cash() から取得して設定。

  - run_monitoring.py を追加
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告の上デフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（モニタリング用 DB は環境で切り替えない）。

- モニタリング DB 初期化ユーティリティ
  - init_monitoring_db による監視テーブルの冪等な初期化処理（run_execution/run_monitoring から利用）。

- プロセス制御ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) を実装して Windows / POSIX 系で適切に優先度を設定。未対応 OS や権限不足時は警告を出してスキップ。
  - set_cpu_affinity(cpu_count) を実装。指定が None の場合は設定しない。利用不可時は警告を出してスキップ。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等配分にフォールバックし警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用して候補を除外するロジック（sell_codes を除外して現保有を計算）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3）。未知レジームは警告の上 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: 複数の配分方式（risk_based, equal, score）に基づいて銘柄ごとの発注株数を計算。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的見積もり、残差処理（fractional remainder に基づく追加配分）を実装。
    - price 欠損時のスキップやデバッグログを追加。

- リサーチ (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB 上の prices_daily から計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を用いて PER / ROE を計算。target_date 以前の最新財務データを参照。
    - 各関数はデータ不足時に None を返すなど堅牢に実装。
  - feature_exploration:
    - calc_forward_returns: target_date から各ホライズン先の将来リターンを計算（horizons のバリデーション付き）。
    - calc_ic: スピアマンランク相関（IC）を実装。レコードが少ない場合は None。
    - rank / factor_summary: ランク変換、基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージのエクスポートに zscore_normalize を追加（kabusys.data.stats から）。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）でバッチセンチメント評価して ai_scores に書き込む処理を実装。
  - 機能:
    - ニュース集計ウィンドウ計算 (前日15:00 JST ～ 当日08:30 JST を UTC で扱う)。
    - 記事の銘柄ごと集約（1銘柄あたり記事数・文字数のトリム）。
    - 最大 20 銘柄/チャンクで API 呼び出し。
    - 429 / ネットワーク / 5xx に対する指数バックオフリトライ（上限回数あり）。
    - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（影響範囲をコードで限定して DELETE→INSERT）。
  - 実装上の注意:
    - API キーが未設定の場合は ValueError を送出。
    - datetime.today()/date.today() を直接参照しない実装でルックアヘッドバイアスを防止。
    - executemany のパラメータが空でないことをチェック（DuckDB の制約回避）。

- ツール (kabusys.tools.paper_verification_report)
  - Paper Trading 検証レポート生成スクリプトを追加。
  - コマンドライン引数で期間指定（--from/--to）や DB パス指定（--db）が可能。
  - 指標:
    - 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。
  - 合格基準（デフォルトの閾値）を設定:
    - 稼働率 >= 99.0%
    - 注文成立率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - DB が存在しない・テーブル欠損時は N/A や 0 を扱って堅牢にレポートを出力。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- 設計上のフェイルセーフ / 防御的実装
  - MONITOR_POLL_INTERVAL に 0 以下や非整数が設定されてもデフォルトにフォールバックし、警告ログを出すように実装（run_monitoring）。
  - プロセス優先度設定 / CPU affinity 設定は権限不足や未対応プラットフォームで例外を吐かないように警告でスキップする実装にした。
  - DuckDB / SQLite を使う処理は接続のクローズを finally で行うなどリソース解放を確実に行う。
  - レポート生成やファクター計算でデータ不足（テーブル・カラムがない等）の場合に sqlite3.OperationalError を捕捉して N/A 扱いや 0 で継続するようにした（paper_verification_report）。

### Security
- OpenAI API キーの取り扱いは引数または環境変数（OPENAI_API_KEY）から解決。未設定時に明示的にエラーを出して漏洩・未意図の呼び出しを防止。

---

注: 上記はソースコードから推測してまとめた CHANGELOG です。個々の実装詳細（関数の引数仕様・戻り値・振る舞い）はそれぞれのモジュールの docstring を参照してください。
CHANGELOG
=========

すべての注目すべき変更点はここに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------
- TODO / 今後の改善予定
  - position_sizing.calc_position_sizes:
    - price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価など）を使う拡張を検討。
    - lot_size を銘柄ごとに指定できる設計への拡張予定（stocks マスタの導入）。
  - apply_sector_cap:
    - "unknown" セクターの取り扱い等、さらに細かなポリシーの追加検討。
  - ai.news_nlp:
    - ファイル途中で切れている箇所の実装完了（記事取得・API コールのチャンク化・DB 書き込み処理の最終化）を予定。

0.1.0 - 2026-04-16
-----------------
Added
- 基本情報
  - パッケージ初期リリース。パッケージバージョンは __version__ = "0.1.0"。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor をポーリングするループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用（監視用 DB を本番 DB と合わせて使用する設計）。
    - 停止フラグ（data/stop_requested.flag）を確認して安全にループ終了。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用に専用の SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成に対応（実運用/モックの切り替え）。
    - ExecutionEngine 実行は別スレッドで行い、停止フラグで安全停止。
    - 起動時にプロセス優先度を "high" に設定。
    - PID 管理（data/execution.pid）や停止フラグチェックを実装。

- 設定管理
  - config.py
    - .env/.env.local 自動ロード（プロジェクトルートの検出: .git または pyproject.toml で判定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化オプション。
    - .env 解析の細かな仕様実装（export 対応、引用符内のバックスラッシュエスケープ、インラインコメント処理等）。
    - Settings クラスを追加し、アプリケーション設定値をプロパティ経由で取得可能に（例: duckdb_path, sqlite_path, PAPER_FILL_MODE の検証、env の検証など）。
    - 各種環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証用レポート生成スクリプトを追加。
    - CLI オプション: --from, --to（日付範囲）、--db（DB パス上書き）。
    - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
    - システム安定性（稼働率）、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）等を集計して出力。
    - 合格/不合格（PASS/FAIL）判定の閾値を定義（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 レイテンシ <=200ms）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比例配分（全銘柄のスコアが 0 の場合は等配分へフォールバック、警告ログ出力）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有比率が閾値を超える場合、新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームはログ警告のうえ 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を計算。
      - allocation_method による振る舞い: "risk_based"（損切り・リスク率ベース）と "equal"/"score"。
      - 単元（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り）等のパラメータをサポート。
      - Aggregate cap（利用可能現金を超える場合のスケーリング）と端数処理（lot_size 単位での再配分）を実装。
      - 価格欠損時はログを出しスキップ。

  - portfolio/__init__.py
    - 上記関数群をパッケージ公開。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX(Linux/Mac/FreeBSD) を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定（None で何もしない）。
    - アクセス権限不足や未対応環境では警告を出してスキップ。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: PER（EPS が有効な場合）と ROE を計算（raw_financials と prices_daily を結合）。
    - DuckDB 接続を受け取り SQL を用いて高効率に計算する設計。

  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括クエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。データ不足（有効レコード < 3）の場合は None を返す。
    - rank / factor_summary: ランク変換・基本統計量集計（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

  - research/__init__.py
    - 主要関数（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）と zscore_normalize を公開。

- AI / ニュース NLP（初期実装）
  - ai/news_nlp.py
    - raw_news をバッチで OpenAI API（gpt-4o-mini を想定）に送りセンチメントスコア（-1.0〜1.0）を生成し、ai_scores テーブルへ書き込む機能の骨格を追加。
    - 仕様:
      - タイムウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST を対象（UTC に変換して DB 比較）。
      - 1 銘柄あたり最大記事数・最大文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 1 API コールで最大 _BATCH_SIZE 銘柄を処理する設計。
      - RateLimit / ネットワーク / 5xx 等に対して指数バックオフでリトライ（上限 _MAX_RETRIES）。
      - レスポンス検証とスコアの ±1.0 クリップ。
      - OpenAI API キーは引数 api_key または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
    - 注: ファイルが途中で切れている箇所があり、記事の集約取得ロジックや DB 書き込み周りは継続実装が必要。

Changed
- 監視と実行の起動動作
  - 監視(run_monitoring)は環境に関係なく監視 DB（Settings.sqlite_path）を使用する設計であることを明確化。
  - 実行(run_execution)は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用するように分離。

Fixed
- .env パーサーの改善
  - export プレフィックス、引用符内のバックスラッシュエスケープ、インラインコメントの扱い等をより正確に処理するよう改良（.env 読み込みの堅牢性向上）。

Security
- OpenAI API キー取扱い
  - news_nlp.score_news は API キーが明示的に設定されていない場合に例外を出すことで、秘密鍵の未設定による誤動作を防止。

Notes / Migration / 注意事項
- 環境変数と .env のロード順
  - OS 環境変数 > .env.local（上書き）> .env（未設定キーのみ）。既存の OS 環境変数は保護されます。
  - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 監視 DB の取り扱い
  - run_monitoring は Settings.sqlite_path を使用します（KABUSYS_ENV にかかわらず）。監視用 DB を別にしたい場合は Settings.sqlite_path を上書きしてください。

- Paper Trading 分離
  - 実行系は paper_trading 環境で paper_sqlite_path を使用し、本番 DB とデータを分離しています。Paper Trading 用の挙動（MockBrokerClient の fill_mode など）は PAPER_FILL_MODE 環境変数で制御できます。

- 未実装 / 注意点
  - ai/news_nlp.py は主要アルゴリズムの設計が記載されていますが、ファイル末尾が途切れており完全実装ではありません。運用前に記事取得・API 呼び出しループ・DB 書込ロジックの完了確認が必要です。
  - position_sizing の価格欠損時の扱いに注意（現状はスキップで過少見積りの可能性あり）。

参考: 主な環境変数
- KABUSYS_ENV (development | paper_trading | live)
- SQLITE_PATH (監視用 DB、デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、デフォルト data/paper_trading.db）
- DUCKDB_PATH（DuckDB ファイル、デフォルト data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒）
- PAPER_FILL_MODE（instant | partial | never | reject）
- OPENAI_API_KEY（news_nlp 用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（1 を設定すると .env 自動ロードを無効化）

以上。
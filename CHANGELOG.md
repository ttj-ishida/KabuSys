# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]
- （未リリースの変更はここに記載）

## [0.1.0] - 2026-04-13
初期リリース

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。
  - ログ出力は基本 INFO レベルで初期化される（起動スクリプト共通）。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値や 0 以下はデフォルトにフォールバックして警告を出力。
    - プロセス優先度を開始時に "high" に設定（プラットフォームに依存せず psutil を利用して設定）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視データベースに接続し初期化する。
    - duckdb 接続を使用して補助処理を行う。
    - check_once 呼び出し中の例外はログに出力して次のポーリングへ継続。KeyboardInterrupt により正常終了。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し本番 DB と分離。
    - プロセス優先度を開始時に "high" に設定。
    - BrokerClientFactory を用いてブローカークライアントを生成。OrderRepository、OrderManager、RiskManager（デフォルト設定付き）、Reconciler を組み立て ExecutionEngine を実行。
    - 監視テーブルが存在することを保証するため init_monitoring_db を呼び出す（冪等）。

- 設定管理
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パーサ実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート。
    - Settings クラスを用意し、各種環境変数（J-Quants / kabuAPI / LINE / DB パス / PID/KILL フラグ / リソース閾値 / 環境種別など）をプロパティ経由で取得可能。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）を追加。
    - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装し、無効値時は ValueError を送出。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。CLI 形式で期間指定（--from/--to）や DB パス指定（--db）可能。
    - 稼働率・注文成功率（Filled/Created）・送信率（Sent/Created）・リスク却下数・API レイテンシ（avg/max/P95）を集計してレポート出力。
    - P95 計算、日時フィルタ生成、テーブル欠如時のフォールバックを実装。閾値による PASS/FAIL 判定を実装（既定閾値をスクリプト内定義）。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順、同点は signal_rank を用いたタイブレーク）。
    - 等金額配分とスコア加重配分の計算関数を実装。全スコアが 0 の場合は等金額配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別時価を計算して max_sector_pct を超えるセクターの新規候補を除外する。unknown セクターは除外対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull":1.0, "neutral":0.7, "bear":0.3）。未知のレジームは警告と共に 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算（risk_based / equal / score）を実装。lot_size（単元）による丸め、per-position と aggregate の上限処理、利用可能現金に応じたスケーリング（余りは fractional 残差で lot 単位で配分）、cost_buffer による保守的なコスト見積もりを実装。
    - 価格欠損時のスキップ、portfolio_value を使った _max_per_stock 上限を適用。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差を吸収するプロセス優先度設定ユーティリティを実装（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。サポート対象 OS と例外処理（権限不足等）を考慮して警告出力し失敗時はスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を追加（引数検証・権限例外処理あり）。

- リサーチ / ファクター
  - research/factor_research.py
    - DuckDB 接続を受け取り、Momentum / Volatility / Value の各ファクターを SQL と Python で計算する関数を実装。
    - calc_momentum: mom_1m/3m/6m、ma200_dev（200 日移動平均乖離）を算出。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を算出。true_range の NULL 伝播を制御。
    - calc_value: raw_financials から最新財務を結合して PER/ROE を算出。
    - DuckDB 側でウィンドウ関数を活用した効率的な実装。

  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（horizons デフォルト [1,5,21]）、Spearman ランク相関に基づく IC 計算 calc_ic、ファクタ統計 summary（count/mean/std/min/max/median）を実装。外部ライブラリに依存しない純粋 Python 実装。

  - research/__init__.py に主要 API をエクスポート（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）。

- AI / ニュースNLP
  - ai/news_nlp.py
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化して ai_scores テーブルへ書き込む処理を実装。
    - ニュース収集ウィンドウを JST 基準で計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較）。
    - 銘柄ごとに記事を集約しトークン肥大化対策（1 銘柄あたり最大記事数 / 文字数）を実施。
    - 最大 20 銘柄/バッチで API 呼び出しを行い、429/ネットワーク/5xx 時に指数バックオフでリトライ。
    - レスポンスの厳密な JSON バリデーションとスコアクリッピング（±1.0）を実装。
    - 成功したコード群のみを対象に部分的に ai_scores を置換（DELETE → INSERT）して部分失敗時の既存データ保護を行う。
    - API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種秘密情報は環境変数経由で取得する設計。自動 .env ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注記:
- 各モジュールは DuckDB / SQLite / psutil / openai 等の外部依存があります。実行環境に応じて適切に依存パッケージと環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY）を設定してください。
- .env の自動ロードはプロジェクトルート検出に依存します（.git または pyproject.toml が存在するディレクトリ）。パッケージ配布後の使用やテスト時に挙動を変更したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
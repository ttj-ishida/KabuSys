CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-13
------------------

Added
- 基本パッケージ初期リリースを追加。
  - パッケージバージョンは kabusys.__version__ = "0.1.0"。

- 実行用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 環境変数 KABUSYS_ENV により paper_trading モード時は専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）と MockBrokerClient を使用する実装をサポート（本番 DB と分離）。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority）。
    - ExecutionEngine の構築に必要なコンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, DuckDB 接続など）を組み立てる。
    - RiskManager のデフォルト設定（max_position_pct 等）を指定し、初期 portfolio value を broker.get_available_cash() から取得。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視データを記録。
    - プロセス優先度を高めてから起動し、KeyboardInterrupt で安全にシャットダウン。

- 設定管理
  - config.Settings を導入。環境変数 / .env / .env.local から設定を読み込む自動ローダーを実装。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行うため、CWD に依存しない。
    - 必須環境変数未設定時は _require() で ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - 各種パス設定（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH）と監視閾値（CPU/MEM/DISK）をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーションを実施（instant/partial/never/reject）。
    - KABUSYS_ENV の許容値を validation（development, paper_trading, live）。
    - ログレベルのバリデーション（DEBUG..CRITICAL）。

- ポートフォリオ構築関連（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順 → 上位 N を選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率に基づく配分。全スコアが 0 の場合は等金額配分にフォールバックして警告出力。

  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター暴露に基づき、セクター上限を超えている場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告の上 1.0 にフォールバック。

  - portfolio.position_sizing
    - calc_position_sizes: weight / candidates / 各種パラメータを受け、銘柄ごとの発注株数（lot_size 単位）を算出。
    - risk_based / equal / score の allocation_method をサポート。
    - per-stock 上限（max_position_pct）や aggregate cap（available_cash）、cost_buffer を考慮したスケーリングと remainder ベースでの端数配分ロジックを実装。

- 研究・リサーチ機能（DuckDB ベース、外部依存を極力排除）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出（target_date 以前の最新財務データ）。
    - DuckDB のウィンドウ関数を利用した実装で、欠損やデータ不足時は None を返す設計。

  - research.feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターン（LEAD を利用）を計算。horizons のバリデーションを実施。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。有効レコード数 3 未満で None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量の算出（count/mean/std/min/max/median）を提供。
    - 設計方針として pandas 等に依存せず標準ライブラリで実装。

  - research.__init__ で zscore_normalize を data.stats から再エクスポート。

- AI ニュース NLP（OpenAI）
  - ai.news_nlp
    - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込むロジックを実装。
    - チャンクサイズ、最大記事数・最大文字数を制限することでトークン肥大化を抑制（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライする実装（最大リトライ回数あり）。
    - 出力 JSON のバリデーションとスコアクリップ（±1.0）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計。
    - パス/閾値を定義して PASS/FAIL 判定を行う（稼働率 99%、成功率 90%、送信率 95%、P95 latency 200ms）。
    - 日付フィルタ (--from, --to) と --db オプションをサポート。
    - DB が存在しない場合のエラーメッセージを提供。

- ユーティリティ
  - utils.process_priority
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度（high/normal/low）を設定する関数を追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（引数検証・例外時は警告してスキップ）。
    - 権限不足や未実装環境では警告を出して安全にフォールバック。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キー等の機密設定は環境変数での管理を想定。config モジュールは .env 自動読み込みを行うが、明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Known issues / Operational considerations
- process_priority, cpu_affinity はプラットフォーム差分や権限に依存するため、権限不足や未対応 OS では設定がスキップされログに警告が出力されます。
- Settings の必須値未設定時は ValueError を投げます。デプロイ前に .env の設定と必要な環境変数を確認してください（.env.example を参照）。
- Paper Trading モードは本番 DB と明確に分離して動作する設計になっていますが、運用時は PAPER_TRADING_SQLITE_PATH 等の設定を確認してください。
- DuckDB を前提とした集計処理が多数含まれます。prices_daily / raw_financials / raw_news 等のテーブル構造およびデータ整備が前提です。

参考
- 環境変数や設定に関する詳細は kabusys.config.Settings のプロパティドキュメントを参照してください。
- 各モジュールは原則として副作用を排した純粋関数（portfolio / research）または明確なサイドエフェクト（DB / API 書き込み）に分けて設計されています。
CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" のフォーマットに準拠しています。

[Unreleased]
------------

（現在のリリースは下記参照）

0.1.0 - 2026-04-13
-----------------

Added
- パッケージ初版リリース（kabusys v0.1.0）。
- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバックし、警告を出力。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して初期化。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用（settings.paper_sqlite_path）して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine の組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）を行いセッションを実行。
- 設定管理
  - config.Settings を導入し環境変数ベースの設定取得を統一。
  - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。優先順は OS 環境変数 > .env.local > .env。テスト等のため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを強化し、export 形式、クォート文字列、エスケープ、行内コメント処理等に対応。
  - 各種設定プロパティを追加／検証実装（例：PAPER_FILL_MODE の有効値検証、KABUSYS_ENV の検証、LOG_LEVEL の検証）。
  - データベース関連のパス設定を提供（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）。
  - 監視・閾値・PID/kill フラグ等の設定プロパティ追加（cpu/memory/disk の閾値等）。
- 監視関連
  - monitoring_db 初期化を行うユーティリティを run スクリプトから呼出し、監視テーブルの存在を保証（冪等処理）。
- ツール
  - tools.paper_verification_report を追加。Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成。
    - 出力指標：稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95レイテンシ等。
    - デフォルト閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 200 ms）。
    - 日付範囲フィルタ（--from / --to）と --db オプションをサポート。DB が存在しない場合のエラーメッセージを出力。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates（スコア降順、タイブレークは signal_rank）を実装。
    - calc_equal_weights / calc_score_weights を実装。スコア合計が 0 の場合は等金額配分にフォールバックして警告を出す。
  - portfolio.risk_adjustment
    - apply_sector_cap を実装：既存保有のセクター・エクスポージャーを計算し、セクター上限超過時は当該セクターの新規候補を除外（"unknown" セクターは制限を適用しない）。
    - calc_regime_multiplier を実装：regime に基づく投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック（警告出力）。
  - portfolio.position_sizing
    - calc_position_sizes を実装：allocation_method に応じた発注株数計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、portfolio レベルの aggregate cap（available_cash）でスケールダウン、残差配分ロジックを実装。
    - cost_buffer による保守的コスト見積りを反映。
- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) を実装：Windows / POSIX（Linux, Darwin, FreeBSD）を吸収。権限不足や未対応 OS の場合は警告を出力してスキップ。
    - set_cpu_affinity(cpu_count) を実装：最初の N コアに固定。引数検証と権限エラーの扱いを実装。
- リサーチ（DuckDB を利用した純粋関数群）
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB 接続を受け prices_daily / raw_financials を参照してファクターを算出（MA、ATR、リターン等）。
    - スキャン範囲やウィンドウ長に関する定数（例：MA200、ATR 20、各モメンタム窓）を定義。
  - research.feature_exploration
    - calc_forward_returns（任意ホライズンでの将来リターン）、calc_ic（Spearman ランク相関による IC 計算）、rank、factor_summary（基本統計量計算）を実装。
    - 外部依存を極力使わず標準ライブラリのみで実装。
  - research.__init__ で zscore_normalize（kabusys.data.stats）と上記関数群を公開。
- AI / ニュース NLP
  - ai.news_nlp
    - raw_news と news_symbols を集約し OpenAI（gpt-4o-mini）でセンチメントスコアを算出して ai_scores に書き込む機能を実装（score_news）。
    - バッチ化（デフォルト 20 銘柄/コール）、トークン肥大化対策（1銘柄あたり最大記事数・最大文字数でトリム）、スコアを ±1.0 にクリップ。
    - OpenAI クライアントのリトライ方針（429/ネットワーク/5xx に対して指数バックオフ、最大リトライ回数 3 回）を採用。
    - スコア書き込みは部分的失敗に備え、対象コードを絞って置換（DELETE → INSERT）する運用を想定。
    - API キーは引数 api_key または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - ニュース収集ウィンドウは JST ベース（前日 15:00 ～ 当日 08:30 JST）を UTC に変換して DB クエリに使用。ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計方針。
- パッケージ初期化
  - __init__.py にて __version__ = "0.1.0" を設定。

Security, Configuration & Notable Defaults
- .env 自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。プロジェクトルートが見つからない場合は自動ロードをスキップ。
- .env 読み込み時、既存 OS 環境変数はデフォルトで保護される（.env.local は override=True でも OS 環境変数は上書きされない）。
- OpenAI API の利用は API キーが必須（OPENAI_API_KEY）。外部 API を叩く処理は失敗してもフェイルセーフ（ログ記録して継続）となる箇所が多いが、API キー未設定は即時エラー。
- Paper Trading モードは DB を明確に分離（PAPER_TRADING_SQLITE_PATH）しているため、paper_trading 環境での検証・テストは本番データへ影響を与えない設計。
- MONITOR_POLL_INTERVAL、PAPER_FILL_MODE 等、実行時設定可能な環境変数はデフォルト値を持ち不正値時に検証／フォールバックする。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし。

Deprecated
- 初版リリースのため該当なし。

Removed
- 初版リリースのため該当なし。

Notes / 今後の課題（コード内 TODO 等）
- position_sizing: price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価）の導入検討。
- 将来的に単元株（lot_size）を銘柄別に持たせる設計への拡張（stocks マスタの導入）。
- ai.news_nlp: 部分失敗時のより詳細なリカバリ／再試行ポリシーの検討。

問い合わせ
- このCHANGELOGに関する質問や誤り報告は開発チームまでお願いします。
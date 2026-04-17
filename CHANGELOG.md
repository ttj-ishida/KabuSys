CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」フォーマットに従って記載しています。

0.1.0 - 2026-04-17
------------------

Added
- 初回リリース。KabuSys の基礎モジュール群を追加。
  - コマンド／サービス起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトへフォールバック）。
      - 停止フラグファイル（data/stop_requested.flag）検知による安全停止。
      - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
      - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用する旨を明示。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は専用の MockBrokerClient を使用し、paper_trading 用 DB（デフォルト data/paper_trading.db）に完全分離して記録。
      - 起動時のプロセス優先度設定、停止フラグ検知、PID ファイル管理（data/execution.pid）を実装。
  - 設定管理
    - config.py
      - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
      - .env パーサ強化: export プレフィックス、クォートされた値のエスケープ、インラインコメント判定（クォート無しは '#' の直前がスペース/タブの場合にコメント扱い）に対応。
      - Settings クラスを導入し、環境変数から各種設定を取得。必須変数チェック（_require）や値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を追加。
      - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）や paper_trading 用パス（PAPER_TRADING_SQLITE_PATH）を提供。
  - Monitoring DB 初期化ユーティリティ（init_monitoring_db の呼び出しを start スクリプトに組み込み、監視テーブルの存在を保証）。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成スクリプトを追加。
      - 指定期間（--from / --to）または DB 全体を対象に、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下件数を集計し、Pass/Fail 判定を出力。
      - P95 計算、日付フィルタ生成、DB 存在チェック、各種 SQL の例外フォールバックを実装。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates（スコア降順、タイブレークは signal_rank）
      - calc_equal_weights（等金額配分）
      - calc_score_weights（スコア加重、全スコアが 0 の場合は等配分へフォールバック）
    - portfolio/risk_adjustment.py
      - apply_sector_cap（既存ポジションを考慮したセクター集中制限。unknown セクターは制限対象外）
      - calc_regime_multiplier（market regime に応じた投下資金乗数: bull=1.0, neutral=0.7, bear=0.3。未知レジームは 1.0 でフォールバック）
    - portfolio/position_sizing.py
      - calc_position_sizes（risk_based / equal / score の allocation_method をサポート）
      - 単元株（lot_size）で丸め、最大ポジション上限・利用率上限を尊重
      - aggregate cap 超過時のスケーリングと残差処理（lot 単位での追加配分）を実装
      - cost_buffer による手数料・スリッページの保守的見積りを反映
  - ユーティリティ
    - utils/process_priority.py
      - Windows（psutil の PRIORITY_CLASS）と POSIX（nice 値）の差分を吸収してプロセス優先度を設定するユーティリティを実装。
      - CPU affinity 設定関数 set_cpu_affinity を追加（指定コア数に固定）。
      - 権限不足や未対応環境では警告を出して安全にフォールバック。
  - リサーチ / ファクター計算
    - research/factor_research.py
      - momentum, volatility, value のファクター計算を追加（DuckDB を利用して prices_daily / raw_financials を参照）。
      - 各ファクターのウィンドウ長・欠損処理・集計ロジックを実装（MA200, ATR20 等）。
    - research/feature_exploration.py
      - 将来リターン（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク関数（rank）を追加。
      - pandas 等に依存せず、標準ライブラリのみで実装。
    - research/__init__.py にエクスポートを追加（zscore_normalize を含む）。
  - AI / ニュース NLP
    - ai/news_nlp.py
      - raw_news から銘柄ごとに記事を集約して OpenAI API（gpt-4o-mini を想定）へバッチ送信し、センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を追加。
      - タイムウィンドウ計算（JST ベース）、バッチ処理（最大 20 銘柄）、記事トリム（最大記事数・文字数）、429/ネットワーク/5xx に対する指数バックオフ・リトライ、レスポンスの厳密な JSON バリデーションを実装。
      - スコアは ±1.0 にクリップし、部分失敗時も既存スコアを保護するため書き込みは対象コードのみで delete→insert を行う方針。
  - パッケージメタ
    - __init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Migration / 使用上の注意
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings 経由で必須チェックが入ります。未設定の場合は起動時にエラーになります。
- 環境切替
  - KABUSYS_ENV は "development" | "paper_trading" | "live" のいずれかにする必要があります（大文字・小文字は区別されない）。paper_trading を指定すると execution は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使います。
- ログレベル
  - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれか。無効値は例外。
- .env 自動読み込み
  - プロジェクトルートが .git または pyproject.toml で検出できる場合、自動で .env を読み込みます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監視関連
  - MONITOR_POLL_INTERVAL に不正な値を設定した場合は警告が出力されデフォルト (60s) にフォールバックします。
  - 停止は data/stop_requested.flag ファイルの作成で行います（run_monitoring / run_execution ともに検知）。
- Paper Trading
  - PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。不正値は起動時に例外を投げます。
- DB
  - デフォルトパス: data/monitoring.db（監視用）, data/paper_trading.db（ペーパートレード）, data/kabusys.duckdb（分析用）
- OpenAI API
  - ai/news_nlp.score_news は API キーを引数または環境変数 OPENAI_API_KEY から取得します。キー未設定時は ValueError を送出します。
- 既知の制限
  - 一部注記（TODO）や将来拡張のコメントがコード内に残っています（例: position_sizing の銘柄別 lot_size の拡張や sector_exposure の price フォールバックなど）。運用時はこれらの挙動を理解した上で使用してください。
  - ai/news_nlp は堅牢な設計（バッチ・リトライ・JSON バリデーション等）を行っていますが、API 使用時のコストやレート制限に留意してください。

今後の予定
- テストカバレッジ向上（ユニットテスト整備）
- position_sizing の銘柄別 lot_size 対応、price フォールバックロジックの追加
- ai/news_nlp の運用監視・モニタリング改善（失敗時の部分的ロールバック戦略の検討）
- ドキュメント（設計書・運用手順書）の拡充

（以上）
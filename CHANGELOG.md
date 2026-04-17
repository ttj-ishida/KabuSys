CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠し、`Unreleased` → バージョン単位で記載しています。

Unreleased
----------
（特になし）

0.1.0 - 2026-04-17
------------------

Added
- 初期リリース: kabusys パッケージ（バージョン 0.1.0）。
- 実行用エントリスクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を用いて実際のブローカーまたはモックを切替可能。
    - ExecutionEngine の起動時に依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立て、スレッドで run_session を実行。外部停止フラグ（data/stop_requested.flag）で安全に停止可能。
    - プロセス優先度を "high" に設定して起動（utils.process_priority.set_process_priority 呼び出し）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（監視データを一元化）。
    - 停止フラグ（data/stop_requested.flag）および PID ファイルの取り扱いを実装。
- 設定管理
  - config.Settings: 環境変数ベースの設定クラスを追加。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。読み込み順は OS 環境 > .env.local > .env。
    - .env 読み込み時に OS 環境変数を保護（既存値は上書きされない／保護セット protected）。
    - .env パーサの強化: export prefix, クォート文字、バックスラッシュエスケープ、コメント処理などに対応。
    - 各種設定プロパティを実装（DB パス、PID/kill フラグパス、閾値、env/log_level 検証、paper_trading 用設定等）。無効値時は ValueError を送出して早期検出。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）を追加。
- データベース連携
  - DuckDB と SQLite の接続を受け取る設計（research・ai・monitoring・execution が利用）。
  - 監視用 DB 初期化ユーティリティ init_monitoring_db を起動処理内で呼び出し（冪等性を確保）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank をタイブレークにして選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（スコア合計が 0 の場合は等金額にフォールバックして警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中リスクの上限チェック。既存保有からセクター別エクスポージャを算出して、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear をマッピング。未知のレジームは警告のうえ 1.0 をフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応する発注株数計算を実装。
      - 単元株（lot_size）丸め、1 銘柄上限・集計上限（available_cash）でスケールダウン、cost_buffer を用いた保守的見積り、残差ロジックによる lot 単位の再配分を実装。
      - price が欠損/0 の場合のスキップやデバッグログあり。
- リサーチ機能（DuckDB ベース）
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value: prices_daily / raw_financials を用いたモメンタム・ボラティリティ・バリュー系ファクター計算。
      - ウィンドウチェック（必要な行数未満は None を返す）やスキャン範囲のバッファを実装。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。入力検証（horizons の範囲）あり。
    - calc_ic: スピアマンランク（Information Coefficient）を計算する実装（結合・None 排除・最小サンプルチェック）。
    - factor_summary / rank: 基本統計量・ランク処理を実装。標準ライブラリのみで実装。
  - research.__init__: zscore_normalize を含む主要 API をエクスポート。
- ニュース NLP（AI）モジュール
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングし、ai_scores テーブルに書き込む設計を追加。
    - ニュース収集ウィンドウ計算（JST 基準 → UTC 変換）。
    - バッチ処理、トークン肥大化対策（記事数・文字数のトリム）、最大 20 銘柄単位の API 送信、429/5xx/タイムアウト等に対する指数バックオフのリトライ設計。
    - API レスポンス検証、スコアクリップ（±1.0）、部分的更新（対象コードのみ DELETE → INSERT）で耐障害性を確保。
    - API キー解決（引数または OPENAI_API_KEY 環境変数）。未設定時は ValueError。
- ユーティリティ
  - utils.process_priority: プロセス優先度設定（Windows/Linux/macOS に対応）と CPU affinity 設定を追加。権限不足や未対応 OS の場合は警告でスキップ。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs テーブルを参照して稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計して判定（PASS/FAIL）。
    - 日付フィルタ --from / --to / --db をサポート。DB 存在チェックと OperationalError によるフォールバック対応あり。
- パッケージ初期化
  - __init__.py にパッケージ名と __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- .env のパース/ロード動作を改善し、クォート内のエスケープ・インラインコメント処理や export プレフィックスに対応。OS 環境変数を上書きしない保護ロジックを追加。

Security
- .env 自動ロード時に OS 環境変数を protected として上書き禁止にすることで、テスト/運用環境の誤設定による秘密情報上書きを防止。

Notes / Known issues
- ai/news_nlp.py は設計上の多くの堅牢化（バッチ、リトライ、レスポンス検証）を含むが、実装途中で一部の関数実装が途中で切れている可能性（ソースの末尾が途中で終端）があります。OpenAI 連携を有効化する前に完全な実装と単体テストを推奨します。
- apply_sector_cap 内で price が欠損 (0.0) の場合のエクスポージャ過小見積りに関する TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する旨がコメントされています。
- position_sizing は現状「単一 lot_size (既定 100) を全銘柄共通」とする設計。将来的には銘柄別 lot_map を受け取る拡張を想定している旨の TODO コメントあり。
- Settings のプロパティは厳格なバリデーションを行うため、既存の環境変数が想定外の値の場合は起動時に例外が発生する可能性があります。デプロイ前に .env.example を参照して環境変数を整備してください。

Developers
- 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動読み込みをスキップできます（テスト時に便利）。
- ロギング: 起動スクリプトは logging.basicConfig(level=logging.INFO) を使用。詳細デバッグを得たい場合は LOG_LEVEL または環境変数で調整してください。

License
- （ソース上にライセンス情報が明示されていないため CHANGELOG には記載していません。必要に応じて LICENSE を追加してください。）
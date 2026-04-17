# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py: 0.1.0）に合わせています。

## [0.1.0] - 2026-04-17

### Added
- 初回リリース：KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - コマンド／サービス起動スクリプト
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを追加。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
      - 停止フラグファイル（data/stop_requested.flag）検知で優雅に終了。
      - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 専用 DB（data/paper_trading.db）で完全分離して動作。
      - エンジンは別スレッドで実行し、停止フラグ検知で engine.stop() を呼び出して停止。
  - 環境設定管理（src/kabusys/config.py）
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）を実装。優先順位は OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス、クォート（エスケープ対応）、インラインコメント等に対応。
    - Settings クラスに各種プロパティを実装（DB パス、API トークン、監視閾値、PAPER_FILL_MODE 等）。入力値のバリデーションを実施。
  - ポートフォリオ構築（src/kabusys/portfolio/*）
    - 銘柄候補選定と重み計算（select_candidates、calc_equal_weights、calc_score_weights）。
    - セクター集中制限とレジーム乗数（apply_sector_cap、calc_regime_multiplier）。
    - 発注数量計算（calc_position_sizes）:
      - risk_based / equal / score の各配分方式に対応。
      - 単元株丸め、1 銘柄上限、aggregate cap によるスケールダウン（残差処理を含む）。
      - cost_buffer により手数料・スリッページを保守的に見積もり。
  - 研究・ファクター計算（src/kabusys/research/*）
    - ファクター計算: calc_momentum、calc_volatility、calc_value（DuckDB を利用し prices_daily / raw_financials を参照）。
    - 将来リターン・IC 等: calc_forward_returns、calc_ic、factor_summary、rank。
    - 各関数は DuckDB 接続を受け取り SQL と純粋関数で処理する設計。
  - AI ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news を集約して OpenAI（gpt-4o-mini）へバッチスコアリングし、ai_scores テーブルへ書き込む処理の設計・実装。
    - スコアは ±1.0 にクリップ、429/ネットワーク断/5xx 等は指数バックオフでリトライ（最大リトライ回数制限あり）。
    - ニュース収集ウィンドウ（JST 基準）計算ユーティリティを実装（calc_news_window）。
    - API キー未設定時は明確なエラーを返す。
  - ユーティリティ（src/kabusys/utils/process_priority.py）
    - プロセス優先度設定（set_process_priority）を実装。Windows と POSIX（Linux/Mac/FreeBSD）差分を吸収。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
  - 開発ツール（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading の検証レポート出力ツールを追加。
    - コマンドライン引数 --from/--to/--db に対応。デフォルト DB は data/paper_trading.db。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）等の指標算出と PASS/FAIL 判定（閾値はソース内定数として定義）。
  - パッケージ初期設定（src/kabusys/__init__.py）
    - バージョン情報とエクスポート定義を追加（__version__ = "0.1.0"）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の必須情報が未設定の場合に明確に ValueError を送出するようにしており、不正な未設定状態での API 呼び出しを防止。

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Notes / Implementation details / 動作上の注意
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数の不正値（0 や負数、非数）を検出して警告し、デフォルト 60 秒にフォールバックします。
- run_execution は paper_trading 環境下で本番 DB と完全分離された SQLite（data/paper_trading.db）を使用します。RiskConfig の initial_portfolio_value は BrokerClient の get_available_cash() で初期化されます。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後でもカレントワーキングディレクトリに依存せず動作します。ただしプロジェクトルートが特定できない場合は自動ロードをスキップします。
- calc_score_weights は全スコアが 0.0 の場合に等金額配分にフォールバックし WARNING を出します。
- apply_sector_cap は sector_map に存在しない銘柄を "unknown" 扱いとし、unknown セクターには上限制約を適用しません（設計上の意図）。
- calc_position_sizes の aggregate cap スケーリングは単元株（lot_size）単位での残余配分ロジックを持ち、再現性のために安定ソートを使用します。
- research モジュールは DuckDB 上の prices_daily / raw_financials テーブルに依存します。データ不足時は None を返す設計です。
- paper_verification_report は対象テーブルが存在しない場合に sqlite3.OperationalError を捕捉してデフォルト値にフォールバックし、レポートを出力します。
- utils/process_priority は権限不足（psutil.AccessDenied 等）や未対応プラットフォーム時に警告を出して処理をスキップします。

### Known issues / TODOs / Work in progress
- src/kabusys/ai/news_nlp.py: ファイル末尾で処理中断（提供されたコードが途中で切れているため、一部内部実装（例: _fetch_articles の続きや実際の書き込みロジック）が未完）。本番運用前に残り実装と十分なエラーハンドリング・テストが必要。
- position_sizing.calc_position_sizes の価格欠損（price が 0.0）に関しては現在コメントで将来のフォールバック（前日終値や取得原価等）を検討中。欠損時にエクスポージャーが過少評価されるリスクあり。
- 将来的には lot_size を銘柄毎に持たせる等の拡張を想定している（現在は全銘柄共通）。
- research モジュールのスキャン範囲や日数バッファは暫定値（ドキュメント参照）であり、実データでの検証が推奨される。

---

（今後のリリースでは「Changed」「Fixed」「Security」等のカテゴリを埋めていきます。）
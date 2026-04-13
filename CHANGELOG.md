# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
慣例に従い、セクションは Added / Changed / Fixed / Security 等に分けています。日付はこのファイル作成時点（YYYY-MM-DD）を使用しています。

## [0.1.0] - 2026-04-13
初回公開リリース。以下の主要機能を実装しています。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py に __version__ = "0.1.0" を設定）。

- 実行エントリスクリプト
  - 実行系起動スクリプトを追加:
    - run_execution.py: ExecutionEngine の起動処理、ブローカーファクトリの使用、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、paper_trading 環境では専用 SQLite を使用する動作を実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動、MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応、監視用 DB 初期化処理、プロセス優先度設定を行う。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み順: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサ実装：export プレフィックス対応、クォート内バックスラッシュエスケープ、インラインコメント処理等を実装。
    - 各種環境変数（J-Quants / kabu API / LINE / DB パス / 監視閾値 / PID ファイルなど）をプロパティで提供。バリデーション（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実施。

- 監視関連
  - 監視 DB 初期化ユーティリティを使用するエントリポイント（init_monitoring_db を呼ぶ）。
  - run_monitoring は常に本番用 sqlite_path を参照して監視テーブルを管理する仕様。

- Execution 系機能
  - ExecutionEngine 起動フローの組み立て（duckdb 接続、broker 作成、リスク設定、実行セッション開始）。
  - Paper Trading: KABUSYS_ENV=paper_trading 時に別 SQLite（data/paper_trading.db）へデータを記録する分離設計。
  - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec 等）をデフォルトで指定。

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順で上位 N を選択（同点時は signal_rank でブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合は等金額にフォールバック。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションからのエクスポージャ計算、sell_codes を考慮）。
    - calc_regime_multiplier: market regime に応じた乗数（bull/neutral/bear -> 1.0/0.7/0.3）と不明レジームのフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定。lot_size, cost_buffer を考慮した aggregate cap（スケーリング）と再配分ロジックを実装。

- 研究/リサーチ機能（src/kabusys/research）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value: DuckDB 上の prices_daily / raw_financials を用いた各種ファクター算出を実装（MA200, ATR20, PER, ROE 等）。
  - feature_exploration:
    - calc_forward_returns: 将来リターンの一括取得（複数ホライズン対応、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損除外・3レコード未満は None）。
    - factor_summary, rank: 基本統計量・ランク付けユーティリティ。
  - research パッケージの公開 API を整備（zscore_normalize を kabusys.data.stats から再公開）。

- AI / ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI にバッチ送信して銘柄別センチメント（ai_scores）を生成する機能を実装。
    - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ。
    - バッチサイズ制限（_BATCH_SIZE=20）、トークン肥大化対策（最大記事数・最大文字数トリム）、スコアクリップ（±1.0）。
    - OpenAI クライアント生成・429/5xx/ネットワークエラー等へのリトライ戦略（指数バックオフを想定）。
    - レスポンス検証と安全なテーブル更新（部分失敗時に他銘柄を保護する DELETE→INSERT の手順）。
    - API キーの引数／OPENAI_API_KEY 環境変数の解決と未設定時のエラー。

- ユーティリティ（src/kabusys/utils）
  - process_priority:
    - set_process_priority(level): Windows と POSIX の差分を吸収して優先度を設定。対応 OS をチェックし、例外（権限不足等）をログ警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 設定（安全にスキップ可能）。

- ツール
  - paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を計算して標準出力へ表示。コマンドライン引数で期間や DB パスを指定可能。

### Changed
- 設定読み込みの挙動を明確化:
  - .env の自動ロードはプロジェクトルート検出に依存し、CWD に依存しない設計に変更（パッケージ配布後も安定動作）。
  - .env.local は .env を上書きする（override=True）挙動を採用。

- DB 接続方針:
  - 監視(run_monitoring)は環境に依らず本番 sqlite_path を使用する明確化。
  - 実行(run_execution)は paper_trading 環境で paper_sqlite_path を利用して本番 DB と分離。

### Fixed
- .env パーサの堅牢化:
  - export KEY=val 形式のサポート、クォート内のバックスラッシュエスケープ処理、インラインコメント識別ロジックを追加して様々な .env フォーマットに耐性を持たせた。
- position_sizing の aggregate cap 調整ロジック:
  - cost_buffer を考慮したコスト見積りと、残余キャッシュでの lot_size 単位の追加配分を実装してスケールダウン時の丸め誤差を改善。

### Security
- OpenAI API キーの取り扱い:
  - api_key が明示されない場合は環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を送出して明示的に失敗させる（秘密鍵のうっかり漏洩を防ぐため、ログにキー値を出力しない）。

### Notes / Known limitations
- Position sizing:
  - price が欠損（0.0）の場合、エクスポージャ計算が過少評価される可能性があり、将来的に前日終値や取得原価によるフォールバックを検討する旨の TODO を残しています。
- CPU affinity / priority 設定:
  - 権限不足や未対応プラットフォームでは警告を出して処理をスキップするため、意図どおり優先度変更されない環境がある点に注意してください。
- research / ai モジュールは DuckDB のテーブル構成（prices_daily, raw_financials, raw_news 等）に依存します。DB スキーマ・データが存在しない環境ではエラーや N/A 表示になります。
- paper_verification_report は DuckDB ではなく paper_trading 用 SQLite を参照する設計。

---

今後の予定（例）
- 0.2.0 の候補:
  - ファクター標準化・スコアリングパイプラインの追加（zscore 正規化の統合利用例）。
  - broker/mocking の拡張（より現実的な部分約定シミュレーションなど）。
  - AI スコア取得の並列化・非同期化とより堅牢なエラー回復機能。

フィードバックや修正の要望があればお知らせください。
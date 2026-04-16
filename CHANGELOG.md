# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

なお、本リポジトリの初回リリースはパッケージ内部の __version__ = "0.1.0" に合わせて 0.1.0 としています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-16

### Added
- 基本パッケージの初期実装を追加。
  - パッケージ識別子: kabusys（__version__ = 0.1.0）。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml を参照）。
  - export 付き行やクォート文字列、インラインコメント処理に対応した .env パーサを実装。
  - 環境変数の保護（OS 環境変数の上書き防止）や override オプションをサポート。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別など）。
  - 環境違反値検出時に明確な ValueError を投げるバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - settings オブジェクトをエクスポート。

- 実行系起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine を起動するエントリポイントを実装。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH で上書き可能）。
  - BrokerClientFactory による実際のブローカー／モックの切替えを想定。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てと起動ロジックを実装。
  - 停止フラグ（data/stop_requested.flag）検知による安全停止、実行 PID を data/execution.pid に保存する仕組みを想定。
  - 監視テーブルの存在保証（init_monitoring_db を呼び出し冪等的に作成）。

- 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor を利用したポーリングループ実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログを残してデフォルトにフォールバック。
  - 監視処理は実行環境に関わらず本番 sqlite_path を使用する設計。
  - 停止フラグ検知でループ終了。KeyboardInterrupt に対するハンドリングと DB 接続の確実なクローズ。

- プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収してプロセス優先度（high/normal/low）設定を提供。
  - CPU affinity を最初の N コアに固定する関数を提供。権限不足や未対応環境では警告ログを出して安全にスキップ。

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - 候補選定・重み付け（portfolio_builder）
    - select_candidates: スコア降順＋タイブレークとして signal_rank を採用。
    - calc_equal_weights / calc_score_weights: 等分配・スコア重み配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数（risk_adjustment）
    - apply_sector_cap: 既存保有比率に基づき同一セクターの新規候補を除外（"unknown" セクターは適用除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告と共に 1.0 にフォールバック。
  - 株数決定・リスク制限（position_sizing）
    - calc_position_sizes: risk_based / equal / score の allocation_method をサポート。単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer による保守的見積り、aggregate cap によるスケーリングと残余配分ロジックを実装。

- 研究用モジュール（src/kabusys/research/*）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials テーブルを利用したファクター計算を実装（MA200、ATR20、各種リターン、PER/ROE 等）。
    - 計算に必要なデータ不足時の None 扱い、スキャン範囲の最適化（calendar buffer）を実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターン計算。
    - calc_ic: Spearman ランク相関（IC）計算（同順位は平均ランク）と適切なデータフィルタリングを実装。
    - factor_summary / rank: ファクターの基本統計量、ランク変換ユーティリティを提供。
  - research パッケージから主要関数をエクスポート。

- Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）
  - SQLite（デフォルト data/paper_trading.db）から各種メトリクスを集計し、検証レポートを標準出力に出力するコマンドラインツールを提供。
  - 判定基準（稼働率、注文成功率、送信率、P95 レイテンシ）を定義し、期間指定（--from / --to）に対応。
  - DB テーブル欠落時の頑健なハンドリング（OperationalError を捕捉して N/A を表示）。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news + news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメントスコアを ai_scores に書き込むフローを実装（設計書に沿った処理説明・実装）。
  - バッチサイズ、文字数制限、最大記事数、リトライ（429/5xx/タイムアウト）に対する指数バックオフ、レスポンス検証、±1.0 にスコアクリップなどの安全策を実装。
  - ニュース時間ウィンドウ計算ユーティリティ（calc_news_window）を実装。
  - OpenAI API キーの解決と未設定時の ValueError を実装。
  - （注）ファイル末尾が切れているため本体の一部実装は継続中。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境変数からのポーリング間隔取得処理で 0 以下や非整数を検出した際に time.sleep に渡して例外が発生しないようデフォルトにフォールバックするロジックを追加（run_monitoring._get_poll_interval）。
- .env 読み込みで IO エラーが発生した場合に warnings.warn を利用して読み込み失敗を通知するようにした（config._load_env_file）。

### Notes / Known issues
- news_nlp.py はファイル末尾が途中で切れており、記事フェッチ処理や最終的な DB 書き込み部分の実装が未完です。実運用前に該当箇所の完成と統合テストが必要です。
- ポートフォリオ計算やリスク制御の一部（例: price 欠損時のフォールバック価格、銘柄別 lot_size）は TODO コメントに記載の拡張が計画されています。現在は簡易的な挙動（価格欠損はスキップ等）となります。
- set_process_priority / set_cpu_affinity は実行環境の権限によっては動作しない場合があり、その場合は警告ログでスキップします。

### Environment variables (主なもの)
- KABUSYS_ENV (development | paper_trading | live)
- SQLITE_PATH (監視用 SQLite、デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
- DUCKDB_PATH (DuckDB ファイル、デフォルト data/kabusys.duckdb)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔 秒)
- OPENAI_API_KEY (news_nlp 用)
- PAPER_FILL_MODE (paper_trading の fill モード: instant|partial|never|reject)

---

貢献・フィードバック歓迎します。次のリリースでは news_nlp の未実装部分の完了、テストケースの追加、監視/実行エンジンの統合テストを予定しています。
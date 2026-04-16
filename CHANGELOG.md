CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-16
--------------------

Added
- 初回リリース: KabuSys の基本機能群を追加。
- 実行／監視エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用の SQLite（data/paper_trading.db, 環境変数で上書き可）に記録する。停止フラグ（data/stop_requested.flag）と PID ファイル管理に対応。プロセス優先度を起動時に設定。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する。
- 設定管理（config）
  - .env 自動ロード機能を実装（プロジェクトルートの検出：.git または pyproject.toml 基準）。OS 環境変数を保護する仕組み（protected keys）を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env 行パーサーを実装（export プレフィックス、クォート文字列、インラインコメントの扱い等に対応）。
  - Settings クラスを提供し、各環境変数の取得・検証（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、PAPER_FILL_MODE 等）を一元化。KABUSYS_ENV・LOG_LEVEL 等の検証を実装。
- データベース連携
  - duckdb および sqlite3 接続を使用する設計を導入（各モジュールで接続を受け取る形）。
  - 監視用テーブルの初期化ユーティリティ init_monitoring_db を参照して起動時に冪等的にテーブルを作成。
- ポートフォリオ構築（portfolio）
  - portfolio_builder: シグナルの候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全て 0 の場合は等金額配分へフォールバック。
  - risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング）を実装。
  - position_sizing: 株数決定ロジック calc_position_sizes を実装。allocation_method（risk_based / equal / score）に対応し、リスクベース計算、単元株（lot_size）丸め、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer（手数料等の保守的見積）などを考慮。
- 研究（research）
  - factor_research: Momentum / Volatility / Value ファクター計算を実装（calc_momentum, calc_volatility, calc_value）。DuckDB の SQL ウィンドウ関数を活用して移動平均・ATR 等を算出。
  - feature_exploration: 将来リターン計算 calc_forward_returns、情報係数（IC）計算 calc_ic、ファクター統計要約 factor_summary、ランク関数 rank を実装。外部依存は使わず標準ライブラリベースで実装。
- ニュース NLP（AI）
  - news_nlp: raw_news を OpenAI (gpt-4o-mini) へ送ってセンチメントスコアを算出し ai_scores テーブルへ書き込む処理を実装（score_news）。処理の要点：
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正確に計算する calc_news_window。
    - 銘柄ごとに記事を集約し、1 銘柄あたりの最大記事数・文字数でトリム。
    - 最大 20 銘柄/バッチで API に送信、429/ネットワーク断/5xx 等は指数バックオフでリトライ。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ、部分失敗時のデータ保護（対象コードの限定削除→挿入）。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得し、未設定時は ValueError を送出。
- ユーティリティ（utils）
  - process_priority: Windows と POSIX 系（Linux/Mac 等）を吸収してカレントプロセスの優先度設定（set_process_priority）および CPU affinity 固定（set_cpu_affinity）を提供。権限不足や未サポート環境では警告ログを出して安全にスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し PASS/FAIL 判定を出力。DB 存在チェックやテーブル欠損に対する安全ハンドリングあり。

Changed
- （初回リリースのため該当なし）

Fixed
- .env パーサーの堅牢化（クォート中のバックスラッシュエスケープ、インラインコメントの扱い）により多様な .env フォーマットを許容。
- paper_verification_report: データベース/テーブルが存在しない場合に OperationalError を捕捉してレポート生成を継続できるようにした。

Security
- OpenAI API キー等の機密情報は Settings 経由または引数で明示的に渡す設計。自動的に漏洩する仕組みは導入していない。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env 読み込みを無効化可能（テスト用途）。

Notes
- KABUSYS_ENV は "development" / "paper_trading" / "live" のみを受け付ける（Settings で検証）。値が不正な場合は起動時に例外が発生する。
- PAPER_FILL_MODE（paper trading の約定モード）には "instant" / "partial" / "never" / "reject" が有効値。無効値は ValueError。
- run_monitoring は monitoring 用 DB（sqlite_path）を環境にかかわらず使用する設計になっているため、監視データは paper_trading 環境でも本番の monitoring DB に記録される点に注意。

今後の予定（ TODO / 今後検討 ）
- price の欠損時のフォールバック（前日終値や取得原価）を position_sizing / apply_sector_cap で扱う改善。
- 銘柄別 lot_size の導入（現状はグローバルな lot_size を想定）。
- news_nlp のレスポンス処理強化（部分的な JSON 破損時のリカバリ等）。
- テストカバレッジの拡充および DuckDB クエリのパフォーマンス検証。
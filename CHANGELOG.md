Keep a Changelog に準拠した CHANGELOG.md（日本語、推測に基づく記載）

注: 以下は提供されたコードベースの内容から機能追加・変更点を推測してまとめた変更履歴です。実際のコミット履歴ではなく、コードの意図・機能単位で編成しています。

フォーマットの説明:
- 重要な変更点はカテゴリ（Added / Changed / Fixed / Deprecated / Removed / Security）に整理しています。
- 日付は本ファイル作成日（2026-04-12）を使用しています。

[Unreleased]
（現時点では未リリースの差分はありません）

[0.1.0] - 2026-04-12
Added
- 初回公開: KabuSys 自動売買フレームワークの基礎実装を追加。
- コア機能
  - portfolio: 銘柄選定・配分・ポジションサイズ決定・リスク調整機能を追加。
    - portfolio_builder: select_candidates（スコア降順で候補選定）、calc_equal_weights、calc_score_weights（スコア加重配分。全スコアが 0 の場合は等配分にフォールバック）。
    - position_sizing: calc_position_sizes（risk_based / equal / score の割当方法、単元株（lot）丸め、aggregate cap によるスケールダウン、手数料等を考慮する cost_buffer）。
    - risk_adjustment: apply_sector_cap（セクター集中リスクの除外ロジック）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）。
- リサーチ機能（DuckDB 前提）
  - research.factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200乖離の算出）
    - calc_volatility（ATR、相対ATR、平均売買代金、出来高比率）
    - calc_value（PER / ROE の算出）
  - research.feature_exploration:
    - calc_forward_returns（将来リターン算出）
    - calc_ic（Spearman ランク相関による IC 計算）
    - factor_summary / rank（統計サマリとランク変換）
  - research パッケージから zscore_normalize を再エクスポート
- AI / ニュース分析
  - ai.news_nlp: raw_news を集約して OpenAI API（gpt-4o-mini）でセンチメントを算出・ai_scores テーブルへ書き込む処理を追加。
    - バッチ処理（最大 20 銘柄/コール）、トークン対策（記事数・文字数制限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップなどを実装。
    - news ウィンドウ計算（JST基準 → UTC変換）を提供。
- 実行・監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db 既定）に記録して本番 DB と分離。
  - run_monitoring: SystemMonitor 起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（既定 60 秒）。監視処理は環境に関係なく本番 sqlite_path を使用する設計。
  - 両スクリプトとも起動直後にプロセス優先度を「high」に設定するユーティリティ呼び出しを行う。
- 設定・環境変数管理
  - config: 環境変数自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml）を実装。読み込み順は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、クォート（シングル／ダブル）のエスケープ、インラインコメントの処理等に対応。
  - Settings クラスを提供（多くのプロパティを定義）。主なもの:
    - JQUANTS / KABU API / LINE API 関連トークン取得
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH の既定値と Path 変換
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）
    - PID / KILL フラグ関連パスと閾値（CPU/MEM/DISK）
    - KABUSYS_ENV のバリデーション（development|paper_trading|live）および is_live/is_paper/is_dev 判定
    - LOG_LEVEL のバリデーション
- ユーティリティ
  - utils.process_priority: Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定ユーティリティを実装。CPU affinity 設定機能も提供。権限不足や未対応環境では警告を出してスキップするフェイルセーフを備える。
- ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite を読み取り、稼働率・注文成功率・送信率・P95 レイテンシなどの指標を算出して PASS/FAIL レポートを標準出力に出力する CLI スクリプトを追加。コマンドライン引数で期間指定（--from/--to）と DB パス（--db）を指定可能。
- データベース初期化
  - monitoring.monitoring_db:init_monitoring_db を利用して監視テーブルの存在を保証（冪等）する処理を run_execution/run_monitoring に組み込み。

Changed
- DuckDB を分析・AI 周りの計算（research / ai）と Execution/Monitoring の補助に広く導入。SQL と Python を組み合わせた処理設計を採用。
- run_monitoring のデフォルトポーリング間隔を定義して環境変数で上書き可能に（_DEFAULT_POLL_INTERVAL=60 秒）。不正値時は警告してデフォルトにフォールバック。
- run_execution の paper_trading 処理は本番 DB と完全に分離する挙動（paper_sqlite_path を使用）を明文化。

Fixed
- .env ファイルパーサの強化: export 形式対応、クォート内のエスケープ処理、インラインコメントの扱い、無効行のスキップなどを扱う実装により環境変数ロードの堅牢性を向上。
- research.feature_exploration: calc_forward_returns の horizons 引数チェック（正の整数かつ <=252）を追加し、不正入力時に明示的に例外を出すよう改善。

Deprecated
- なし（初回リリース）。

Removed
- なし（初回リリース）。

Security
- OpenAI API キーは引数か環境変数 OPENAI_API_KEY で供給する設計。未設定時はエラーを返し、キーの存在確認を行う。キーのハンドリングに関する追加の保護（暗号化等）は未実装。

Notes / 運用上の注意（実装から推測）
- paper_trading モードでは MockBrokerClient を用いるため、本番口座への注文や資金操作は行われない設計。ただし DB パスや設定により別途運用ミスが発生し得るため、環境変数の設定（PAPER_TRADING_SQLITE_PATH 等）は慎重に行うこと。
- run_monitoring は監視 DB に本番 sqlite_path を使用する（KABUSYS_ENV に依らない）。テスト目的で監視挙動を分離したい場合は適宜 DB パスやコードの調整が必要。
- process_priority / cpu_affinity の設定は権限に依存するため、unprivileged 環境では警告が出力されるが処理は継続する（フェイルセーフ）。
- ai.news_nlp は OpenAI API に依存するため API 失敗時はチャンク単位でスキップして継続する実装（フェイルセーフ）。レスポンス形式に厳密な JSON を期待している。

開発者向け情報（環境変数の主な一覧）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
- OPENAI_API_KEY
- DUCKDB_PATH（既定: data/kabusys.duckdb）
- SQLITE_PATH（既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）
- PAPER_FILL_MODE（instant|partial|never|reject、既定: instant）
- KABUSYS_ENV（development|paper_trading|live、既定: development）
- LOG_LEVEL（DEBUG|INFO|...）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒、既定: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（1 にすると .env の自動ロードを無効化）

--- 
（以降のリリースでは、各モジュールの個別改良（パフォーマンス改善、単体テスト追加、OpenAI レート制御強化、DuckDB スキーマ変更対応、パラメータの設定可能化など）が想定されます。実際の変更履歴を作る際はコミットログ・PR を参照して項目を正確に分割してください。）
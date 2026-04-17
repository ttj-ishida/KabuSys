# Changelog

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog 準拠です。

## [Unreleased]

- なし（初期リリース相当の状態）

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期バージョンの公開。パッケージ名: kabusys、バージョン `0.1.0` を設定。
  - パッケージのエクスポート API を整理（kabusys.__init__ の __all__）。

- 設定管理
  - .env ファイル自動読み込み機能を実装（プロジェクトルートの判定は .git または pyproject.toml を探索）。
  - .env パーサを実装（export KEY=val 形式、クォート・エスケープ、インラインコメント処理に対応）。
  - 環境変数読み込み順序を実装（OS 環境 > .env.local > .env）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
  - Settings クラスを導入し、各種設定値（J-Quants / kabu / LINE / DB パス / 監視閾値 / 環境判定 等）をプロパティで取得・検証する実装を追加。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の入力バリデーションを追加。

- 実行・監視ツール
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。Paper Trading 環境時には専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、Engine のデーモン実行と停止フラグ監視（data/stop_requested.flag）を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor を定期ポーリングで実行する起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、値検証あり）。
    - 監視機能は環境にかかわらず本番用 sqlite_path を利用する設計。
    - 停止フラグ検知でループを安全に終了。

- モニタリング DB 初期化
  - init_monitoring_db を利用して監視用テーブルの存在を保証（冪等）。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームでプロセス優先度設定（Windows / POSIX）および CPU affinity 設定を追加。権限不足や未サポート OS の場合は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates（スコア降順・タイブレーク: signal_rank）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分。全スコア0のときは等金額にフォールバック）
  - portfolio.risk_adjustment:
    - apply_sector_cap（セクター集中の上限判定。sell_codes により当日売却予定銘柄を除外可能）
    - calc_regime_multiplier（market レジームに応じた乗数。b ull/neutral/bear をマッピング、未知レジームで警告とフォールバック）
  - portfolio.position_sizing:
    - calc_position_sizes（risk_based / equal / score の割当方式、lot_size に応じた丸め、per-stock および aggregate のキャップ処理、cost_buffer を考慮したスケーリングと端数配分）

- 研究・リサーチ
  - research.factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、ATR 比率、平均売買代金、出来高比等）
    - calc_value（PER, ROE を raw_financials と prices_daily から計算）
    - 全関数は DuckDB 接続を受け取り SQL で完結する実装
  - research.feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）
    - calc_ic（Spearman ランク相関による IC 計算）
    - rank（同順位の平均ランクに対応）
    - factor_summary（count/mean/std/min/max/median の算出）
  - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポート。

- AI ニュース NLP
  - ai.news_nlp:
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント加工し ai_scores テーブルへ書き込む処理設計を追加。
    - バッチサイズ、入力トリム（記事数・文字数上限）、リトライ（429/ネットワーク/5xx の指数バックオフ）、レスポンスバリデーション、スコアクリップ（±1.0）などを仕様化。
    - タイムウィンドウ計算（JST 基準 → UTC 変換）calc_news_window を実装。
    - score_news 関数の API キー解決・バリデーションを実装。

- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し PASS/FAIL を判定する CLI を提供。
    - 日付フィルタ、P95 計算、各種閾値（デフォルト）を実装。
    - 引数で期間指定および DB パス指定可能（--from/--to/--db）。

### Changed
- なし（初回リリースに相当するため変更履歴は初期追加の記述に集約）

### Fixed
- なし（初回リリースのためバグ修正エントリはなし）

### Known limitations / Notes
- ai.news_nlp の実装ファイルはコード末尾で途中（切り捨て）となっているため、完全な記事取得・API 呼び出し・DB 書き込みの処理は未完成の可能性あり。score_news の初期処理（API キー解決・ウィンドウ計算）は存在するが、続きの fetch/transform/persist 部分が未収録。
- portfolio.position_sizing:
  - price が欠損（0.0）の場合、エクスポージャーや発注量が過少見積りされる可能性があり、将来的に前日終値等でのフォールバックを検討する旨の TODO コメントあり。
  - lot_size は現状すべての銘柄で共通（将来的に銘柄別 lot_map に拡張予定）。
- .env パーサの振る舞いはかなり寛容だが、非常に複雑なエスケープやコメントの特殊ケースで想定外の挙動を示す可能性がある。
- DuckDB の executemany に関する制約を意識した実装上の注意が各所に記載されている（ai.news_nlp 等）。

### Security
- 環境変数の自動読み込みで OS 環境変数を保護する仕組み（protected set）を導入。重要な OS 環境変数が .env によって意図せず上書きされるのを防止。

---

注: 本 CHANGELOG は渡されたコードベースから推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそれに従って修正してください。
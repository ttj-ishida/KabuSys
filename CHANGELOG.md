CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従って記載しています。
日付は本リリースの日付です。

[0.1.0] - 2026-04-12
-------------------

Added
- 基本アプリケーション構成を実装
  - パッケージバージョンを kabusys.__version__ = "0.1.0" として設定。
- 実行エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory の利用、OrderRepository/OrderManager/Reconciler/RiskManager を組み立てて engine.run_session() を実行。
    - プロセス優先度を起動時に "high" に設定する処理を追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルへ接続。
    - プロセス優先度を "high" に設定し、例外発生時にもループを継続する安全処理を実装。
- 設定管理
  - config.py: .env 自動読み込みと Settings クラスを実装。
    - プロジェクトルート検出（.git または pyproject.toml を探索）により CWD に依存しない自動 .env ロードを実現。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）を採用。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - export プレフィックス、クォートされた値、インラインコメント等に対応した .env パーサを実装。
    - 環境変数のバリデーションを実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
    - 各種パスや閾値（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/Memory/Disk 閾値）を Settings で取得可能に。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等金額へフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有を基にセクター集中上限を判定し、新規候補をフィルタリング。unknown セクターは制限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を計算（bull/neutral/bear をマップ、未知レジームは 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: weight/candidates/portfolio_value 等から発注株数を算出。allocation_method に "risk_based"/"equal"/"score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金超過時のスケールダウン）を実装。
    - cost_buffer を考慮した保守的なコスト見積り、スケールダウン時の残差に対する lot 単位の再配分ロジックを追加。
- リサーチ（DuckDB ベース）
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value: DuckDB 接続を受け取り prices_daily / raw_financials から各種ファクター（モメンタム、ATR、平均出来高、PER/ROE 等）を計算。
    - 結果は (date, code) をキーとする dict リストで返す。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括 SQL で取得。
    - calc_ic: スピアマンランク相関（IC）を計算。十分なデータがなければ None を返す。
    - factor_summary / rank: カラムごとの基本統計量の算出、同順位処理（平均ランク）を含むランク変換を実装。
  - research.__init__ から必要な関数を公開。
- AI ニュース NLP
  - ai.news_nlp
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST / UTC 変換）を提供。
    - 最大バッチサイズ、記事数・文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアを ±1.0 にクリップして DB に置換する戦略を実装。
    - OpenAI API キー未指定時は明示的なエラーを送出。
- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX の差を吸収してプロセス優先度を設定。アクセス権限不足等のエラーは警告扱いでスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定する機能を追加（cpu_count=None で無効化、1 未満は ValueError）。
- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプトを追加。SQLite の paper_trading DB を読み、稼働率・注文成功率・送信率・レイテンシ（P95）等を算出し、PASS/FAIL を判定して標準出力に整形して出力。
    - CLI オプションで期間指定（--from, --to）と DB パス指定（--db）をサポート。
    - P95 計算、各種 SQL クエリのフォールバック（テーブルが存在しない場合の安全処理）を実装。

Changed
- DB 初期化/接続
  - monitoring 用のテーブル初期化 (init_monitoring_db) を実行することで監視テーブルの存在を保証（冪等）。
  - run_monitoring は環境に関わらず本番 sqlite_path を使用する設計の明文化（監視は本番データで行うため）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用することで本番 DB と完全分離。
- 設定の堅牢化
  - Settings の各プロパティで入力値チェックを強化（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の有効値検査）。
  - .env パーサの挙動を改善し、export プレフィックスやクォート・エスケープ・インラインコメント処理をサポート。

Fixed
- プロセス優先度設定に関するエラー耐性を向上
  - psutil の操作で AccessDenied, AttributeError, NotImplementedError が発生した場合、警告を出して処理を継続するよう修正。
- ポジションサイズ計算
  - aggregate cap 超過時のスケールダウンロジックを導入し、端数処理（lot_size 単位）と残余キャッシュの再配分を実装してより安定した割当を実現。
- .env ファイル読み込みの堅牢化
  - ファイルが読めない場合は warning を出して継続、読み込みの際のオーバーライド／保護（OS 環境変数保護）挙動を修正。

Notes / Known limitations
- ai.news_nlp の一部処理（大規模なエラーハンドリングや全ケースの DB 書き込みパス）はフェイルセーフ設計により、API が利用できない場合はスキップして継続する方針。ただし部分失敗時の復旧／ロールバックの挙動には注意が必要です。
- position_sizing の price 欠損（0.0）時の扱いについては TODO コメントが残っており、将来的に前日終値や取得原価を使ったフォールバックが推奨されます。
- research モジュールは DuckDB の存在・スキーマ（prices_daily / raw_financials 等）を前提としています。データが欠ける銘柄については None を返す仕様です。
- run_monitoring のポーリング間隔 MONITOR_POLL_INTERVAL は 1 秒以上の正の整数に制限しています。不正値はログ警告後にデフォルト 60 秒へフォールバックします。

Contributing
- バグ修正・機能追加の際は、.env 読み込みの安全性、DuckDB SQL の互換性、単元株（lot_size）処理などに注意して実装してください。

License
- このリポジトリのライセンス情報はプロジェクトルートの pyproject.toml 等を参照してください。
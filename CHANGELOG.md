Keep a Changelog
=================

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

注: 日付はこのコードベースのスナップショット時点 (2026-04-13) を使用しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- プロジェクト初期リリース。パッケージバージョンを __version__ = "0.1.0" に設定。
- 実行・監視用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine を組み立ててワンセッションを実行する起動スクリプト。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する動作をサポート（コメントに記載）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine.run_session() の実行を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（set_process_priority）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。無効値や非正の値はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。
    - 起動時にプロセス優先度を "high" に設定。

- 環境設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順と上書きルールを実装（OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env 行パーサを実装し、export プレフィックス、クォート文字、エスケープ、インラインコメントの扱いに対応。
  - 各種環境変数アクセス用プロパティを提供（パス、閾値、PID ファイル、PAPER_FILL_MODE の検証、KABUSYS_ENV/LOG_LEVEL のバリデーション等）。
  - settings = Settings() をエクスポート。

- モニタリング DB 初期化
  - init_monitoring_db を使用して起動時に監視用テーブルの存在を保証（冪等）。

- ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) を実装（Windows と POSIX の差分を吸収、権限不足時は警告を出してスキップ）。
  - set_cpu_affinity(cpu_count) を実装（指定なしなら変更なし、範囲チェックと権限例外処理あり）。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: スコア降順・同点は signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合は等金額にフォールバックして WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックして新規候補を除外。sell_codes により当日売却予定銘柄をエクスポージャー計算から除外可能。unknown セクターは制限対象外。
    - calc_regime_multiplier: レジーム (bull/neutral/bear) に応じた投下資金乗数を提供。未知レジームは 1.0 でフォールバックして WARNING を出力。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した株数算出。lot_size（単元）丸め、1銘柄上限 (max_position_pct)、aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した保守的コスト見積り、スケーリング後の残差配分ロジックを実装。

- リサーチ (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播を考慮）。
    - calc_value: raw_financials から最新財務データを取得し PER/ROE を算出（EPS が 0/欠損なら None）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで取得（horizons 検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装。有効レコードが 3 未満の場合 None を返す。
    - factor_summary, rank: 基本統計量計算・ランク変換ユーティリティを実装。
  - research パッケージの __all__ を整備し、zscore_normalize を kabusys.data.stats 経由でエクスポート。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols を集約して OpenAI API（gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む処理を実装。
  - 処理フロー:
    - 対象ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window。
    - 銘柄ごとに記事をトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大 _BATCH_SIZE（20）銘柄ずつバッチ送信、429/タイムアウト/5xx 等は指数バックオフでリトライ（最大 _MAX_RETRIES）。
    - レスポンスバリデーション、スコアを ±_SCORE_CLIP にクリップ。
    - 部分失敗時の被害を最小化するため、書き込みは対象コードを限定して DELETE→INSERT の置換を行う。
  - OpenAI クライアント生成は引数 api_key または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出。

- ツール
  - paper_verification_report: Paper Trading 用検証レポート生成 CLI を実装。
    - デフォルト DB: data/paper_trading.db、--db オプションや PAPER_TRADING_SQLITE_PATH 環境変数で上書き可。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - 判定基準（PASS/FAIL）を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - DB のテーブルが存在しない場合に備えて sqlite3.OperationalError を捕捉し、該当指標を N/A または 0 として出力するフォールバックを実装。
    - 出力は人間向けのテキストレポート形式。

Changed
- 主要な起動スクリプトで起動直後にプロセス優先度を "high" に設定する共通の振る舞いを導入（性能確保を目的）。
- DuckDB と SQLite の両方を使用するデータアクセス設計を明確化（分析は DuckDB、監視などのライトウェイト記録は SQLite）。

Fixed
- 多くの関数で欠損データに対する安全なフォールバックを実装（例: momentum/volatility のウィンドウ不足時、value の EPS=0 など）。
- 環境変数パーサの堅牢化（クォート・エスケープ・コメントの扱い、export 形式対応）。

Security
- OpenAI API キーの取り扱いは引数優先→環境変数の順で解決し、未設定時は明示的にエラーにすることで不注意なキー漏洩／未設定による不整合を防止。

Notes / Known behaviour
- run_monitoring は「監視用」DB として settings.sqlite_path（production 想定）を常に使用する設計になっている（KABUSYS_ENV に依存しない）。運用時の注意点として、paper_trading 環境で監視データを分離したい場合は sqlite_path を明示的に切り替える必要があります。
- PAPER_FILL_MODE 等の環境変数は値検証を行うため、不正な値を設定すると起動時に ValueError を送出します。
- process_priority の設定は権限不足（通常の UNIX 非 root 環境で負の nice 値を設定する等）や未対応 OS の場合は警告を出して安全にスキップします。

Acknowledgements
- 本リリースは、DuckDB を分析用データストア、SQLite を軽量ログ／監視用に使い分ける設計思想に基づいて構築されています。API 呼び出しや実オーダー発行については環境（paper_trading vs live）に応じて分離して安全に扱うよう配慮しています。
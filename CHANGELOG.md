CHANGELOG
=========

すべての変更は「Keep a Changelog」仕様に準拠して記載します。  
日付はコードベースから推定したリリース時点（ローカル作業日）を使用しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-16
--------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョン: __version__ = "0.1.0" を設定。
- 実行・監視エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と分離（data/paper_trading.db をデフォルト）。
    - BrokerClientFactory によりブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて別スレッドで実行。
    - 停止フラグ (data/stop_requested.flag) を検知すると安全に停止。PID 管理用ファイル (data/execution.pid) を利用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告のうえデフォルトにフォールバック。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用するよう明示。
    - 停止フラグ (data/stop_requested.flag) によるループ終了、KeyboardInterrupt のハンドリング、接続クローズを実装。
    - 起動時にプロセス優先度を "high" に設定する処理を呼び出す。
- 設定・環境変数管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
    - .env / .env.local の読み込み順序を実装。OS 環境変数は保護（上書き防止）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - 複雑な .env 行パース対応（export プレフィックス、クォート文字列のエスケープ、コメント処理等）。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、閾値、PID パス、環境判定など）をプロパティで取得。入力検証を追加（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の妥当性チェック）。
    - デフォルト値や paper_trading 用の別パス（PAPER_TRADING_SQLITE_PATH）をサポート。
- ポートフォリオ構築関連（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率での加重配分（全スコアが 0 の場合は等配分へフォールバックし WARNING を出力）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック（既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外）。"unknown" セクターは上限判定の対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数の決定（未知レジームは警告のうえ 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: weight/candidates/portfolio_value 等に基づいて発注株数を計算。
      - risk_based / equal / score の配分方式をサポート。
      - 単元（lot_size）丸め、1 銘柄上限、全体 aggregate cap によるスケーリング、cost_buffer の考慮、残差を用いた追加配分ロジックを実装。
      - 価格欠損や価格 <= 0 のケースはスキップしログ出力。
- Monitoring / DB 初期化ユーティリティ
  - 監視テーブルを保証する init_monitoring_db 呼び出しを実行開始時に行う（run_monitoring と run_execution）。
- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）の差分を吸収。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity を提供。権限不足や未対応環境では警告を出しスキップ。
- 研究・リサーチ機能（DuckDB ベース）
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials テーブルを参照してモメンタム・ボラ・バリュー系ファクターを計算。
    - 大きなウィンドウや欠損データ時の取り扱い（条件付き NULL）を考慮。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（任意ホライズン）を計算（LEAD を使用）。
    - calc_ic: スピアマンのランク相関（IC）計算。レコード不足や同値（ties）処理を考慮。
    - factor_summary / rank: 基本統計量の算出とランク関数を実装。
  - research/__init__.py に主要関数をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を読み込み、システム安定性（稼働率）、注文成功率・送信率、リスク却下数、レイテンシ統計（平均/最大/P95）を計算して標準出力へレポート出力。
    - 合格基準（閾値）を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - 日付範囲指定（--from/--to）や --db オプションをサポート。DB が存在しない場合にユーザーへ案内。
- AI ニュース NLP（部分実装）
  - ai/news_nlp.py を追加（OpenAI API を用いたニュースセンチメント集約・スコアリング）
    - ニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応）を提供。
    - バッチ処理（最大 20 銘柄）、トークン制御（各銘柄最大記事数・文字数）、API リトライ（429 / ネットワーク / 5xx に対して指数バックオフ）等の設計方針を実装。
    - レスポンス検証、スコアの ±1.0 クリップ、部分成功時の DB 更新保護（対象コード絞り込み）を計画。
    - 注意: ファイル末尾が途中で切れており、_fetch_articles など一部実装が未完成のように見える（このままでは実行時エラーになる可能性あり）。
- data layer
  - DuckDB と SQLite の両方を利用する設計を採用。DuckDB はリサーチ用集計、SQLite は監視・トレードログ等の永続化に使用。

Changed
- なし（初期実装のため）

Fixed
- なし（初期実装のため）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を参照する実装。未設定時は例外を投げる（漏洩防止の観点で必須化）。

Notes / 実行上の注意
- run_monitoring は監視用 DB に本番 sqlite_path を常に使用します。テスト・Paper Trading 環境でも本番 DB を参照しないよう注意してください（設計でそうしている）。
- run_execution は paper_trading 環境を想定した場合 paper_sqlite_path を使用するため、本番 DB と分離されます。
- ai/news_nlp.py は部分的に未完（ファイル末尾が途切れています）。OpenAI 連携部分を利用する前に残りの実装（記事フェッチ・API 呼び出しループ・DB 書き込みなど）を確認・完成させてください。
- 一部の処理（プロセス優先度変更、CPU affinity 設定）は実行環境や権限によって失敗する可能性があり、失敗時は警告でスキップする実装になっています。

今後の改善候補（推奨）
- ai/news_nlp の未完成部分を実装・テストする（特に _fetch_articles と DB 書き込みトランザクションの安全性）。
- portfolio モジュールのユニットテスト追加（edge case の確認: 価格欠損、lot_size が合わないケースなど）。
- run_monitoring / run_execution のログ出力を設定ファイルまたは Settings.log_level に応じて制御する。
- .env パーサーの追加ケース（複雑なエスケープ、マルチライン値など）への対応や既存テストの整備。

-----
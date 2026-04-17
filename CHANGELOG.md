# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-17

Added
- 実行／監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。Paper Trading 環境（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用することで本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag によるファイルフラグで制御。
- 設定管理
  - config.py: Settings クラスを導入し、環境変数から各種設定を取得。自動 .env 読み込み（.env → .env.local、OS 環境変数を保護する仕組み）および KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - 環境変数パーサーの強化: export プレフィックス、クォート文字、インラインコメント処理等を考慮した .env パース実装を追加。
  - 各種バリデーションを追加（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。
- Portfolio（ポートフォリオ構築）関連の純粋関数群を追加
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 発注株数算出（calc_position_sizes）。risk_based / equal / score の割当方式、単元株（lot_size）での丸め、aggregate cap（投下資金超過時のスケーリング）を実装。
  - portfolio パッケージの __all__ を整備。
- Research（研究）モジュールを追加
  - research.factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算（DuckDB を用いた SQL 実装）。MA200、ATR20、各種モメンタム等を計算。
  - research.feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman のランク相関）計算、ファクター統計サマリー、ランク関数等。外部依存なしで実装。
  - research パッケージを通じた zscore_normalize の再エクスポート。
- AI ニューススコアリング
  - ai.news_nlp: OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析の骨子を追加。銘柄ごとの記事集約、バッチ送信（最大 20 銘柄/コール）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリップ、ai_scores テーブルへの差分更新方針を設計。
  - ニュース収集ウィンドウ計算（JST→UTC 変換）ユーティリティを実装。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定を出力。CLI オプション (--from / --to / --db) をサポート。
- ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 固定ユーティリティを追加。アクセスが許可されない環境ではフォールバックして警告を出す実装。
- パッケージ情報
  - __init__.py にてパッケージの基本情報（__version__ = "0.1.0"）を設定。

Changed
- DB 接続・初期化の取り扱いを明確化
  - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db を冪等に呼び出し）。一方、Execution は paper_trading 環境で paper_sqlite_path を使用することで本番 DB と完全に分離。

Fixed
- 環境変数由来の不正値に対するフォールバック
  - MONITOR_POLL_INTERVAL のパースで 0 以下や非整数が与えられた場合にデフォルト値へフォールバックし、ログ出力で警告するように改善。
  - .env ファイル読み込み失敗時に警告（warnings.warn）を出すようにして無害化。
- 実行中のリソース解放
  - run_monitoring.run と run_execution.main で sqlite3 / duckdb 接続を finally ブロックで確実にクローズするように実装。

Security
- OpenAI API キー未指定時は明確にエラーとなるようにし、キー取得方法（引数優先→環境変数）を明示。

Notes / Known issues
- ai/news_nlp.py はニュース取得・API 呼び出しのロジックの大枠を実装していますが、提供されたソースは末尾が途中で切れている（ファイル末尾が不完全）ため、一部未実装／欠落箇所があります。実作業環境での完全な動作には残り実装（記事フェッチ関数、DB 書き込みトランザクションの実装等）が必要です。
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過小見積りされる可能性がある旨の TODO コメントを残しています。将来的に前日終値や取得原価でのフォールバックを検討。
- position_sizing:
  - lot_size の将来的な銘柄別対応に関する TODO（現状は全銘柄共通の単元数を想定）。
- DuckDB の executemany 周りの注意:
  - ai.news_nlp の設計注釈で DuckDB 0.10 の executemany 制約に注意喚起があり、実装時にパラメータ配列が空でないことを確認する必要がある。

内部設計メモ
- 設定ロード優先順位: OS 環境 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に探索し、見つからない場合は自動ロードをスキップする。
- 実行制御: run_execution / run_monitoring はファイルベースの停止フラグ（data/stop_requested.flag）および PID ファイルを利用して起動／停止を制御。
- リスク設定の既定値は run_execution 側で定義（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）。initial_portfolio_value は broker.get_available_cash() で取得。

---

今後の予定（短期）
- ai/news_nlp の未完部分を実装して end-to-end のニューススコアリングパイプラインを完成させる。
- portfolio の lot_size を銘柄毎にサポートする拡張、価格欠損時のフォールバックロジック追加。
- 単体テストと統合テストの充実（特に DuckDB / SQLite を用いる研究・検証機能周り）。
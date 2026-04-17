CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はリリース日を示します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 基本バージョン 0.1.0 を初回リリース。
- 実行／監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）検出で安全に終了する仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 環境設定管理モジュール（kabusys.config）を追加
  - .env/.env.local の自動読込機能（プロジェクトルート検出ロジック搭載）。
  - export プレフィックス、クォート値、インラインコメント等に対応する .env パーサ実装。
  - Settings クラスで各種環境変数をラップ（DB パス、KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。無効値は ValueError を投げて早期検出。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグに対応。
- 実行系コンポーネント（execution パッケージ周辺）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager などを組み立てる起動フローを run_execution に実装（本体モジュールは別ファイル想定）。
  - RiskConfig のデフォルト値を設定し、初期 available_cash は broker.get_available_cash() を用いる。
- 監視 DB 初期化ユーティリティ呼び出し（init_monitoring_db）を起動スクリプトで保証（冪等性）。
- ユーティリティ：プロセス優先度・CPU affinity 設定（kabusys.utils.process_priority）
  - Windows と POSIX (Linux/Mac/FreeBSD) を吸収。権限不足や未対応環境では警告を出してスキップ。
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
- Portfolio 構築モジュール（kabusys.portfolio）
  - portfolio_builder: シグナル選定（select_candidates）、等金額およびスコア重み（calc_equal_weights, calc_score_weights）。
  - risk_adjustment: セクター上限適用（apply_sector_cap）、レジーム倍率（calc_regime_multiplier）。unknown セクターはセクター上限の対象外とする仕様。
  - position_sizing: 各銘柄の発注株数算出（calc_position_sizes）。risk_based / equal / score の allocation_method をサポートし、lot_size 単位で丸め、aggregate cap によるスケーリングを実装。手数料・スリッページ見積り用の cost_buffer を考慮。
  - pure function 群として DB 参照は行わない設計（メモリ計算）。
  - いくつかの TODO コメント（将来的な lot_size 拡張、価格フォールバックなど）を含む。
- 研究／リサーチ機能（kabusys.research）
  - factor_research: momentum/volatility/value ファクター計算を DuckDB を用いて実装（prices_daily、raw_financials テーブル参照）。MA200、ATR20、各種モメンタム（1m/3m/6m）などを出力。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）やランク付けユーティリティ、ファクターの統計サマリー（factor_summary）。
  - DuckDB を使った単一クエリ中心の実装でパフォーマンスを考慮。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
  - バッチサイズ、トークン肥大対策（最大記事数・最大文字数）、429/5xx/タイムアウトに対する指数バックオフリトライ実装、レスポンスバリデーション、スコアクリッピング（±1.0）などの設計方針を反映。
  - calc_news_window と score_news API を実装（APIキー解決・ウィンドウ計算・エラーチェックを含む）。
  - 注: ファイルの末尾が途中で切れている（実装途中の状態でパッケージ内に存在）。
- ツール：Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - コマンドラインで paper_trading DB を解析して検証レポートを生成するスクリプトを追加。期間フィルタ（--from/--to）、--db オプションをサポート。
  - システム稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算して PASS/FAIL を判定する閾値を設定（稼働率 99.0%、注文成功率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms）。
  - P95 計算、SQL の存在チェック、sqlite3.OperationalError による耐障害性を実装。
- パッケージ情報
  - kabusys/__init__.py にバージョン 0.1.0 を追加。

Changed
- n/a（初回リリースのため変更履歴はなし）

Fixed
- n/a（初回リリースのため修正履歴はなし）

Known issues / Notes
- news_nlp の実装がファイル末尾で途中終了しており、完全な記事フェッチおよび OpenAI への送信処理が未完です。実行時に未実装・途中のコードが原因で例外が発生する可能性があります。継続実装／テストが必要です。
- portfolio.position_sizing, risk_adjustment にコメントで記載の将来的な改善点（銘柄別 lot_size サポート、価格フォールバックなど）が残っています。
- run_monitoring は Monitoring 用 DB として settings.sqlite_path（本番 DB）を常に使用する設計です。テスト環境で監視を走らせる際は注意してください（paper_trading 環境時の分離は run_execution 側でのみ実施）。
- process_priority/set_cpu_affinity は権限やプラットフォーム依存で失敗することがあるため、その場合は警告でスキップする挙動になっています。

Security
- 外部 API（OpenAI）用の API キーは環境変数 OPENAI_API_KEY か関数引数で提供する必要があります。キー未設定時は score_news で ValueError を投げて安全に終了します。

Acknowledgements
- 本リリースはモジュール設計とユーティリティ群に重点を置いた初版です。各モジュール（ExecutionEngine、Broker クライアント等）の詳細実装と統合テストは今後のイテレーションで整備予定です。
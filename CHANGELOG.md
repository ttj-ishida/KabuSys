CHANGELOG
=========

すべての日付は YYYY-MM-DD 形式。  
この CHANGELOG は "Keep a Changelog" の慣習に準拠しています。

Unreleased
----------

- （今後の変更をここに記載）

0.1.0 - 2026-04-17
------------------

Added
- 初回公開リリース。
- 実行/監視ランナーを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用する分離設計、BrokerClientFactory によるブローカー切替、ExecutionEngine のスレッド起動と停止フラグ（data/stop_requested.flag）対応、PID ファイル出力サポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理モジュールを追加
  - kabusys.config.Settings: .env 自動読み込み（.env ← .env.local、OS 環境変数優先）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化、値検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）、各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）や閾値をプロパティで提供。
  - .env パーサ実装: export 付き行、クォート文字列、インラインコメント処理、プロテクトされた OS 環境変数の上書き制御などに対応。
- ポートフォリオ構築ロジックを追加（kabusys.portfolio）
  - portfolio_builder: 候補選定（スコア降順・タイブレーク）、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights、スコア全て 0 の場合のフォールバック警告)。
  - risk_adjustment: セクター集中制限の apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームは警告のうえフォールバック）。
  - position_sizing: 複数の割当方法に対応(calc_position_sizes)。risk_based / equal / score の各方式、単元株（lot_size）丸め、1 銘柄上限・集計上限（aggregate cap）に基づくスケールダウン、cost_buffer（手数料・スリッページ見積）考慮、残差配分ロジックを実装。
- 監視・実行用の DB 初期化ユーティリティ呼び出しを追加（init_monitoring_db を起動時に呼ぶことで監視テーブルの存在を保証）。
- Process 優先度・CPU affinity ユーティリティを追加（kabusys.utils.process_priority）
  - set_process_priority: Windows / POSIX(Linux, Darwin, FreeBSD) に対応した優先度設定。権限不足や未対応 OS の場合に警告でスキップ。
  - set_cpu_affinity: 指定コア数へのピン留め（入力検証、権限不足時は警告でスキップ）。
- Research / データ処理機能を追加（kabusys.research）
  - factor_research: DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）。各関数は prices_daily / raw_financials を利用し、データ不足時に None を返す安全な設計。
  - feature_exploration: 将来リターン calc_forward_returns、スピアマンランク相関による IC 計算(calc_ic)、ランク関数、ファクター統計サマリ(factor_summary) を実装。外部ライブラリ非依存で純粋 Python 実装。
- ニュース NLP モジュールを追加（kabusys.ai.news_nlp）
  - raw_news から銘柄別に記事を集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出し ai_scores に保存する処理設計を導入。バッチ処理、トークン肥大対策（記事数・文字数制限）、リトライポリシー、レスポンス検証、スコアクリップ等を設計段階で整備。ニュースウィンドウ計算(calc_news_window) を提供。
- ツールを追加
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、P95 レイテンシ等を算出・判定し標準出力にレポート表示。閾値（稼働率 99% 等）・P95 計算・日付フィルタ対応を実装。
- パッケージメタ情報
  - kabusys.__init__.py に __version__ = "0.1.0" を設定。

Changed
- DB 分離ポリシーを明示
  - 監視（run_monitoring）は常に本番 sqlite_path を使用する（環境に依存しない監視データの一元化）。
  - 実行エンジン（run_execution）は paper_trading 環境時に専用 SQLite（paper_sqlite_path）を使用し、本番データと完全に分離する設計。
- 実行フローのフェイルセーフ強化
  - run_monitoring と run_execution ともに停止フラグファイルの検出により安全に停止できるように設計。
  - run_monitoring のポーリング中に monitor.check_once() が例外を投げてもループを継続し、次のポーリングまで待機するように変更（例外時に logger.exception を出力）。
- .env 読み込みの優先度・保護ルールを明文化（OS 環境変数は保護され、.env.local は .env を上書き可能）。

Fixed
- 環境変数の数値パースでのフォールバック処理
  - MONITOR_POLL_INTERVAL の値が不正（0 / 負 / 非整数）の場合にデフォルト 60 秒へフォールバックし、警告を出力するよう改善。
- DuckDB executemany の事前チェックに配慮（ai モジュール設計にコメントで留意）。tools.paper_verification_report でも SQLite のテーブル不在時に OperationalError を許容してデフォルト値を返す堅牢化を実施。

Notes / その他
- 多くのデータ処理機能（research や ai/nlp、portfolio 等）は DuckDB / SQLite のテーブル構造に依存します。最小限の存在チェックやデータ不足ハンドリングを行っていますが、実データ投入前にスキーマ準備（prices_daily, raw_financials, raw_news, trade_logs, risk_logs, system_status など）を推奨します。
- OpenAI API を用いる ai/news_nlp は API キーが必須（環境変数 OPENAI_API_KEY または関数引数で提供）。API エラー時のリトライ・フォールバックを設計に含めていますが、実行時の課金やレート制限に注意してください。

Contributing
- バグ報告・機能提案は issue を作成してください。開発時の .env 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

License
- ソース内ライセンス記載に従ってください。
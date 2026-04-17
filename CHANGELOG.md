CHANGELOG
=========

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

フォーマットのルール:
- 変更はカテゴリ別に記載（Added / Changed / Fixed / Deprecated / Removed / Security）
- バージョンごとに日付を付与

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
-------------------

Added
- 初回公開: KabuSys コードベースの基本機能を実装・追加。
  - 実行系 / 監視:
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB（data/paper_trading.db 想定）と MockBrokerClient を使用して本番 DB と分離。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag ファイルで制御。
    - 両スクリプトとも起動時にプロセス優先度を設定する機能を呼び出す（utils.process_priority.set_process_priority）。
  - 設定管理:
    - config.Settings: 環境変数・.env ファイルからの設定読み込み機能を実装。自動 .env ロード（.env → .env.local、OS 環境変数を保護）をサポート。多くの設定プロパティ（DB パス、API トークン、しきい値、環境判定など）を用意。
    - .env パースの強化: export 形式、シングル/ダブルクォート内のエスケープ、およびインラインコメント処理に対応。
  - ポートフォリオ構築:
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - portfolio.position_sizing: position sizing（calc_position_sizes）を実装。risk_based / equal / score の割当方式をサポートし、lot_size 単位で丸め、aggregate cap によるスケーリングを実装。手数料・スリッページの保守的見積り（cost_buffer）を考慮。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
  - 研究用モジュール:
    - research.factor_research: Momentum / Volatility / Value ファクター計算を実装（DuckDB 経由で prices_daily や raw_financials を参照）。MA200、ATR20、各種リターン等を算出。
    - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）・ランク（rank）・統計サマリー（factor_summary）を実装。外部ライブラリに依存せず、標準ライブラリのみで処理。
    - research パッケージは zscore_normalize（kabusys.data.stats から）を再エクスポート。
  - AI / ニュース解析:
    - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini、JSON Mode）でバッチ処理し銘柄ごとのセンチメントを ai_scores テーブルへ書き込むためのスコアリング機能を追加。バッチサイズ、最大記事数、文字数制限、リトライ（指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ等を設計。
    - calc_news_window 関数でニュース収集ウィンドウ（JST→UTC 変換）を提供。
  - ツール:
    - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI を追加。システム稼働率・注文成功率・送信率・レイテンシ等を集計し PASS/FAIL を判定。コマンドライン引数 --from/--to/--db に対応。
  - ユーティリティ:
    - utils.process_priority: クロスプラットフォームでプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装（psutil を使用）。Windows と POSIX 系の差分を吸収。
  - DB 初期化:
    - monitoring_db.init_monitoring_db を利用して監視用テーブルの冪等な初期化を実行（run_monitoring/run_execution）。

Changed
- 監視の DB ハンドリング:
  - run_monitoring はコメントどおり KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを書き込む（監視は本番対象で稼働状況を追う想定）。
- ExecutionEngine 構成:
  - run_execution において paper_trading 環境時は settings.paper_sqlite_path を採用して本番 DB から分離。RiskManager の初期値に broker.get_available_cash() を使用して initial_portfolio_value を設定。
- .env 読み込みの優先度:
  - OS 環境変数 > .env.local > .env の順でロード（.env.local は上書き可能）。

Fixed
- .env パーサーの堅牢性向上:
  - export KEY= 値、クォート内バックスラッシュエスケープ、インラインコメントの扱い、空行／コメント行除外等に対応し、想定外の行フォーマットで無効化するよう修正。
- 各モジュールで None / 空データへの安全ガードを追加（例: factor / latency / order 統計取得時の sqlite3.OperationalError をハンドリングして空結果でフォールバック）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI 使用時は OPENAI_API_KEY（または score_news の api_key 引数）必須。未設定時は明示的に ValueError を送出して失敗する仕様。

Notes / Known issues
- ai/news_nlp.py は大枠の設計と多くの処理フローを実装済みだが、ソースが途中で切れている（ファイル末尾が不完全）ため、_fetch_articles 等の内部関数や最終的な書き込み処理が未完の可能性があります。実運用前に該当箇所の実装・テストが必要です。
- position_sizing や apply_sector_cap 内の一部 TODO（価格欠損時のフォールバック等）が残っています。実データの欠損ケースに対する追加処理を検討してください。
- duckdb を用いたクエリの正当性とパフォーマンスはデータ量に依存するため、運用環境での実データを用いたベンチマークを推奨します。
- run_monitoring/run_execution の停止制御はファイルフラグ方式（data/stop_requested.flag）で行っているため、運用スクリプト側でのフラグ管理ルール（作成・削除権限等）を整備してください。

問い合わせ / 貢献
- このリポジトリへの貢献、バグ報告、設計質問は issue を立ててください。詳細な再現手順やログを添付いただくと対応が早くなります。
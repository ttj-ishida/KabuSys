CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に従います。

0.1.0 - 2026-04-16
-----------------

Added
- パッケージ初期リリース。バージョンは kabusys.__version__ = "0.1.0"。
- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用。
    - 停止フラグ (data/stop_requested.flag) による優雅な終了処理を実装。
    - DuckDB と sqlite の接続初期化処理を含む（init_monitoring_db 呼び出し）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 等の組み立てを行い、ExecutionEngine を別スレッドで実行。
    - 停止フラグの検知でエンジンを停止する仕組みと PID ファイル管理を実装。
- 設定管理
  - kabusys.config.Settings を導入。
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - export 文・クォート・インラインコメント等に対応した .env パーサ実装。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）と各種パス/閾値プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/MEM/DISK閾値等）。
    - 必須変数未設定時は分かりやすいエラーを投げる _require() を提供。
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates, calc_equal_weights, calc_score_weights を実装。calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes を実装。risk_based / equal / score の配分方法、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を考慮。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap によるセクター集中上限チェック（sell_codes を考慮）と calc_regime_multiplier（regime に応じた投下資金乗数: bull/neutral/bear）を実装。
- ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority(level) により Windows/Linux/macOS の差分を吸収して優先度設定。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン固定（指定なしならスキップ）。
    - アクセス権限不足や未対応 OS に対しては安全にログ警告でスキップする実装。
- 研究 / リサーチ
  - kabusys.research.factor_research
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB 経由で prices_daily / raw_financials を参照し、各種ウィンドウサイズや欠損取り扱いを明示。
  - kabusys.research.feature_exploration
    - calc_forward_returns（可変ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（count/mean/std/min/max/median）、rank（同順位は平均ランク）を実装。外部依存を持たない純 Python 実装。
  - research パッケージの __all__ を整備（zscore_normalize を data.stats から再エクスポート）。
- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading の検証レポート生成ツールを追加。期間指定（--from / --to）と DB 指定（--db または PAPER_TRADING_SQLITE_PATH）に対応。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標取得と PASS/FAIL 判定ロジックを実装（閾値はソース内に定義）。
- AI / ニュース処理（部分実装）
  - kabusys.ai.news_nlp
    - ニュース記事を OpenAI（gpt-4o-mini）でスコアリングし、ai_scores テーブルへ書き込む処理の設計・多数の実装済みユーティリティを追加。
    - バッチサイズ、トークン肥大化対策（記事数・文字数トリム）、API リトライ（429/タイムアウト/5xx に対する指数バックオフ）、レスポンス検証、スコアクリッピングを実装。
    - calc_news_window(target_date) を提供（JST ベースの収集ウィンドウを UTC naive datetime で返す）。
    - 注意: score_news 関数はソースが途中で切れており（ファイル末尾の途切れ）、部分実装であるため完全動作は未確認。
- パッケージ初期化
  - kabusys.__init__ にてパッケージ名と __version__ を定義。
  - kabusys.portfolio / research / utils / tools 等の __init__.py を整備してエクスポートを整理。

Changed
- （初回リリースのため該当なし。ただし、各モジュールで堅牢性・欠損値・例外処理を強化している箇所あり。）
  - 環境変数読み込み周りで OS 環境変数を保護する protected 対応や .env.local の上書き優先度を明確に実装。

Fixed
- 初回リリースとして、以下のようなロバストネス改善を実施
  - MONITOR_POLL_INTERVAL の不正値に対してデフォルトへフォールバックするログ出力を追加。
  - init_monitoring_db を冪等で呼び出し、監視テーブルが存在しないケースでも安全に初期化。
  - set_process_priority / set_cpu_affinity が権限不足や未対応環境で例外を投げないよう警告ログでスキップ。

Known issues / Notes
- ai/news_nlp.py の score_news 関数がファイル末尾で途中（"if not articl" で途切れ）になっており、完全実装が必要。現状ではニュース NLP のフルパイプラインは未完。
- position_sizing.calc_position_sizes 内に将来的な拡張 TODO：
  - 銘柄別の lot_size をサポートする等の拡張が想定されている。
- apply_sector_cap は price_map に欠損（価格=0.0）があるとエクスポージャーを過少評価してしまう旨の TODO コメントあり。前日終値などのフォールバック価格導入が検討事項。
- DuckDB/SQLite のテーブルスキーマや init_monitoring_db の詳細は別モジュールに依存するため、データベース側で適切なスキーマが必要。
- OpenAI を利用する機能は API キー管理とレート制限に注意。score_news は API キー未指定時に ValueError を投げる仕様。

Deprecated
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- OpenAI API キー等の機密情報は Settings 経由で環境変数として管理する設計。 .env の自動読み込みはプロジェクトルート検出に依存し、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

この CHANGELOG はコードベースの現状から推測して作成しています。実装意図・未実装箇所・将来の改善点はソース中のコメントや TODO を参照してください。
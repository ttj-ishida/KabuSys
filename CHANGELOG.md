CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

v0.1.0 - 2026-04-12
-------------------

Added
- 全体
  - 初版リリース。モジュール群（設定、実行・監視ランナー、ポートフォリオ構築、リサーチ、AI ニューススコアリング、ユーティリティ、ツール）が追加されました。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を設定。

- 設定管理 (src/kabusys/config.py)
  - .env 自動ロード実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env と .env.local の読み込み順序および OS 環境変数の保護（protected）をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化のサポート。
  - .env の行パーサーを実装（export プレフィックス、クォート処理、インラインコメントの扱いを考慮）。
  - Settings クラスを実装。J-Quants / kabu API / LINE / DB / 監視 / システム設定等のプロパティを提供。
  - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - paper_trading 用データベースパス（PAPER_TRADING_SQLITE_PATH）とその他監視閾値、PID/KILL フラグパスの設定を提供。

- 実行 / 監視ランナー
  - run_execution.py
    - ExecutionEngine 起動エントリポイントを追加。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading のときは paper_sqlite_path を使用して本番 DB と分離する設計。
    - BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - DuckDB 接続を ExecutionEngine に渡す。
    - RiskManager のデフォルト構成値を設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動エントリポイントを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（デフォルト 60 秒）を上書き可能。
    - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用（監視用 DB の初期化を保証）。
    - プロセス優先度を "high" に設定し、SQLite / DuckDB 接続を作成して SystemMonitor.check_once を定期実行。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しが実行スクリプト側で行われ、監視テーブルの存在を冪等に保証（両 runner で実施）。

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - portfolio_builder.py
    - select_candidates, calc_equal_weights, calc_score_weights を実装（スコア降順ソート、同点時のタイブレーク等）。
  - risk_adjustment.py
    - apply_sector_cap: 既存保有のセクターエクスポージャを計算してセクター過集中を防ぐフィルタを実装（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market レジーム ("bull","neutral","bear") に応じた投下資金乗数を提供（デフォルトフォールバック含む）。
  - position_sizing.py
    - calc_position_sizes: risk_based / equal / score の allocation ロジックを実装。単元株（lot_size）で丸め、per-stock と aggregate のキャップ、cost_buffer を考慮したスケーリング処理を実装。

- 研究 (src/kabusys/research/*)
  - factor_research.py
    - DuckDB を用いたファクター計算実装（モメンタム: 1M/3M/6M/MA200乖離、ボラティリティ: ATR20/相対ATR/出来高指標、バリュー: PER/ROE）。
    - 各関数は target_date を引数に取り、prices_daily / raw_financials テーブルのみ参照する設計。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、factor_summary、rank を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで統計処理を実行。

- AI ニューススコアリング (src/kabusys/ai/news_nlp.py)
  - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) にバッチで問い合わせ、銘柄ごとのスコアを ai_scores テーブルへ書き込む処理を実装。
  - ニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供（calc_news_window）。
  - 最大チャンクサイズ、最大記事数・文字数トリム、スコアの ±1.0 クリップ、エラーハンドリング（429/ネットワーク/5xx に対する指数バックオフ）を実装。
  - API キーの解決（引数 > 環境変数 OPENAI_API_KEY）と未設定時の ValueError を実装。
  - レスポンス検証と部分更新（該当コードのみ DELETE→INSERT）を行う方針を採用。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 検証レポート生成 CLI を追加。--from / --to / --db オプションをサポート。
  - デフォルト DB パスは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）。
  - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を集計し、閾値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）で PASS/FAIL を判定して標準出力に整形出力。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) を実装し、Windows と POSIX(Linux/Mac/FreeBSD) を吸収。権限不足等を安全にスキップ。
  - set_cpu_affinity(cpu_count) を実装。指定コア数でプロセスをピン留めする機能（未サポート環境は警告でスキップ）。

- パッケージ API エクスポート
  - kabusys.research と kabusys.portfolio の __init__ で主要関数を再エクスポート。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- 環境変数読み込み時に OS 環境変数を protected として上書きを防ぐことで、テスト時や実行時の誤上書きリスクを低減。

Notes / Implementation details
- SQLite と DuckDB の併用設計
  - 監視データは SQLite に保存（monitoring 用テーブルの初期化を実行スクリプト側で保証）。
  - 時系列・ファクター計算等の分析用途には DuckDB を使用する設計。
- Paper trading と Live の分離
  - KABUSYS_ENV=paper_trading の場合、実行時に専用の paper_trading DB を用い、本番 DB と完全分離する設計思想を採用。
- フェイルセーフ設計
  - 外部 API 呼び出し（OpenAI やブローカー）失敗時は例外を適切に扱い、可能な限り他処理を継続するように実装。
  - run_monitoring のポーリングループは check_once の例外をログに記録して次回ポーリングへ継続する挙動。

Deprecated
- なし

Unreleased
- 今後のリリースで想定している改善案（未実装）
  - position_sizing の銘柄別 lot_size サポート（stocks マスタから取得）
  - apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価など）
  - news_nlp の並列化やRateLimit最適化、OpenAI レスポンスのより厳密なスキーマ検証
  - テストカバレッジの強化と CI ワークフローの追加

参考
- 主なファイル:
  - src/kabusys/config.py
  - src/kabusys/run_monitoring.py
  - src/kabusys/run_execution.py
  - src/kabusys/portfolio/
  - src/kabusys/research/
  - src/kabusys/ai/news_nlp.py
  - src/kabusys/tools/paper_verification_report.py
  - src/kabusys/utils/process_priority.py

--- End of changelog ---
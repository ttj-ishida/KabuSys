Keep a Changelog
=================

すべての重要な変更を記録します。  
このファイルは "Keep a Changelog" の形式に従います。  

フォーマット:
- 変更はセクション (Added, Changed, Fixed, ...) に分類します。
- バージョンごとに逆順（最新が上）で並べます。

Unreleased
----------

（未リリースの変更はここに記載してください）

0.1.0 - 2026-04-13
-----------------

Added
- 初期リリース: KabuSys — 日本株自動売買システムの基本機能群を実装。
- 実行/監視用エントリポイントを提供:
  - run_execution.py: ExecutionEngine の起動スクリプト。起動時にプロセス優先度を設定し、SQLite / DuckDB に接続して注文処理セッションを実行。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番用 sqlite_path を使用。
- 実行環境分離（Paper Trading）:
  - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離。
  - PAPER_FILL_MODE により Paper Trading の約定振る舞いを指定可能（instant / partial / never / reject）。
- 設定管理モジュール (kabusys.config):
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml から探索）。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサは export 形式・クォート・インラインコメント等に対応。
  - Settings クラス経由で各種設定をプロパティで取得（DB パス、PID ファイル、閾値、環境種別判定等）。
  - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
- ポートフォリオ構築（kabusys.portfolio）:
  - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier)。
  - position_sizing: 発注株数計算 (calc_position_sizes)。risk_based / equal / score の配分方式、lot_size（単元）丸め、aggregate cap スケーリング、コストバッファ考慮等を実装。
- リサーチモジュール（kabusys.research）:
  - factor_research: momentum / volatility / value ファクター計算（DuckDB を利用、prices_daily / raw_financials を参照）。MA200、ATR、リターン等を計算。
  - feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（calc_ic）、ファクター統計サマリ (factor_summary)、ランク変換 (rank)。
  - research パッケージは zscore_normalize を含めた主要関数を再エクスポート。
- AI ニュース NLP（kabusys.ai.news_nlp）:
  - raw_news を集約して OpenAI API (gpt-4o-mini) にバッチ送信、銘柄ごとのセンチメントスコアを ai_scores テーブルへ保存する機能。
  - バッチサイズ、トークン肥大対策（記事数、文字数上限）、最大リトライ、指数バックオフ、レスポンス検証、スコアの ±1.0 クリップ等を実装。
  - API キーは引数または OPENAI_API_KEY 環境変数で指定。未指定時は ValueError を送出。
  - ニュース収集ウィンドウ（日次, JST→UTC 変換）を calc_news_window で明示的に計算し、ルックアヘッドバイアスを排除。
- 監視 DB 初期化ユーティリティ:
  - init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。
- 実行コンポーネント（Execution）:
  - BrokerClientFactory による Broker クライアントの生成（Paper と Live を切り替え）。
  - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組立てと起動。
  - RiskConfig にデフォルトの閾値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 設定, max_drawdown 等）を設定。
- ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプト。期間指定 CLI (--from, --to, --db) に対応。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出して PASS/FAIL 判定を出力。閾値はソース内定義（稼働率 99%、注文成功率 90% など）。
- プラットフォームユーティリティ（kabusys.utils.process_priority）:
  - set_process_priority(level): Windows と POSIX(Linux/Mac/FreeBSD) の差分を吸収してプロセス優先度を設定。権限不足や未対応 OS は警告を出してスキップ。
  - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を設定（権限不足や未対応時は警告を出す）。
- パッケージ情報:
  - パッケージバージョン __version__ = "0.1.0" を追加。

Changed
- （初期リリースにつき該当なし）

Fixed
- （初期リリースにつき該当なし）

Deprecated
- （初期リリースにつき該当なし）

Removed
- （初期リリースにつき該当なし）

Security
- OpenAI API キーは環境変数または明示的引数でのみ使用するように設計。未設定時は処理を中断してキーの漏洩を防止。

Notes / Implementation details
- DuckDB をリサーチ・AI 用データ加工に使用。prices_daily / raw_financials / raw_news / ai_scores 等のテーブルを前提としている。
- run_monitoring は監視 DB に常に本番 sqlite_path を使用する設計（誤って paper_trading DB を監視しないための保守的設計）。
- .env ローダはプロジェクトルート検出に __file__ ベースの親ディレクトリ探索を使用するため、CWD に依存しない。
- calc_position_sizes 等は全て純粋関数（副作用なし）で設計、将来的なユニットテストを容易にする。
- Paper Trading と Live の DB を厳密に分離し、本番データの汚染を防ぐ。
- いくつかの箇所で入力バリデーション・不正値処理（例: MONITOR_POLL_INTERVAL の不正値フォールバック、PAPER_FILL_MODE の検証、horizons の検証）を行っている。

今後の予定（想定）
- 更なる単体テスト追加（pure 関数群の網羅）。
- BrokerClient の具体実装（kabuステーション/Mock）の増強とエンドツーエンド検証。
- AI スコアリングのメタデータ保存や結果の履歴管理機能追加。
- 銘柄別 lot_size 対応（現在はグローバル lot_size）。
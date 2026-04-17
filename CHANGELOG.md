# Changelog

すべての注目すべき変更点を記載します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- バージョン毎に Added / Changed / Fixed / Removed 等で分類
- 日付は YYYY-MM-DD 形式

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-17

### Added
- プロジェクト初期リリース。以下の主要機能・モジュールを追加。
  - 実行/監視ランナー
    - run_execution.py
      - ExecutionEngine の起動スクリプトを追加。
      - KABUSYS_ENV が paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db 既定）を使用して本番 DB と完全分離。
      - 実行中に data/stop_requested.flag を検知すると安全に停止する仕組みを実装。
      - data/execution.pid を PID ファイルとして利用。
      - スレッドでエンジンを起動し、停止フラグ検出でエンジン.stop() を呼び停止を行う。
      - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を利用）。
      - Execution 用コンポーネント群（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立てる。
      - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec 等）を定義、initial_portfolio_value は broker.get_available_cash() を参照。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
      - data/stop_requested.flag を検知してループを終了。KeyboardInterrupt にも対応。
      - 起動時にプロセス優先度を "high" に設定。
  - 設定管理
    - config.Settings クラスを実装。
      - 環境変数の取得ラッパー（各 API トークン、DB パス、各種閾値、KABUSYS_ENV/LOG_LEVEL 等）。
      - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許容）。
      - env 値の検証（development/paper_trading/live のみ許容）と利便性プロパティ（is_live / is_paper / is_dev）。
    - .env 自動読み込み
      - プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env → .env.local の順で環境変数を読み込む（OS 環境変数は保護）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
      - .env パーサーは export 形式、クォート、バックスラッシュエスケープ、インラインコメントを扱えるよう実装。
  - Portfolio（銘柄選定・配分・分散制御・株数計算）
    - portfolio.portfolio_builder
      - select_candidates: スコア降順・タイブレークに signal_rank を使用して候補選定。
      - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア全て 0 の場合は等分にフォールバック）。
    - portfolio.risk_adjustment
      - apply_sector_cap: 既存保有を考慮したセクター集中上限（max_sector_pct）適用。unknown セクターは上限適用外。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは警告して 1.0 フォールバック。
    - portfolio.position_sizing
      - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") に基づく株数決定を実装。
      - 単元株（lot_size）丸め、max_per_stock（portfolio_value * max_position_pct）制約、コストバッファ cost_buffer を考慮した aggregate cap によるスケーリングと残差配分ロジックを実装。
      - price 欠損時の安全スキップやログ出力を含む堅牢な実装。
  - Research（ファクター計算・特徴量解析）
    - research.factor_research
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。十分な履歴が無ければ None を返す。
      - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高変化率を計算（データ不足で None）。
      - calc_value: raw_financials から最新財務を取得して PER/ROE を計算。
      - DuckDB 接続を受け、prices_daily / raw_financials を参照する設計。
    - research.feature_exploration
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。horizons の検証あり。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足（<3 レコード）時は None。
      - factor_summary / rank: 基本統計量の集計、ランク付けユーティリティを提供。
  - AI / ニュース NLP
    - ai.news_nlp
      - ニュース記事を OpenAI API（gpt-4o-mini）でセンチメントスコア化して ai_scores テーブルへ書き込む処理を実装（score_news）。
      - 処理設計: タイムウィンドウ集約、銘柄ごとに記事をトリム（上限記事数・文字数）、最大 20 銘柄バッチ、429/5xx/ネットワーク断に対する指数バックオフリトライ、レスポンス検証、±1.0 にクリップ。
      - calc_news_window: JST ベースのニュース収集ウィンドウ計算を提供（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
      - API キー解決は引数 > 環境変数 OPENAI_API_KEY。未設定時は ValueError。
      - （注）ファイル末尾が切れている部分あり（実装継続の余地あり）。
  - ユーティリティ
    - utils.process_priority
      - set_process_priority(level): Windows / POSIX の差を吸収してプロセス優先度を設定（"high" / "normal" / "low"）。権限不足や未対応 OS では警告してスキップ。
      - set_cpu_affinity(cpu_count): 最初の N コアへ固定。引数検証とエラーハンドリングを実装。
  - ツール
    - tools.paper_verification_report
      - Paper Trading の検証レポートを生成する CLI ツールを追加。
      - コマンドライン引数 --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数でも DB 指定可。
      - レポートは稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を算出し、閾値（稼働率>=99%, fill>=90%, send>=95%, P95<=200ms）で PASS/FAIL を判定。
      - レコード不足やテーブル欠損時の安全処理および出力フォーマットを実装。
  - パッケージメタ情報
    - kabusys.__version__ を "0.1.0" に設定。
  - DB 初期化
    - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの冪等な初期化を各ランナーで保証。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Implementation details
- 環境変数の自動読み込みは OS の既存環境変数を上書きしない仕様。ただし .env.local は override=True で読み込まれる（protected set により OS 既存キーは保持）。
- DuckDB と SQLite を併用する設計。分析系は DuckDB（高速な列指向処理）、監視/実行ログは SQLite を想定。
- 多くの関数は「DB 参照なし（純粋関数）」として設計されており、ユニットテストが適用しやすい。
- ai.news_nlp の score_news はエラー耐性を重視し、部分失敗時に他銘柄の既存スコアを保護する書き換え戦略を採用している（DELETE→INSERT を銘柄絞りで制御）。
- 一部ファイル（ai.news_nlp）の末尾が切れているため、そこは今後継続実装・テストが必要。

---

今後の予定 / TODO（抜粋）
- ai.news_nlp の完全実装とエンドツーエンドテストの追加。
- price 欠損時のフォールバック価格（前日終値など）導入によるリスク評価改善（position_sizing 内 TODO）。
- 銘柄別 lot_size 対応（stocks マスタ導入）および position_sizing の拡張。
- より細かなログ・メトリクス収集と自動アラート（監視モジュール拡張）。

以上。
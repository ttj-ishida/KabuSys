CHANGELOG
=========

すべての注目すべき変更を時系列で記録します。  
このファイルは "Keep a Changelog" の慣例に従っています。

フォーマット:
- 変更はカテゴリ別に整理（Added / Changed / Fixed / Removed / Deprecated）
- バージョン見出しにはリリース日を併記

[Unreleased]
------------

（次のリリースに向けた未リリースの変更はここに記載します）

0.1.0 - 2026-04-16
-----------------

Added
- 初回リリース: KabuSys コア機能群を追加。
- 実行スクリプト
  - run_execution.py を追加。
    - プロセス開始時に優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、本番 DB と完全分離された PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を選択可能（BrokerClientFactory による選択ロジック）。
    - ExecutionEngine の起動・管理（pid ファイル、停止フラグ検出、スレッドでの実行、停止時のクリーンアップ）を実装。
    - RiskManager、OrderManager、Reconciler、OrderRepository の組み立て・設定（RiskConfig のデフォルト値を含む）。
  - run_monitoring.py を追加。
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する仕様。
    - stop_requested.flag 検出による安全な停止処理を実装。
- 設定管理
  - config.Settings を追加。
    - .env 自動ロード機構（プロジェクトルート自動検出: .git または pyproject.toml を上位ディレクトリから探索）。
    - .env / .env.local の読み込み順序と override / protected ルール（OS 環境変数を保護）。
    - .env のパーサーは export 形式、クォート文字列、インラインコメント処理、無効行のスキップに対応。
    - 多数のプロパティを提供（J-Quants・kabuAPI・LINE・DB パス・監視閾値・環境判定など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ有効）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選抜（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 株数決定ロジック（calc_position_sizes）
    - risk_based / equal / score の配分方式に対応。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap スケーリング、cost_buffer（手数料・スリッページ考慮）を実装。
    - 価格欠損時のスキップや安全弁（_max_per_stock）を実装。
- リサーチ / ファクター計算
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 経由で prices_daily / raw_financials を参照）。
    - mom_1m / mom_3m / mom_6m / ma200_dev、atr_20 / atr_pct / avg_turnover / volume_ratio、per / roe を計算。
    - ウィンドウサイズ・欠損ハンドリングを考慮。
  - research.feature_exploration: 将来リターン算出(calc_forward_returns)、IC（calc_ic）、rank、factor_summary を追加。外部依存（pandas 等）なしで実装。
  - research パッケージは zscore_normalize を外部（kabusys.data.stats）から再エクスポート。
- AI ニュース NLP
  - ai.news_nlp を追加（ニュースセンチメントスコアの生成ロジック）。
    - OpenAI（gpt-4o-mini）を用いたバッチスコアリング、JSON モード出力の厳密なバリデーション、スコアの ±1.0 クリップ。
    - 前日15:00 JST ～ 当日08:30 JST のウィンドウ定義（UTC への変換）を提供（calc_news_window）。
    - 1 銘柄あたりの記事数・文字数上限 (_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK)、バッチサイズ、リトライ（指数バックオフ）を実装。
    - API キー解決（引数または環境変数 OPENAI_API_KEY）と未設定時のエラー。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・P95 レイテンシ等を集計。
    - パス/フェイル基準（稼働率・成功率・送信率・P95 レイテンシ）を導入し、CLI オプションで期間指定（--from / --to / --db）可能。
    - P95 算出、欠損ハンドリング、レポート出力フォーマットを実装。
- ユーティリティ
  - utils.process_priority: プロセス優先度設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応し、psutil を用いて優先度や CPU affinity を設定。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足時は警告ログでスキップ。
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- .env 自動ロードの挙動
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - プロジェクトルートが特定できない場合は自動ロードをスキップ（配布後の環境でも安全）。
- run_monitoring の挙動
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバックと警告を追加。
  - 監視は常に Settings.sqlite_path（本番 DB）を使う旨を明記（環境に依存しない監視 DB ポリシー）。

Fixed
- 各種 NULL / データ欠損に対する堅牢性を強化（ファクター計算、ATR / MA 計算、P95 算出、position sizing の価格欠損時のスキップなど）。

Removed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Notes / Breaking changes
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。監視データを Paper Trading と共有したくない場合は注意してください。
- Paper Trading 実行時はデフォルトで data/paper_trading.db を使用し、本番 DB と完全に分離されます。環境変数 PAPER_TRADING_SQLITE_PATH で変更可能です。
- process_priority / set_cpu_affinity は権限やプラットフォームによっては効果がなく、失敗時は警告を出して処理を継続します。

開発者向けメモ
- ドキュメント参照: PortfolioConstruction.md / StrategyModel.md に基づいた実装が多く含まれます（実リポジトリに同梱されているものを参照してください）。
- DuckDB 接続を用いる research / ai モジュールはローカルの DuckDB ファイル（Settings.duckdb_path）または外部で作成した DB を参照します。

--- 

（以降のリリースでは Unreleased セクションを使用して差分を記録してください）
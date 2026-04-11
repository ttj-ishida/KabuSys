CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用しています。

[Unreleased]
-------------

- 開発中の変更はここに記載します。

[0.1.0] - 2026-04-11
-------------------

Added
- 初期リリースを追加。以下の主要コンポーネントを実装。
  - 起動スクリプト
    - run_execution: ExecutionEngine の起動スクリプトを提供。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB（data/paper_trading.db）と MockBrokerClient を使う挙動をサポート。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）に対応。
  - 設定管理
    - kabusys.config.Settings: 環境変数と .env/.env.local の自動ロード機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサは export 形式、クォート、インラインコメント、上書き保護（protected keys）に対応。
    - 多数のプロパティを提供（DB パス、API トークン、PID / kill フラグパス、閾値、環境種別判定など）。
    - PAPER_FILL_MODE の検証（instant|partial|never|reject）。
  - ポートフォリオ構築
    - portfolio.portfolio_builder: 銘柄候補の選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: 株数計算ロジック（calc_position_sizes）。risk_based / equal / score の配分方式、単元株丸め、個別上限・集計上限（スケーリング）、コストバッファ対応。
  - リサーチ（DuckDB ベースのファクター計算）
    - research.factor_research: Momentum / Volatility / Value ファクター（calc_momentum, calc_volatility, calc_value）。
    - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク関数（rank）。
    - research パッケージは zscore_normalize を data.stats から再エクスポート。
  - AI 関連
    - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出・ai_scores へ書き込む score_news を実装。チャンク処理、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスの厳密なバリデーション、スコアのクリップ（±1.0）、DuckDB トランザクションでの冪等書き込み（部分失敗時の保護）を備える。
    - ai.regime_detector: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを重み付け合成して日次の市場レジーム（bull/neutral/bear）を判定。API キー解決、API 失敗時のフォールバック、冪等書き込みを実装。
  - ユーティリティ
    - utils.process_priority: Windows / POSIX を透過するプロセス優先度設定（set_process_priority）と CPU affinity 固定ユーティリティ（set_cpu_affinity）。権限不足や未対応 OS に対する安全なフォールバックとログ出力を行う。
  - パッケージ基礎情報
    - kabusys.__init__ にバージョン 0.1.0 を追加。

Changed
- 初期リリースにつき、既存仕様の大枠を確立。
  - run_monitoring は監視処理に本番 sqlite_path を常に使用する方針を明記（環境に依存しない監視 DB 使用）。
  - run_execution は paper_trading 環境と本番環境を DB レイヤで分離（settings.is_paper に基づく sqlite_path 選択）。

Fixed
- 設計上のフォールトトレラント化と安全弁を多数導入。
  - MONITOR_POLL_INTERVAL に不正（0 以下や非整数）が渡された場合は警告を出してデフォルト値にフォールバック。
  - .env ファイルの読み込みでファイルアクセス失敗時に警告を出して継続。
  - OpenAI API 呼び出しでの JSON パース失敗や想定外フォーマットに対して耐性を持たせ、部分的失敗が他データを破壊しないように処理。
  - DuckDB executemany の空パラメータ問題（0.10 系）を考慮して、空リストは呼ばない分岐を追加。

Security
- 環境変数未設定時の明確な例外メッセージ（_require）を追加し、API キー未設定での明示的エラーを行う（OpenAI キー等）。

Notes / Implementation details
- DuckDB を利用したオンディスク分析（prices_daily / raw_financials / raw_news 等）を前提に設計。リサーチ / AI モジュールはいずれも DuckDB 接続を受け取り外部 API への副作用を限定。
- 日付・時刻の取り扱いにおいてルックアヘッドバイアスを防ぐ方針を各モジュールで徹底（target_date 引数ベース、date.today()/datetime.today() 直接参照を回避）。
- OpenAI 呼び出しは Chat Completions（JSON mode）を想定。ユニットテスト用に _call_openai_api を差し替え可能に実装。

For developers
- settings モジュールはプロジェクトルート検出（.git または pyproject.toml）に失敗した場合は自動 .env ロードをスキップします。CI やテストで自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 新規テーブルへの書き込みは冪等性を意識して実装しています（例: ai_scores / market_regime の DELETE→INSERT パターン）。
- 単体関数群（portfolio/*, research/*）は純粋関数設計を心がけており、DB 参照を伴わない計算ロジックは副作用を持ちません。

未対応 / 既知の改善点
- position_sizing の lot_size は現状全銘柄共通。将来的に銘柄別 lot_map をサポートする予定（TODO がコード内に記載）。
- apply_sector_cap: price_map に価格欠損（0.0）があるとエクスポージャーを過少見積りする可能性があり、フォールバック価格（前日終値等）の使用が検討課題。
- ai モジュールのモデル/プロンプトは今後のバージョニングで改定される可能性あり。

--- 

（この CHANGELOG はソースコードの実装内容から推測して作成されています。実際のリリースノートとして利用する場合は差分の確認・日付の調整を行ってください。）
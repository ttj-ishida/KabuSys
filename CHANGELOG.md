# CHANGELOG

すべての重要な変更はこのファイルに記録されます。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

## [未リリース]
- （なし）

## [0.1.0] - 2026-04-11
最初の公開リリース。自動売買フレームワークのコア機能を実装しました。主な追加点は以下の通りです。

### 追加（Added）
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、Paper Trading 用に分離された SQLite DB（data/paper_trading.db, 環境変数で上書き可）を使用する。
    - 起動時にプロセス優先度を高（high）へ設定する仕組みを組み込み。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立ててセッションを実行。
    - DuckDB を分析用に接続。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出力。
    - 監視処理は環境（development/paper_trading/live）にかかわらず本番 sqlite_path を使用するようになっている（運用の意図に注意）。

- 設定管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env のパーサを実装（export プレフィックス、クォート文字列、インラインコメント、保護された OS 環境変数の扱いに対応）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - Settings クラスを導入し、環境変数から各種設定値をプロパティとして提供（DB パス、PID ファイルパス、監視閾値、ログレベル、環境判定など）。
    - 一部設定で値検証を実施（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の有効値チェックなど）。

- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder
    - 候補選定（select_candidates）と配分重み計算（calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバックして警告を出力。
  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）を実装。既存保有の時価を集計して上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear をマップ、未知レジームは 1.0 にフォールバックして警告）。
  - portfolio.position_sizing
    - 株数算出ロジック（calc_position_sizes）を実装。allocation_method に応じて risk_based / equal / score の方式をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、全体の aggregate cap、コストバッファ(cost_buffer) を踏まえたスケーリング、端数の優先割当（残差配分）などを扱う。

- 研究・特徴量
  - research.factor_research
    - Momentum / Volatility / Value ファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。DuckDB の prices_daily / raw_financials テーブルを用いた SQL ベースの計算。
    - 計算ウィンドウや必要サンプル数チェックを行い、不足時には None を返す設計。
  - research.feature_exploration
    - 将来リターン計算(calc_forward_returns)、IC（Information Coefficient）計算(calc_ic)、基本統計量計算(factor_summary)、ランク付け(rank) を実装。外部ライブラリに依存せず標準ライブラリのみで実装。

- AI 関連
  - ai.news_nlp
    - raw_news と news_symbols を元に OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを評価し、ai_scores テーブルへ書き込む score_news を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と記事集約、1銘柄あたりの記事上限・文字数上限でトリム処理。
    - チャンク（最大 20 銘柄）単位で API を呼び、429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフで再試行。API 呼び出し失敗時は部分的にスキップして継続（フェイルセーフ）。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score の型チェック、既知コードのみ採用、スコアを ±1.0 にクリップ）。
    - DuckDB への書き込みは部分失敗を考慮し、対象コードのみ DELETE → INSERT を行う（トランザクション制御、エラーハンドリング）。
  - ai.regime_detector
    - ETF 1321（日経連動 ETF）の 200 日 MA 乖離とマクロ経済ニュースの LLM センチメントを合成して日次の市場レジーム判定（'bull'/'neutral'/'bear'）を行うモジュールを追加。
    - MA 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。データ不足時は中立 (=1.0) でフォールバック。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し、スコア合成ロジック、market_regime テーブルへの冪等書き込みを実装。API エラー時は macro_sentiment=0.0 にフォールバックして継続。

- ユーティリティ
  - utils.process_priority
    - プラットフォームを意識せずプロセス優先度を設定する set_process_priority(level) を実装（Windows / POSIX の差分吸収）。
    - CPU アフィニティを設定する set_cpu_affinity(cpu_count) を追加。
    - 許可されない操作・権限不足が起きた場合は警告を出して安全にスキップする設計。

- パッケージ基礎
  - kabusys.__init__ にバージョン情報 __version__ = "0.1.0" を追加し、主要なサブパッケージを __all__ で公開。

### 変更（Changed）
- DuckDB と SQLite を用途別に分離して利用
  - DuckDB: 分析・ファクター計算・研究・AI 前処理用
  - SQLite: 監視・実行の永続ストレージ（paper_trading 環境は別 SQLite を利用）
- .env ロード順序: OS 環境変数 > .env.local > .env（OS 環境変数は保護され上書きされない）

### 修正（Fixed）
- .env のパースにおけるクォートやエスケープ、インラインコメント処理を堅牢化（意図しないトークン分割を防止）。
- OpenAI API 呼び出しに関するエラー処理を強化（特定エラーでのリトライ、その他は安全にスキップ）。

### 注意点（Notes）
- OpenAI API キーは score_news / regime_detector の呼び出しで引数に渡すか、環境変数 OPENAI_API_KEY を設定する必要があります。未設定時は ValueError を送出します。
- run_monitoring の監視 DB は環境値にかかわらず settings.sqlite_path を使用します。Paper Trading と本番 DB を完全に分離したい場合は設定の確認・調整を推奨します。
- calc_position_sizes 等は単元株や価格欠損時の挙動について TODO コメントが残っています（将来的な拡張点: 銘柄別 lot_size のサポート、価格フォールバックなど）。

---

メンテナンスや既知の改善点は今後のリリースで追記します。
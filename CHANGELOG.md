# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。セマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-04-12

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能を提供する多数のモジュールを追加。
- パッケージメタ情報
  - パッケージバージョンを `0.1.0` として定義（src/kabusys/__init__.py）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local の自動ロード（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - .env パーサを実装（コメント、export 形式、クォート・エスケープ処理、protected key の考慮）。
  - 必須環境変数検査ヘルパー `_require`。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム環境判定など）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の許容値チェック）。

- 実行エントリ・監視スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離して利用（data/paper_trading.db をデフォルト）。
    - BrokerClientFactory によるブローカークライアント生成を利用（paper_trading では Mock を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構築しセッション実行。
    - 起動時にプロセス優先度を High に試行的に設定。
    - duckdb 接続の利用。
    - 監視テーブルの初期化（init_monitoring_db）による冪等性保証。
    - RiskManager の初期構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装。

  - 監視ポーリング起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor を初期化してポーリングループを実行。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用（monitoring データは分離しない設計）。
    - 起動時にプロセス優先度を High に設定を試行。

- プロセス制御ユーティリティ（src/kabusys/utils/process_priority.py）
  - クロスプラットフォームでプロセス優先度（high/normal/low）の設定を試みる `set_process_priority` を提供（Windows / POSIX 対応）。
  - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供。
  - psutil の権限不足や未対応機能に対しては警告を出して安全にスキップ。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 候補選定と重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - BUY シグナルのスコア降順ソート、上位 N 選択。
    - 等金額配分およびスコア加重配分（スコア全て 0 の場合は等金額にフォールバック）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - 既存保有を考慮したセクター集中制限（max_sector_pct）を適用する関数 `apply_sector_cap`。
    - 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数 `calc_regime_multiplier`。未知レジームは 1.0 でフォールバック。
  - 株数決定・資金配分（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じたポジションサイズ決定（"risk_based"/"equal"/"score"）。
    - 単元株（lot_size）丸め、1銘柄上限・集約上限（available_cash）によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮。
    - risk_based では stop_loss_pct と risk_pct から許容株数を算出。
    - aggregate cap 超過時のスケーリングと余剰キャッシュによる再配分ロジックを実装。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - モメンタム / ボラティリティ / バリューのファクター計算（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 接続を受け取り SQL ウィンドウ関数で効率的に計算。
    - データ不足時の None 処理（例: MA200 のサンプル数が不足する場合など）。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン対応、入力バリデーションあり）。
    - Spearman ランク相関（Information Coefficient）計算（`calc_ic`）。
    - ランク変換ユーティリティ（`rank`）およびファクター基本統計量サマリー（`factor_summary`）。
    - pandas 等に依存せず標準ライブラリのみで実装。

- AI ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約して OpenAI API（gpt-4o-mini）へ送信し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores に書き込む処理を実装。
  - バッチ処理（最大 20 銘柄／回）、トークン肥大化対策（1銘柄あたり最大記事数／最大文字数）、JSON Mode として厳密なレスポンス検証。
  - 429/ネットワーク/5xx に対する指数バックオフリトライ（上限あり）。API キーは引数または環境変数 OPENAI_API_KEY で指定。
  - ニュース収集ウィンドウの計算ユーティリティ（JST ベース → UTC 変換）を実装。
  - 部分失敗に備えて、影響を受ける銘柄コードのみ置換することで既存スコアを保護する運用方針。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用検証レポート生成スクリプトを追加。
  - 検証指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
  - パス/フェイル判定閾値を定義（稼働率 >=99%、成功率 >=90% など）。
  - CLI オプションで期間指定（--from, --to）および DB パス指定（--db）。PAPER_TRADING_SQLITE_PATH 環境変数も使用可能。
  - 出力は標準出力へ整形レポート。

- モジュールエクスポート整理
  - portfolio / research パッケージの __init__ にて主要 API を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- OpenAI API キーやその他秘密は環境変数から取得する設計。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能（テスト等でのキー露出を制御するためのフラグ）。

---

注:
- 本リリースの実装は DuckDB / SQLite / psutil / openai クライアント等の外部依存に依存します。データベース接続先や API キーは環境変数で設定してください。
- paper_trading 環境は本番 DB と分離される設計になっていますが、運用時は環境変数の設定と DB パスの確認を必ず行ってください。
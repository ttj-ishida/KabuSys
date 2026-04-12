# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージ内の __version__（0.1.0）に基づきます。

## [0.1.0] - 2026-04-12

### 追加 (Added)
- 基本構成
  - パッケージ初期リリース。モジュール群を追加し、日本株自動売買システムのコア機能を提供。
  - バージョン: `kabusys.__version__ = "0.1.0"`。

- 環境設定 (kabusys.config)
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env / .env.local の読み込み順序をサポート。既存の OS 環境変数を保護する仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 複雑な .env パース機能を実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い）。
  - Settings クラスを追加し、アプリ設定値をプロパティ経由で取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須環境変数取得（未設定時は例外）。
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等のパス設定。
    - PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject"）の検証。
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL の検証。
    - CPU/MEM/DISK しきい値等の監視パラメータ。

- 実行エントリ / プロセス管理
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定（set_process_priority）。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート（paper/live の切替を想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立て、セッションを実行。
    - RiskManager のデフォルト設定（max_position_pct 等）をコード内で定義。

  - run_monitoring.py
    - SystemMonitor をポーリングで実行する起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値や 0 以下はデフォルトにフォールバックし警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する旨の設計。
    - duckdb 接続と sqlite 接続を初期化し、監視ループ実行中は例外処理でログに残しつつ継続するフェイルセーフを実装。

  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定ユーティリティを追加（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - CPU affinity 設定 helper（最初の N コアにプロセスを固定）。
    - 権限不足や未サポート環境での安全なフォールバック／警告出力を実装。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバックし警告を出す。

  - risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）：既存ポジションのセクター別時価から上限超過セクターを検出し、新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームは 1.0 でフォールバック）。

  - position_sizing.py
    - 株数決定ロジック（calc_position_sizes）を実装。
    - allocation_method による分岐（"risk_based", "equal", "score"）をサポート。
    - lot_size（単元）丸め、per-stock 上限、aggregate cap（available_cash を超えた場合のスケーリング）を実装。
    - cost_buffer（手数料・スリッページ見積り）を用いた保守的なコスト見積りと端数配分ロジックを備える。

  - パッケージエクスポート: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier。

- リサーチ・ファクター計算 (kabusys.research)
  - factor_research.py
    - モメンタム、ボラティリティ、バリューの各ファクター計算を実装（DuckDB を用いた SQL ベース）。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播に注意した実装。
    - calc_value: raw_financials から最新財務情報を結合し PER/ROE を計算。

  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、統計サマリー（factor_summary）、ランク付け（rank）を実装。
    - calc_forward_returns: 可変ホライズン対応と入力バリデーション（horizons が 1〜252 の整数であること）。
    - calc_ic: None フィールドやデータ不足（有効レコード < 3）をハンドリング。

  - research パッケージ __init__.py で zscore_normalize（kabusys.data.stats から）を再エクスポート。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメントスコアリング機能を追加（score_news）。
  - 処理フロー:
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - raw_news と news_symbols を銘柄ごとに集約（記事数/文字数の上限でトリム: _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄ずつのバッチ送信、JSON モードでの厳密なレスポンス期待。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンスバリデーションとスコアの ±1.0 クリッピング。
    - 成功チャンク分のスコアを部分的に ai_scores テーブルへ安全に置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT の戦略：部分失敗時に他銘柄の既存スコアを保護）。
  - OPENAI_API_KEY の解決ロジック（引数 > 環境変数）。未設定時は ValueError。

- ツール (kabusys.tools.paper_verification_report)
  - Paper Trading 用検証レポート生成スクリプトを追加（コマンドライン実行可能: python -m kabusys.tools.paper_verification_report）。
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
  - レポート指標:
    - 稼働率（uptime_pct）、注文成功率（fill_rate_pct）、送信率（send_rate_pct）、P95 レイテンシ（p95_ms）、リスク却下数等を算出。
  - Pass/Fail 基準値を定義（THRESHOLD_* 定数、例: 稼働率 >= 99%）。
  - 日付フィルタ (--from, --to) による期間指定及び CLI オプション --db をサポート。
  - P95 計算、欠損時の N/A 表示、SQLite のテーブル未存在時の安全な扱い（OperationalError をハンドリング）をサポート。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 既知の注意点 / 今後の改善候補
- position_sizing.calc_position_sizes:
  - open_prices に欠損（0.0）があるとエクスポージャーや発注量が過小見積りになる可能性がある旨の TODO コメント（前日終値や取得原価でのフォールバック検討）。
- news_nlp:
  - 大規模な記事 / トークン肥大化対策は実装済みだが、API コスト制御や並列実行の最適化は今後の改善候補。
- research モジュールは DuckDB の prices_daily / raw_financials に依存。実データ投入やパフォーマンス検証が必要。
- settings._require による必須値不足は起動時に例外を投げるため、デプロイ時の環境変数整備が必要。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートが別途存在する場合はそれに合わせて更新してください。
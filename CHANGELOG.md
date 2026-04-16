CHANGELOG
=========

すべての重要な変更点はここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

なお、本CHANGELOGはリポジトリ内のコード内容から推測して作成したものであり、実際のコミット履歴とは異なる場合があります。

[0.1.0] - 2026-04-16
-------------------

Added
- パッケージ初期実装（バージョン 0.1.0）。
- 起動スクリプト:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はフォールバックして警告ログ出力。
    - 停止フラグファイル (data/stop_requested.flag) 検知でループを終了。
    - プロセス優先度を "high" に設定（set_process_priority 呼び出し）。
    - monitoring 用 DB 初期化（init_monitoring_db）、DuckDB 接続。
    - check_once() の例外はキャッチしてログ出力し次ポーリングへ継続。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用（settings.paper_sqlite_path）。paper_trading 時は本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
    - 実行はバックグラウンドスレッドで行い、停止フラグで安全に停止処理を行う。
    - 実行 PID ファイル (data/execution.pid) の取り扱い（Engine に渡す）。
- 設定管理:
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出 .git または pyproject.toml を基準）。
    - .env パーサを実装（export プレフィックス、クォート・エスケープ、インラインコメントの取り扱いなどに対応）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - Settings クラスを導入し、各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 環境クラス等）。
    - PAPER_FILL_MODE の検証（valid: "instant", "partial", "never", "reject"）とエラーメッセージ。
    - デフォルトパス: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, PAPER_TRADING_SQLITE_PATH=data/paper_trading.db。
    - 環境名検証（development, paper_trading, live）とログレベル検証。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等比率 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
    - スコアが全銘柄で 0 の場合は等分配にフォールバックして WARNING ログ。
  - portfolio/risk_adjustment.py
    - セクター集中上限適用 (apply_sector_cap)。既存保有を考慮して過集中セクターの候補を除外。unknown セクターは除外対象外。
    - レジーム乗数 (calc_regime_multiplier) 実装（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - 発注株数計算 (calc_position_sizes) 実装。
    - allocation_method に "risk_based", "equal", "score" をサポート。
    - lot_size（単元株）丸め、銘柄ごとの上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer を考慮した保守的見積り、残差に基づく追加配分ロジックを実装。
- リサーチ:
  - research/factor_research.py
    - Momentum / Volatility / Value ファクター計算関数を実装（DuckDB 接続を使用して prices_daily, raw_financials テーブルを参照）。
    - calc_momentum, calc_volatility, calc_value を提供。
  - research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC（Spearman）計算 (calc_ic)、rank、統計サマリ (factor_summary) を実装。
    - 外部ライブラリに依存しない純粋 Python 実装。
- ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - CLI オプション: --from, --to, --db。PAPER_TRADING_SQLITE_PATH 環境変数対応。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシを出力。
    - デフォルト合格基準（閾値）を定義（稼働率 99%、成功率 90%、送信率 95%、P95 200 ms）。
    - SQL の OperationalError を考慮したフォールバック処理。
- AI / NLP:
  - ai/news_nlp.py
    - raw_news から銘柄別に記事を集約し、OpenAI API (gpt-4o-mini) を用いてセンチメントスコアを算出して ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、トークン肥大化対策（記事数／文字数トリム）、429/ネットワーク/5xx のエクスポネンシャルバックオフリトライ、レスポンス検証、スコアクリッピング（±1.0）、部分成功時の置換ロジック（対象コードに限定した DELETE→INSERT）を設計。
    - 注意: OpenAI API キーが未設定の場合は ValueError。
    - ニュース時間ウィンドウ計算ユーティリティ (calc_news_window) を提供。
    - （注）ファイル末尾が切れているため動作は部分実装の可能性あり（コードベースの状態に依存）。
- ユーティリティ:
  - utils/process_priority.py
    - set_process_priority(level) を実装（Windows と POSIX の差分吸収、psutil 使用）。
    - set_cpu_affinity(cpu_count) を実装（指定コア数に固定）。
    - アクセス権限不足や未対応プラットフォーム時には警告を出してスキップするフォールバック。

Changed
- パッケージ初版として多数の機能を実装。実行時のデフォルト動作やファイルパス/環境変数のデフォルト値が明確化された。
- 監視処理は KABUSYS_ENV にかかわらず monitoring 用 sqlite_path（data/monitoring.db）を使用するように明示。

Fixed
- （このリリースは新規実装が主体のため、既知のバグ修正の記述なし）

Security
- ai/news_nlp.py は OpenAI API キー（OPENAI_API_KEY または api_key 引数）を必要とする。API キーの管理や権限に注意すること。
- .env 自動読み込みがデフォルトで有効（プロジェクトルート検出に成功した場合）。テスト環境等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すること。

Notes / Breaking changes
- Settings.paper_fill_mode は許容値を検証するため、既存 .env で不正な値が設定されている場合は起動時に ValueError が発生する。
- MONITOR_POLL_INTERVAL は環境変数で上書き可能だが、1 未満の値や整数以外は無効と判断され、デフォルト 60 秒にフォールバックする（警告ログ）。
- position_sizing の lot_size は現状全銘柄共通での想定。将来的に銘柄別単元対応に拡張予定（コードに TODO コメントあり）。

開発者向けメモ
- DuckDB 接続を受ける関数群（research/*, ai/news_nlp など）はテーブルスキーマとデータ品質に依存するため、テスト用 DB を用意してユニットテストを実行してください。
- ai/news_nlp の挙動（バッチ処理、API レスポンス検証、部分置換ロジックなど）は外部 API の仕様変更に敏感なので、API バージョン変更時は要確認です。
- run_execution/run_monitoring はプロセス優先度の設定を試みます。権限のない環境では警告を出して進行する設計ですが、要件に応じて変更してください。

---- 
（このCHANGELOGはソースコードの内容から推測して作成した要約です。実際の運用・リリースノートとして利用する場合は、コミット履歴・テスト結果・デプロイ手順などを合わせて更新してください。）
KEEP A CHANGELOG — 形式に準拠した CHANGELOG.md（日本語）

注: 内容は提示されたコードベースから推測して作成しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-12
-------------------
Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムのコア機能を追加。
- 設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 行パーサは export 形式、クォート、エスケープ、行内コメントなどに対応。
  - 必須環境変数取得時の _require() により未設定は ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
  - 各種設定プロパティを提供:
    - DB パス: DUCKDB_PATH, SQLITE_PATH（paper_trading 時は PAPER_TRADING_SQLITE_PATH を使用）
    - Paper Trading 関連: PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject" の検証）
    - 監視・プロセス管理: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - システム閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - 環境種別バリデーション: KABUSYS_ENV（development / paper_trading / live）
    - ログレベルバリデーション: LOG_LEVEL

- 実行/監視スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper 専用 SQLite（data/paper_trading.db をデフォルト）を使い、MockBroker を想定して本番 DB と完全分離。
    - BrokerClientFactory を経由したブローカークライアントの生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を実行。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を含む。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視専用テーブルを本番 DB に記録する設計）。
    - 起動時にプロセス優先度を "high" に設定する試みを行う。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しを実装（監視テーブルの存在を保証／冪等）。

- ユーティリティ（kabusys.utils）
  - process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定ユーティリティを追加（Windows: HIGH_PRIORITY_CLASS、POSIX: nice 値）。
    - CPU affinity 設定関数 set_cpu_affinity を追加（最初の N コアに固定）。
    - 権限不足や未対応環境の際は警告を出して安全にフォールバック。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder.py
    - シグナルの選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を追加。全スコアが 0 の場合は等配分にフォールバックして警告を出す。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮して新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - position_sizing.py
    - calc_position_sizes: 重み・候補・現金・既存保有・価格情報から発注株数を算出する主要ロジックを実装。
    - risk_based / equal / score の allocation_method に対応。
    - 単元株（lot_size）丸め、per-position および aggregate 上限、cost_buffer（手数料・スリッページ想定）を考慮したスケーリングと端数処理。
    - portfolio_value が小さい、価格が不正などのケースで安全にスキップする処理を含む。

- リサーチ（kabusys.research）
  - factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER, ROE）などのファクター計算を追加。DuckDB の prices_daily/raw_financials を参照して純粋関数で計算。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクターの統計サマリ（factor_summary）、ランク関数（rank）を追加。
    - 外部依存（pandas 等）なしで実装。horizons の検証やランクの tie 処理に配慮。

- AI ニューススコアリング（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメントスコアリング機能を追加。
  - news ウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST に相当する UTC 範囲）と記事集約ロジックを実装。
  - バッチ（最大 20 銘柄）での API 呼び出し、429/ネットワーク/5xx に対する指数バックオフリトライ、結果検証、スコアクリップ（±1.0）を実装。
  - OpenAI API キー未設定時は ValueError を送出。API 呼び出し失敗時はフェイルセーフでスキップ。
  - DuckDB の ai_scores テーブルへの差分置換（部分更新）を行う設計。

- ツール（kabusys.tools）
  - paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加（コマンドライン実行: python -m kabusys.tools.paper_verification_report）。
    - 対象 DB は PAPER_TRADING_SQLITE_PATH / --db で指定可能（デフォルト data/paper_trading.db）。
    - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）などを集計してレポート出力。
    - Pass/Fail の閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 <= 200ms）し、判定理由を出力。

- パッケージメタ
  - __version__ = "0.1.0"

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 注意事項
- 環境変数・必須トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）は未設定だと起動時に例外を投げる設計です。運用時は .env を用意してください（.env.example を参照）。
- run_monitoring は監視データの記録先として常に settings.sqlite_path（本番 DB）を使用します。監視データを別 DB に分離したい場合は設定を変更してください。
- OpenAI API を利用する機能は外部依存（openai パッケージ）と API キーを必要とします。ローカルでテストする際は api_key 引数または環境変数 OPENAI_API_KEY を設定してください。
- process_priority / cpu_affinity は OS と実行権限に依存します。権限が不足する環境では警告を出して設定をスキップします。

今後の検討事項（TODO）
- position_sizing の価格欠損時に前日終値等へのフォールバックを導入してエクスポージャーの過少見積りを防止。
- 銘柄ごとの lot_size を stocks マスタから取得する設計への拡張。
- AI スコアリングの並列化やより堅牢な部分更新戦略（トランザクション）検討。
- DuckDB / SQLite のスキーマ変更時のマイグレーション処理整備。

以上。
# Changelog

すべての重要な変更は Keep a Changelog の形式で記載しています。  
この CHANGELOG は、提示されたコードベースの内容から推測して作成しています（実装・設計意図に基づく要約）。

全般的な注意
- プロジェクトメタ情報: パッケージバージョンは src/kabusys/__init__.py により v0.1.0 として定義されています。
- 環境変数やファイルパスのデフォルトは data/ 以下を想定しています（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb 等）。

Unreleased
- （このファイル作成時点での未リリースの注記があればここに追加）

[0.1.0] - 2026-04-17
Added
- 基本アプリケーション／モジュールを初版として追加。
  - 実行系
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。  
      - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。  
      - BrokerClientFactory によるブローカークライアント生成をサポート（MockBrokerClient を含む想定）。  
      - ExecutionEngine を別スレッドで実行し、 data/stop_requested.flag による外部停止を監視。エンジン停止と PID ファイル管理を実装。
      - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み。初期ポートフォリオ値は broker.get_available_cash() から取得。
  - 監視系
    - run_monitoring.py: SystemMonitor をポーリングする起動スクリプトを追加。  
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。  
      - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを操作（init_monitoring_db を呼ぶ）。  
      - data/stop_requested.flag による安全なループ停止。起動時にプロセス優先度を "high" に設定。
  - 設定管理
    - config.py: 環境変数／.env ロード機構を実装。  
      - プロジェクトルートを .git または pyproject.toml で自動検出し、.env と .env.local を読み込む（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。  
      - .env パーサはコメント、quoted value、export 形式等の扱いを強化。必須変数取得用の _require()、各種設定プロパティ（DB パス、API トークン、閾値、環境判定など）を提供。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。  
      - システム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等を算出して PASS/FAIL 判定。閾値はファイル冒頭で定義（稼働率 99%、fill rate 90%、send rate 95%、P95 200ms）。  
      - 日付フィルタ (--from / --to)、--db オプション対応。DB が存在しない場合のエラーメッセージを出力。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全て 0 の際は等分配にフォールバックし警告。
    - portfolio/risk_adjustment.py: セクター上限除外（apply_sector_cap）、市場レジームに基づく乗数（calc_regime_multiplier）を実装。未知レジームはログ警告のうえ 1.0 でフォールバック。
    - portfolio/position_sizing.py: 発注株数決定ロジックを実装（risk_based / equal / score）。  
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap のスケーリング、cost_buffer による保守的コスト見積り、残差分を lot_size 単位で再配分するアルゴリズムを導入。
  - リサーチ / ファクター計算
    - research/factor_research.py: Momentum / Volatility / Value ファクター計算を追加。DuckDB の prices_daily / raw_financials テーブルを用いた SQL ベースの実装。  
      - モメンタム: 1M/3M/6M リターン、MA200乖離（データ不足時は None）。  
      - ボラティリティ: ATR20、相対ATR、平均売買代金、出来高比率。true_range の NULL 伝播を慎重に扱う。  
      - バリュー: EPS→PER、ROE（target_date 以前の最新財務データを参照）。
    - research/feature_exploration.py: 将来リターン（複数ホライズン対応）、Spearman ランク相関（IC）計算、ファクター統計サマリ、安定したランク付け関数を実装。外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
    - research/__init__.py に必要関数を公開。
  - AI / NLP
    - ai/news_nlp.py: raw_news を OpenAI API にかけて銘柄ごとのセンチメントスコアを生成するモジュールを追加。  
      - タイムウィンドウ計算（JST → UTC）、記事集約（銘柄ごとに最新 N 記事・文字数制限）、最大 20 銘柄のバッチ送信、リトライ（429/タイムアウト/5xx は指数バックオフ）、レスポンス検証、スコアクリップ ±1.0、部分的成功でも既存スコアを保護するための差分書き込み戦略を設計。  
      - 実装は OpenAI の例外型（APIError 等）を考慮。API キー未設定時は ValueError を投げる。  
      - 注意: 提示されたコード断片は末尾が途中で切れており（_fetch_articles 呼び出し直前で中断）、記事取得部分や DB 書き込みの具体実装は未表示（実装予定／一部未完の可能性あり）。
  - ユーティリティ
    - utils/process_priority.py: プロセス優先度（Windows / POSIX の差分吸収）と CPU affinity 設定ユーティリティを追加。  
      - set_process_priority(level) で high/normal/low を設定。サポート外 OS ではスキップして警告。権限不足時は警告を出して続行。  
      - set_cpu_affinity(cpu_count) で最初の N コアに固定（cpu_count None は何もしない）。権限/未対応環境は警告を出してスキップ。
  - パッケージ初期化
    - kabusys/__init__.py を追加（__version__ = "0.1.0", __all__ の定義）。

Changed
- N/A（初回リリース相当のため「追加」が中心）

Fixed
- 設計上の堅牢性強化（実装に含まれる改善点を列挙）
  - .env 読み込み: OS 環境変数を保護する仕組みを導入、.env ファイルの読み込み失敗時に警告を出すように改良。
  - .env パーサ: export 形式、クォートされた値内のエスケープ処理、インラインコメントの取り扱い等を改善して誤読を減らす。
  - DB クエリ: DuckDB / SQLite を問わず、クエリ内で NULL と欠損値の扱いに注意した実装（例: true_range の NULL 伝播制御、カウント条件付き集計）。
  - position_sizing のスケーリング: aggregate cap 超過時にスケールダウンして lot_size 単位で再配分することで、利用可能現金に合わせた安全な割当を実現。
  - run_monitoring/run_execution: 停止フラグ（data/stop_requested.flag）の検出と安全なシャットダウンを導入。

Deprecated
- N/A

Removed
- N/A

Security
- N/A（ただし OpenAI API キー等の機密情報は環境変数で管理する設計）

Migration notes / 運用上の留意点
- 環境変数:
  - 自動的に .env / .env.local がロードされる仕組みが有効になっているため、運用環境で明示的に環境を管理したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - PAPER_TRADING_SQLITE_PATH を設定すると paper_trading モードの DB を分離可能（run_execution）。
  - MONITOR_POLL_INTERVAL で監視のポーリング間隔を秒単位で指定可能（1 未満や不正な値は無視され、デフォルト 60 秒が使われます）。
- ファイルフラグ:
  - data/stop_requested.flag を作成することで run_monitoring / run_execution の外部停止が可能。存在確認はループ内で行われます。
- OpenAI:
  - ai/news_nlp.py を使用する場合は OPENAI_API_KEY を設定するか、score_news の api_key 引数で渡してください。API 呼び出しの失敗はリトライする設計ですが、API 利用量・料金に注意してください。
- DB スキーマ:
  - paper_verification_report や research モジュールは特定のテーブル（system_status, trade_logs, risk_logs, prices_daily, raw_financials, raw_news 等）を想定しています。実行前に対応するスキーマ／初期データを準備してください。

既知の制限 / TODO（コードから推測）
- ai/news_nlp.py の記事取得および DB 書き込みロジックが提示ファイル内で途中で途切れており、完全実装は別箇所に存在するか未完の可能性があります。運用前に _fetch_articles 等の実装確認が必要です。
- position_sizing の price フォールバック（価格欠損時に前日終値や取得原価等を使う）は TODO コメントあり。価格欠損があるとエクスポージャーが過小評価される恐れあり。
- セクター不明 ("unknown") の取り扱いは現状で上限適用除外になっているため、マスタ整備が推奨されます。
- research モジュールは DuckDB に依存するクエリを多用するため、パフォーマンス・メモリに留意した運用が必要。

---

この CHANGELOG はコードベースの内容から推測して作成したため、実際のコミット履歴や意図とは差異がある可能性があります。差異があれば、実際の git コミットやリリースノートを元に修正してください。
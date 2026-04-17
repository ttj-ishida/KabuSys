CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在未リリースの変更はここに記載します。）

v0.1.0 - 2026-04-17
-------------------

Added
- 初回公開: KabuSys コードベースの主要コンポーネントを追加。
  - パッケージ全体
    - パッケージメタ情報: __version__ = "0.1.0" を設定。
    - 公開 API: portfolio, research, tools, execution, monitoring など主要モジュールをエクスポート。
  - 設定管理 (kabusys.config)
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - .env / .env.local の読み込みロジック（クォート対応、エスケープ、コメント処理、override/protected オプション）。
    - Settings クラスでアプリケーション全体の環境変数取得を集中管理（DB パス、API トークン、監視閾値、動作環境判定等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - 実行/運用スクリプト
    - run_execution: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成。OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
      - ExecutionEngine をスレッドで実行、data/stop_requested.flag による外部停止制御、execution.pid 管理。
      - RiskManager にデフォルトのリスク設定を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒、0 以下は警告のうえデフォルトにフォールバック）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。
      - stop flag（data/stop_requested.flag）検出でループ終了。
      - プロセス優先度を High に設定して起動。
  - 監視 DB 初期化
    - init_monitoring_db を利用して監視用テーブルを冪等に初期化（run_execution/run_monitoring が利用）。
  - プロセス制御ユーティリティ (kabusys.utils.process_priority)
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。
    - Windows / POSIX の差を吸収（psutil に依存）。権限不足等は警告でフォールバック。
  - Portfolio 構築モジュール (kabusys.portfolio)
    - portfolio_builder
      - select_candidates: スコア降順、signal_rank によるタイブレーク。
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア全体が 0 の場合は等配分へフォールバックし警告）。
    - risk_adjustment
      - apply_sector_cap: セクター集中制限。既存保有のセクター別時価を計算し max_sector_pct 超過セクターの候補除外。unknown セクターは制限適用除外。
      - calc_regime_multiplier: 市場レジーム(bull/neutral/bear) に応じた資金乗数（未知レジームは 1.0 でフォールバック）。
    - position_sizing
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算。
      - 単元株丸め、per-position 上限および aggregate cap（available_cash に基づくスケールダウン）、cost_buffer を用いた保守見積り。
      - lot_size 将来的拡張の注記と価格欠損時の挙動（ログ出力）。
  - リサーチ機能 (kabusys.research)
    - factor_research: モメンタム / ボラティリティ / バリュー ファクター計算を追加。
      - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を参照して各種ファクターを返す（date, code ベース）。
      - 欠損データや必要行数不足時は None を返す設計。
    - feature_exploration: 将来リターン・IC・統計サマリーを追加。
      - calc_forward_returns: 指定 horizon で将来リターンを計算（入力バリデーションあり）。
      - calc_ic: スピアマンのランク相関（ランク付けは平均ランク、ties を考慮）。
      - factor_summary / rank: 基本統計量の算出とランク変換ユーティリティ（外部依存無しで実装）。
    - research パッケージは zscore_normalize を data.stats からインポートして公開。
  - AI ニュース NLP (kabusys.ai.news_nlp)
    - raw_news から銘柄別に記事を集約し OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメントスコア（-1.0〜1.0）を計算・ai_scores に書き込み。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装。
    - 429, ネットワーク断, タイムアウト, 5xx は指数バックオフでリトライ（上限あり）。API キー解決と未設定時の ValueError を実装。
    - 出力のフォーマット厳密検証、スコアクリップ（±1.0）、部分失敗時のデータ保護（対象コードを限定して DELETE/INSERT）方針。
  - ツール
    - kabusys.tools.paper_verification_report
      - Paper Trading 検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
      - --from / --to / --db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数で DB 指定可能。
      - 指標: 稼働率 (uptime_pct)、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）。
      - パス/フェイル基準値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
      - DB テーブル欠如時の耐障害処理（OperationalError を捕捉して N/A を出力）。
  - その他
    - 各モジュールで入力チェック・None 耐性・ログ出力（debug/info/warning/exception）を適切に実装。
    - DuckDB と sqlite3 を用途に応じて使い分け（時系列ファクター計算は DuckDB、監視/発注ログは SQLite を想定）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定。未設定時は例外で明示。

Notes / 注意事項
- run_monitoring は説明コメント通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」するため、テスト環境で監視を分離したい場合は sqlite_path を変更する必要があります。
- run_execution は paper_trading 環境で paper_sqlite_path を使用することで本番 DB とデータを分離します。
- process_priority/set_cpu_affinity は権限やプラットフォームに依存するため失敗した場合は警告ログを出して処理を継続します。
- position_sizing 等のアルゴリズムは将来の拡張（銘柄別 lot_size マスタや価格フォールバック等）を想定したコメント・TODO を含みます。
- DuckDB 側のクエリはウィンドウ関数や LEAD/LAG を多用しており、prices_daily/raw_financials スキーマが想定どおりであることが前提です。

将来の予定（例）
- position_sizing の銘柄別 lot_size 対応。
- price フォールバック（前日終値や取得原価）を使ったエクスポージャー計算の改良。
- news_nlp の API モデル切替や並列化の最適化。
- モニタリング・実行のプロセス監視強化（より安全な PID 管理、ログローテーション等）。

-----
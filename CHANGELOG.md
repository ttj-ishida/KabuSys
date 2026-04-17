CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。  

※この CHANGELOG はリポジトリ内のコード内容から推測して作成しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-17
------------------

初回公開リリース。以下の主要機能・モジュールを実装しています。

Added
- 基本パッケージ情報
  - kabusys パッケージ（__version__ = "0.1.0"）。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 停止フラグ（data/stop_requested.flag）検知でループを停止。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
  - run_execution.py
    - ExecutionEngine（注文実行エンジン）起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ検出でエンジンを安全に停止。PID ファイル / stop フラグの利用。

- 設定・環境読み込み
  - config.Settings クラス
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - export KEY=val 形式・クォート付き値・インラインコメント対応を含む堅牢な .env パーサ実装。
    - 各種プロパティを提供（J-Quants / kabu API / LINE / DB パス / Paper Trading 設定 / 監視閾値 / ログレベル / 環境判定など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject に制約）。
    - PAPER_TRADING_SQLITE_PATH による paper_trading 用 DB の上書き。
    - 各種閾値プロパティ（CPU/MEMORY/DISK）やフラグパスを提供。

- モニタリング・データ基盤
  - monitoring.monitoring_db.init_monitoring_db 呼び出しを各スクリプトで担保（監視テーブルの存在保証、冪等）。

- Execution サブシステム（起動時組み立て）
  - BrokerClientFactory によるブローカークライアント生成。
  - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine の組み立てと起動ロジック。
  - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）と初期ポートフォリオ値に broker.get_available_cash() を使用。
  - エンジンは別スレッドで実行、停止フラグ検知により stop() を呼び出し安全終了。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順、同点は signal_rank によるタイブレーク。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合は等金額配分へフォールバックして警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター別エクスポージャーに基づき新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method (risk_based / equal / score) に対応した株数決定。
    - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り）考慮。
    - aggregate cap を超えた場合のスケールダウン実装と残差を考慮した追加配分ロジック。

- 研究（Research）モジュール
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離（DuckDB を使った SQL 実装）。
    - calc_volatility: ATR(20), 相対 ATR, 20日平均売買代金, 出来高比率。
    - calc_value: PER（EPS の有無を考慮）と ROE（raw_financials から最新を取得）。
    - DuckDB を前提にパフォーマンスを意識したクエリ設計。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出（horizons 検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。利用可能レコードが不足する場合は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）集計。
    - 外部ライブラリ不使用（標準ライブラリのみ）。

- AI ニュース NLP スコアリング
  - ai.news_nlp
    - raw_news を OpenAI（gpt-4o-mini）に送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルに書き込む処理。
    - バッチ処理（最大 20 銘柄 / コール）、記事数と文字数のトリム（最大記事数/最大文字数を指定）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時に既存スコアを保護するためコード絞り込みで DELETE→INSERT を実施。
    - target_date を基準にニュース収集ウィンドウを計算し、ルックアヘッドバイアスを排除（内部で datetime.today() を参照しない設計）。
    - OPENAI_API_KEY を引数または環境変数から解決、未設定時は例外を送出。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX (Linux, Darwin, FreeBSD) の差分を吸収してプロセス優先度を設定。アクセス不可時は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留め。引数検証と失敗時のフォールバックあり。
  - logging を用いた適切な情報・警告・例外ログ出力。

- コマンドラインツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成スクリプト。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - CLI オプション: --from, --to, --db。
    - 基準値（PASS/FAIL 判定）を設定（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 <=200ms）。

Changed
- （本リリースは初回のため該当なし）

Fixed
- 環境変数 / .env 読み込みに関する堅牢性強化（export のサポート、クォート・エスケープの正しい扱い、インラインコメントの取り扱い、不正値はデフォルトや例外で制御）。
- MONITOR_POLL_INTERVAL の不正値（0 や非整数）での ValueError を回避し、ログ警告のうえデフォルトへフォールバック。

Security
- API キー（OpenAI など）未設定時に明示的なエラーを出す設計（鍵の存在チェックを実装）。

Deprecated
- （本リリースは初回のため該当なし）

Removed
- （本リリースは初回のため該当なし）

Notes / Known issues / TODOs
- portfolio.position_sizing.calc_position_sizes 内の価格欠損（price が 0.0）の扱いについて TODO コメントあり（フォールバック価格の検討）。
- ai.news_nlp のファイル末尾が途中で切れている箇所がある（この CHANGELOG は現行コードを元に作成）。必要に応じて API 呼び出し周りの最終処理（記事取得フェーズの完了判定など）を確認してください。
- 将来的に lot_size を銘柄別に持たせる拡張を検討する旨のコメントあり。

Contributors
- コードベースより推定（内部製作者）。リポジトリのコミット履歴がある場合はそちらを参照してください。

参考
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/
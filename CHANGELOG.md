CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

Unreleased
----------
- 進行中 / 既知の課題
  - kabusys.ai.news_nlp.score_news 内の記事集約フェーズ（_fetch_articles 呼び出し以降）が入力上で途中切れしているため、記事取得・バッチ送信の最終実装・検証が未完です。実運用前に残り実装の復元／テストを推奨します。
  - portfolio.position_sizing の price フォールバック（価格欠損時の扱い）や、将来的な銘柄別 lot_size サポートに関する TODO コメントあり。特に price==0.0 の扱いがポジション算出に影響するため注意。

0.1.0 - 2026-04-16
------------------
Added
- 基本パッケージ初期実装（バージョン 0.1.0）
  - パッケージ情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
  - 設定管理
    - src/kabusys/config.py
      - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。OS 環境変数の保護（protected）に対応。
      - export KEY=val、クォート付き値、コメント行のパース対応。バリデーション機能（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
      - Settings クラスで主要な環境設定（DB パス、PID / フラグパス、閾値など）をプロパティとして提供。
  - 実行 / 監視プロセス起動スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプト。プロセス優先度設定（high）と PID ファイル管理。
      - paper_trading 環境時は paper_trading 用の専用 SQLite DB（settings.paper_sqlite_path）を使用し、本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、エンジンスレッドによるセッション実行、停止フラグによる安全停止。
      - RiskConfig による各種リスク閾値（max_position_pct, max_utilization, rate_limit, circuit_breaker 等）を初期設定で採用。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
      - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視専用テーブル初期化を保証）。
      - 停止フラグファイル検知によるループ終了、例外を捕捉して継続する堅牢なポーリング実装。
  - モニタリング DB 初期化ユーティリティ
    - monitoring.monitoring_db.init_monitoring_db を起動時に呼び出し、監視テーブルの存在を冪等に保証。
  - プロセス制御ユーティリティ
    - src/kabusys/utils/process_priority.py
      - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（high/normal/low）を提供。権限不足や未対応 OS を考慮して安全に失敗（警告）する実装。
      - CPU affinity 設定ユーティリティ set_cpu_affinity を追加（None 設定でスキップ、1 未満は ValueError）。
  - ポートフォリオ構築（純粋関数群）
    - src/kabusys/portfolio/*
      - portfolio_builder.py
        - select_candidates: スコア降順選定（同点時は signal_rank でタイブレーク）。
        - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（スコア全0時は警告の上等分配へフォールバック）。
      - risk_adjustment.py
        - apply_sector_cap: 既存保有のセクターエクスポージャーに基づく候補除外ロジック（"unknown" セクターは制約適用外）。
        - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear、未知レジームは 1.0 でフォールバック）。
      - position_sizing.py
        - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算、単元株（lot_size）に丸め、per-stock 上限と aggregate cap のスケールダウンロジック、cost_buffer を用いた保守的見積り、残差処理による追加配分アルゴリズムを実装。
      - これらは副作用なしのメモリ内計算で、外部 DB 参照なし（純粋関数）。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - calc_momentum, calc_volatility, calc_value: DuckDB を用いた prices_daily / raw_financials に対する一括 SQL ベースのファクター計算（MA200、ATR20、PER、ROE 等）。データ不足時に None を返す安全設計。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 複数ホライズンの将来リターンをまとめて取得。
      - calc_ic / rank / factor_summary: ランク相関（Spearman）による IC 計算、ランク付けユーティリティ、基本統計量集計（count/mean/std/min/max/median）。
    - research パッケージは zscore_normalize を data.stats から再エクスポート。
  - AI ニュース NLP（スコアリング）基盤
    - src/kabusys/ai/news_nlp.py
      - raw_news の集約→OpenAI（gpt-4o-mini）へのバッチ送信→レスポンスバリデーション→ai_scores テーブル更新という設計方針を実装。
      - バッチサイズ、1銘柄当たりの最大記事数／文字数、スコアクリップ（±1.0）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）など実運用向けの保護を導入。
      - 出力は厳密な JSON ({"results": [...]}) を期待し、部分失敗時に他銘柄スコアを保護するため更新時に対象コードで絞って部分置換する方針。
  - CLI / ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 検証レポート生成ツール（CLI）。PAPER_TRADING_SQLITE_PATH を参照して system_status/trade_logs/risk_logs を集計し、稼働率・注文成功率・送信率・レイテンシ（P95含む）を算出して PASS/FAIL 判定を行う。
      - P95 パーセンタイル計算、日付フィルタ、DB 存在チェック、sqlite3.OperationalError を考慮したフェイルセーフ実装を採用。

Changed
- N/A（初期リリースのため過去からの変更は無し）

Fixed
- N/A（初期リリース）

Notes / 実装上の留意点
- 環境変数の自動ロードはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視用 DB として settings.sqlite_path（デフォルト data/monitoring.db）を使用します。監視データは環境に依存せず本番 DB パスを利用する設計です。
- run_execution は paper_trading 環境時に settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、発注履歴と監視を本番から分離します。
- process_priority / cpu_affinity は権限不足や未対応 OS でも安全にスキップされるよう警告ベースの設計です。
- research モジュールは DuckDB を前提とした SQL-heavy 実装。prices_daily / raw_financials のスキーマに依存します。
- ai.news_nlp の score_news を使用する場合は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）の提供が必須です。

Security
- 外部 API キー（OPENAI_API_KEY など）は環境変数で管理する設計。ソースツリーに秘匿情報を書き込まないでください。

今後の予定（参考）
- ai.news_nlp の未完実装部分の復元・追加テスト。
- position_sizing の価格フォールバックロジック強化（price missing 時の扱い改善）。
- 銘柄別 lot_size サポート、より細かい取引手数料／スリッページモデルの導入。
- モニタリング・検証レポートの自動化（CI / 定期ジョブ）とエクスポート機能。

--- 
（この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際の変更履歴やリリース日付はリポジトリの正式履歴に従ってください。）
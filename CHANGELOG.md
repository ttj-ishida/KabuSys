CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本書式は "Keep a Changelog" に準拠します。

フォーマット:
- Unreleased: 今後の作業項目 / TODO
- 各バージョン: リリース日とカテゴリ別の変更点（Added / Changed / Fixed / Deprecated / Removed / Security）

Unreleased
----------
予定・既知の改善点（コード中の TODO から推測）
- Portfolio
  - price が欠損（0.0）の場合のエクスポージャー算出に対するフォールバック価格（前日終値や取得原価など）を導入予定。
  - 将来的に銘柄ごとの lot_size を stocks マスタに持たせる設計に拡張予定（現状は全銘柄単一の lot_size を使用）。
- news_nlp
  - OpenAI API の失敗処理について部分的失敗時のロールバック/再試行戦略の改善検討。
- 汎用
  - DuckDB/SQLite 操作に関する追加の堅牢化（ex. executemany の空パラメータ回避は既に考慮済みだが、さらなるテストを予定）。
- ドキュメント
  - PortfolioConstruction.md / StrategyModel.md への参照実装に合わせた更なる注釈・例の追加予定。

[0.1.0] - 2026-04-13
--------------------
Added
- 全体
  - 初期リリース。日本株自動売買システム "KabuSys" の基本コンポーネントを実装。
  - パッケージバージョン: __version__ = "0.1.0"
- 実行・監視
  - run_execution.py: ExecutionEngine の起動スクリプトを実装。
    - 環境変数 KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / settings.is_paper）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine.run_session() を呼び出してセッション実行。起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - kabusys.config: .env 自動読み込み機能（プロジェクトルートの探索: .git / pyproject.toml を基準）。
    - 読み込み順: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複雑な .env 行のパース対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなど）。
    - Settings クラスで各種設定をプロパティとして提供（DB パス、API トークン、監視閾値、環境判定など）。
    - PAPER_FILL_MODE のバリデーション、有効値: "instant" | "partial" | "never" | "reject"。
- ポートフォリオ構築
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順に並べ上位 N を選択（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。スコア合計が 0 の場合は等金額にフォールバック。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）で新規候補を除外。既存保有のエクスポージャー算出と除外ロジックを実装。unknown セクターは上限対象外として扱う。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に基づく投下資金乗数を提供。未知レジームは 1.0 にフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") に対応した発注株数計算。リスクベース計算、ポジション上限、単元株丸め、aggregate cap によるスケーリング（端数配分ロジック含む）を実装。
- 研究・ファクター
  - kabusys.research.factor_research
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を参照して各種ファクター（モメンタム、ATR 等、PER/ROE）を計算。
    - 実装は SQL ウィンドウ関数を用い、データ不足時は None を返す等の堅牢化。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（複数ホライズンを一括クエリ）。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）計算、平均/分散/中央値等の統計サマリーを提供。外部ライブラリに依存せず標準ライブラリのみで実装。
- AI / ニュース
  - kabusys.ai.news_nlp
    - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコアリングし ai_scores に書き込む処理を実装（バッチ化、チャンクサイズ、トークン制御、スコアクリップ、リトライ/backoff を含む）。
    - ニュース収集ウィンドウ（JST 基準 → UTC 変換）ロジックを実装。
    - API キー処理、レスポンスのバリデーション、部分失敗時に他コードのスコアを保護する置換方式（DELETE/INSERT）を採用。
- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用 SQLite（data/paper_trading.db をデフォルト）を参照し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計してレポート出力する CLI ツールを実装。
    - P95 計算、日付フィルタ、DB 存在チェック、各種 OperationalError に対するフォールバックを実装。
- ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows/Linux/Mac 等に対応し、アクセス権限不足等の例外は警告ログでスキップ。

Changed
- 初回リリースにつき過去の変更履歴は無し。

Fixed
- 初回リリースにつき過去の修正履歴は無し。

Deprecated / Removed / Security
- なし（初回リリース時点）

Notes / Implementation Details
- DB
  - SQLite は監視用（monitoring.db）/ paper_trading 用データベースを環境に応じて分離。
  - DuckDB は時系列データ（prices_daily / raw_financials 等）の分析に使用。
- フェイルセーフ設計
  - monitoring のポーリングループや AI スコア処理では、外部エラーや例外を捕捉してログ出力し継続する設計。
  - .env の自動ロードでは OS 環境変数を保護する仕組みあり。
- ロギング
  - 各モジュールでログ出力を適切に配置し、問題発見時のデバッグ情報を出力するように設計。

開発者向け補足
- Settings のプロパティは ValueError を投げる設計が多く、起動前に必須環境変数の確認を意図している点に注意。
- DuckDB を利用する研究系関数は SQL 中でウィンドウ関数を多用しており、大量データでの実行時はリソースに注意。
- news_nlp の OpenAI 呼び出しはバッチ処理・リトライ設計が組み込まれているが、API 料金・レート制限に留意すること。

Contributing
------------
バグ修正、改善案、ドキュメント更新のプルリクエスト歓迎。コード内に散見される TODO を参考に実装を進めてください。
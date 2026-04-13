# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。重要なリリースのみをここにまとめています。日付はコードベースから推測した初期リリース日として記載しています。

全般的な方針:
- モジュールはできるだけ純粋関数／DB副作用の分離を重視しています（Portfolio モジュール等）。
- DuckDB / SQLite をデータ層に用い、実行環境（本番 / paper_trading）を環境変数で切り替え可能にしています。
- 外部 API 呼び出し（OpenAI 等）に対してはフェイルセーフかつバッチ／リトライ戦略を実装しています。

Unreleased
- （今後の変更・改善をここに記載してください）

[0.1.0] - 2026-04-13
--------------------
Added
- 初期リリースを追加。
  - パッケージバージョン: kabusys.__version__ = "0.1.0"
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度を "high" に設定し、paper_trading 環境では専用の SQLite DB（PAPER_TRADING_SQLITE_PATH, data/paper_trading.db）を使用する。BrokerClientFactory 経由で MockBrokerClient を切り替え可能。
  - run_monitoring.py: SystemMonitor をポーリングで実行するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境に依らず本番 sqlite_path を使用する設計。
- 設定・環境管理
  - config.py: .env 自動読み込み機能（プロジェクトルート判定: .git / pyproject.toml）を実装。export 付き行、クォート／エスケープ、インラインコメント等に対応する堅牢な .env パーサを実装。主要な設定プロパティ（DB パス、API トークン、監視閾値、PID/KILL フラグパスなど）を提供。
  - Settings による環境種別（development / paper_trading / live）のバリデーション。
  - PAPER_FILL_MODE の検証（instant|partial|never|reject）を実装。
- モニタリング
  - monitoring_db 初期化ユーティリティを呼び出して監視テーブルの冪等初期化を保証。
- Execution 関連コンポーネント
  - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等の組み立て・起動フローを実装（run_execution から利用）。
  - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を明示的に設定し、初期ポートフォリオ値を broker.get_available_cash() から注入。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でブレーク）と上位 N 抽出。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分（スコア全0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック（既存保有の時価を用いて上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear に対応、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。単元株（lot_size）丸め、ポジション上限、aggregate cap（現金制限）に応じたスケールダウンと端数配分ロジックを実装。
- 研究（Research）モジュール
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily/raw_financials を用いたファクター計算を実装（MA200, ATR20, 各種モメンタム等）。データ不足時は None を返す国際化されたロバスト設計。
  - research/feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターン計算。
    - calc_ic: Spearman ランク相関（IC）計算。データ不足時は None を返す。
    - factor_summary, rank: 基本統計量とランク計算ユーティリティ。
  - research.__init__ にて zscore_normalize のエクスポートを含む公開 API を整理。
- AI ニューススコアリング
  - ai/news_nlp.py: raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）にバッチ送信し、ai_scores テーブルへ書き込む処理を追加。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）と記事トリム（最大記事数・文字数）を実装。
    - チャンク単位（最大 20 銘柄）での API 呼び出し、429/5xx/ネットワークエラーに対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分更新（対象コードのみ DELETE→INSERT）により部分失敗時に既存データを保護する。
    - API キー未設定時に例外を発生させる明示的なバリデーションを追加。
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows/Linux(Mac/FreeBSD) に対応したプロセス優先度設定。未対応 OS や権限エラーは警告してスキップする堅牢化。
    - set_cpu_affinity: 指定コア数への固定（存在チェック・権限失敗は警告でスキップ）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等を算出し PASS/FAIL 判定を出力。デフォルト DB は data/paper_trading.db。閾値はソース内定数で管理。
- DB 接続
  - SQLite と DuckDB を併用（監視・注文ログは SQLite、時系列解析は DuckDB を想定）。各起動スクリプトで接続を閉じる設計。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- 外部 API キーの扱いは環境変数経由。OpenAI キー未設定時は処理を中断して明示的に通知する実装。

Notes / 実装上の注記（今後の改善候補）
- .env パーサは多くの実用ケースに対応しているが、特殊なエスケープやマルチラインの扱いは未対応。必要に応じて既製のライブラリ導入を検討。
- position_sizing の価格欠損時の取り扱い（price == 0 の場合）に対する注記と TODO を残しています（フォールバック価格の導入検討）。
- news_nlp は OpenAI 呼び出しに強く依存するため、ローカルオフライン時の代替フローやメトリクス保存の強化を検討。
- run_monitoring は監視用 DB と本番 DB を共用する設計（意図的）だが、運用上の要求に応じて分離の検討が必要。

貢献/開発
- 初期実装として内部 API（モジュール公共インターフェース）を明確にし、ユニットテストで検証しやすい純粋関数設計を優先しています。今後テストカバレッジ・CI 設定の追加を推奨します。
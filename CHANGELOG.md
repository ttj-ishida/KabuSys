# CHANGELOG

すべての注目すべき変更を記録します。これは「Keep a Changelog」準拠の形式です。

- 既知の互換性方針: セマンティックバージョニングを採用します。  
- 日付表記: YYYY-MM-DD

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-17
初回リリース。システム全体のコア機能を実装しています。

### 追加
- 全体
  - パッケージ kabusys 初版リリース（__version__ = "0.1.0"）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）。
  - .env 自動ロード機能を実装（.env, .env.local）。既存 OS 環境変数を保護するための上書き制御と KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - 環境設定を取得する Settings クラスを実装。多数の設定プロパティ（DBパス、APIキー、監視閾値、ログレベル、環境種別など）を提供。

- 実行 / 監視
  - 実行エントリポイント:
    - run_execution: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用（本番 DB と分離）。
    - run_monitoring: SystemMonitor ポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（デフォルト 60 秒）を上書き可能。監視は環境に関係なく本番 sqlite_path を使用する点に注意。
  - 停止制御:
    - 両スクリプトともプロジェクト配下 data/stop_requested.flag（停止フラグ）を監視し、検知時に安全終了する仕組みを実装。
    - run_execution は PID ファイル管理とスレッドベースの実行/停止を実装。

- データベース / 分析
  - DuckDB / SQLite 接続の利用を標準化（各モジュールは接続を受け取ってクエリを実行）。
  - monitoring_db 初期化呼び出しを適切な箇所で実施（冪等に監視テーブルを保証）。

- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルから上位 N を選出（スコア降順、同点タイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分の実装。全スコアが 0 の場合のフォールバックと警告。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限のフィルタリング（既存保有の時価計算、sell_codes の除外対応、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知のレジームは 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の各割当方式に基づく発注株数算出。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）でのスケールダウン、cost_buffer による保守見積り、残差分の lot_size 単位での再配分ロジックなどを実装。

- 研究・リサーチ
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value: DuckDB 上の prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを計算。
    - 大きな窓幅や欠損データ取扱い（必要な行数未満は None を返す）を実装。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括で取得する汎用実装、ホライズン検証を含む。
    - calc_ic: スピアマンのランク相関（IC）計算の実装（結合・欠損除外・最小サンプルチェック）。
    - rank / factor_summary: ランク（同順位は平均ランク）および基本統計サマリー (count/mean/std/min/max/median) を実装。
  - research パッケージは kabusys.data.stats の zscore_normalize を再エクスポート。

- ニュース NLP（AI スコアリング）
  - ai.news_nlp:
    - raw_news を指定ウィンドウ（JST 前日15:00〜当日08:30）で集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜+1.0）を算出して ai_scores テーブルに書き込む設計を実装。
    - バッチサイズ、トークン肥大化対策（記事数・文字数トリム）、JSON 出力のバリデーション、スコアのクリップ、リトライ（429/5xx/ネットワーク/タイムアウト）に対する指数バックオフの方針を定義。
    - 実装はフェイルセーフ設計（API 失敗時はスキップして継続）を志向。
    - （注）ファイル末尾で関数の読み込み/処理部分が部分的に切れている箇所があるため、細部は本リリース時点の実装状況に依存。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定。失敗時（権限不足 等）は警告を出してスキップ。
    - set_cpu_affinity: プロセスを先頭 N コアにピン留めする機能を実装。引数検証とエラー時のフォールバックあり。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用の検証レポート生成 CLI を実装。PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を参照可能。
    - システム安定性（稼働率）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）を算出して PASS/FAIL 判定（しきい値はソース内定義）を行う。
    - P95 計算や日付フィルタの付加、DB 存在チェック、SQL 発行時の OperationalError に対する堅牢化を実装。

### 修正（実装上の注意点／堅牢化）
- .env パーサ:
  - export KEY=val 形式、クォート（シングル／ダブル）内のバックスラッシュエスケープ、インラインコメントの扱い、クォートなし値内のコメント判定（直前に空白またはタブ）など多くのケースに対応する堅牢なパーサを実装。
- MONITOR_POLL_INTERVAL のパース:
  - 不正な値（非整数、0 以下など）は警告を出してデフォルト（60 秒）にフォールバックする安全設計。
- SQL / 集計処理:
  - ファクター/レポート系でデータ不足・NULL に対して None を返すなどの防御的実装。
  - DuckDB/SQLite に対するクエリ実行箇所で OperationalError を捕捉してフォールバックする箇所を追加（tools.paper_verification_report 等）。

### 既知の制約 / 注意事項
- run_monitoring は「監視」用 DB として settings.sqlite_path（デフォルト data/monitoring.db）を常に使用する設計で、開発環境であっても本番用パスを参照する点に注意してください（ソースコメント参照）。
- run_execution は paper_trading モード時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。paper_trading モードは Settings.is_paper に依存します。
- ai.news_nlp の実処理部分がファイル末尾で途中まで（切断）になっている箇所があるため、OpenAI API 周りのフルパス実装はリリース後の修正が予想されます。
- 一部 TODO コメントあり（例: position_sizing の銘柄別 lot_size 拡張、価格欠損時のフォールバック価格など）。

### セキュリティ
- API キー等の機密情報は環境変数経由で取得。Settings._require により必須設定が未設定の際は明確に例外を投げる設計。

---

今後の予定（例）
- ai.news_nlp の完全実装・テストと、失敗時の部分ロールバック戦略の強化。
- 追加の単体テストおよび統合テストの整備（特に DB クエリと並列実行部分）。
- position_sizing の銘柄別 lot_size 対応と価格フォールバックロジックの導入。

（以上）
# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお、この CHANGELOG はリポジトリ内のコードを解析して推測に基づき作成したものであり、実際のリリースノートと差異がある可能性があります。

## [Unreleased]

（今後の変更をここに記載）

---

## [0.1.0] - 2026-04-16

初回公開リリース。以下の主要機能群とユーティリティを実装しました。

### Added
- 基本パッケージ情報
  - kabusys パッケージ初期リリース（__version__ = 0.1.0）。
- 実行用エントリスクリプト
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 起動前 / 実行中に data/stop_requested.flag を監視して安全に停止。
    - 実行用 PID ファイル機能（data/execution.pid）でプロセス管理。
- 監視用エントリスクリプト
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（既定 60 秒）。不正な値は警告を出して既定値にフォールバック。
    - 監視は環境に関係なく本番 sqlite_path を使用（設計上の注意点として明記）。
    - 起動時にプロセス優先度を High に設定（utils の set_process_priority を使用）。
    - data/stop_requested.flag を検知してループを終了。
- 設定 / 環境変数管理
  - config.py：Settings クラスを実装。
    - .env, .env.local の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 読み込み時に OS 環境変数を保護（上書き禁止）する仕組みを導入。
    - export KEY=val 形式やシングル/ダブルクォート、エスケープシーケンス、インラインコメントを考慮した .env パーサ実装（_parse_env_line）。
    - 各種必須値チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）、DB パス、paper_trading 関連設定、監視閾値、環境（development/paper_trading/live）などをプロパティとして提供。
    - PAPER_FILL_MODE のバリデーション実装（instant/partial/never/reject のみ許容）。
- ポートフォリオ構築ロジック（純粋関数）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順＋タイブレークで上位 N 件選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装（スコア合計が 0 の場合は等分配にフォールバックして警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック。既存保有を元にセクターごとのエクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear、およびフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: weight / candidates / risk_based 等の複数アルゴリズムに基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer を考慮した保守的見積り、端数の割振りロジックを実装。
- 研究（Research）モジュール
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value：DuckDB の prices_daily / raw_financials を用いたファクター計算（MA200, ATR20 等）。
    - データ不足時の None 戻りや行数チェックを行う安全設計。
  - research.feature_exploration
    - calc_forward_returns：将来リターン（複数ホライズン）を一度のクエリで取得する設計。
    - calc_ic：Spearman（ランク相関）による IC 計算（ランクは同順位を平均ランクで処理）。
    - factor_summary：count/mean/std/min/max/median を算出する要約関数。
  - research.__init__ で主要関数を公開。
- ニュース NLP（AI）モジュール（初期実装）
  - ai.news_nlp：raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを算出する処理の骨格を実装。
    - タイムウィンドウ計算（JST→UTC 変換）、1 銘柄あたりのトークン制限、バッチサイズ、スコアクリップ（±1.0）、リトライ（指数バックオフ）等の方針を実装。
    - レスポンス検証・部分成功時の DB 書き込み戦略などの設計を盛り込む（score_news は途中実装箇所あり）。
- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）を吸収して優先度設定を行う。未対応 OS は警告でスキップ。権限不足や未実装 API に対しては警告で安全にフォールバック。
    - set_cpu_affinity: 指定コア数に CPU affinity を設定（1 未満の値は ValueError）。
- 監視 DB 初期化
  - monitoring.monitoring_db (参照される初期化関数 init_monitoring_db を呼び出す箇所を追加)。監視テーブルが存在することを保証する呼び出しを run_monitoring/run_execution 両方で行う。
- ツール
  - tools.paper_verification_report：Paper Trading の検証レポート生成ツールを追加。
    - システム稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を出力。
    - コマンドラインオプションで期間指定（--from / --to）や DB パス指定（--db）。
    - DB テーブルがない場合や OperationalError に対しては安全に N/A を返すよう保護実装。
    - P95 計算、日付フィルタ生成、フォーマット関数などを実装。

### Changed
- 設計上の明確化
  - 監視プロセス（run_monitoring）は KABUSYS_ENV に依存せず常に production 用 sqlite_path を参照する仕様となっていることを起動スクリプトのドキュメントに明記（意図的な設計）。
  - run_execution は paper_trading 環境時に DB を完全分離する仕様（paper_sqlite_path を使用）を明示。
- .env ローダ
  - OS 環境変数を保護するため、.env ファイル読み込み時に既存キーを上書きしない / 上書きする挙動を制御するフラグ（override）を採用。

### Fixed
- .env パーサ（_parse_env_line）の堅牢性向上
  - export キーワード対応、シングル／ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い（クォートあり/なしでの違い）を実装し、実務でよくある .env の記述バリエーションに対応。
- run_monitoring のポーリング間隔取得
  - MONITOR_POLL_INTERVAL に 0 以下や非整数が渡された場合に time.sleep での ValueError を避け、警告ログを出してデフォルト（60秒）にフォールバックするように修正。

### Security
- OpenAI API キーの取り扱い
  - ai.news_nlp.score_news は引数で api_key を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照する仕様。未設定時は明示的に ValueError を発生させることで鍵漏洩や誤動作を避ける設計。

### Deprecated
- なし

### Removed
- なし

---

注記:
- ai/news_nlp.score_news はファイル末尾で途中切れ（score_news の続きが存在しない/未表示）ため、完全な動作保証は現状ではできません。実運用に投入する場合は未実装箇所の完成・テストを推奨します。
- 実際のリリースノート作成時は、コミット履歴やリリース時期（正式なリリース日）に基づく追記・修正を行ってください。
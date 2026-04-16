# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-16

### Added
- 初期公開: KabuSys 基本モジュール群を追加。
- 実行/監視エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB を使用して本番 DB と完全に分離。
    - BrokerClientFactory を経由したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド実行を実装。
    - 停止フラグ (data/stop_requested.flag) と pid ファイル (data/execution.pid) を利用して外部停止を実現。
    - RiskConfig によるリスクパラメータ適用（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視起動時にプロセス優先度を設定（utils.process_priority.set_process_priority）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（※挙動に注意）。
    - 停止フラグファイル検知でループ終了。
- 設定管理
  - config.Settings クラスを追加。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env/.env.local の読み込み優先順位 (OS 環境変数 > .env.local > .env) と保護機構（既存 OS 環境変数は上書きしない）。
    - .env の行パーサを実装（export プレフィックス対応、クォート文字列内のバックスラッシュエスケープ対応、インラインコメント処理など）。
    - 各種プロパティを実装（J-Quants / Kabu API 用トークン、LINE 設定、duckdb/sqlite パス、paper_trading 用パス、監視しきい値、KABUSYS_ENV 検証など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates(): シグナルのソートと候補抽出機能を追加。
    - calc_equal_weights(), calc_score_weights(): 等配分・スコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes(): allocation_method (risk_based / equal / score) に基づく株数計算。lot_size、cost_buffer を考慮した aggregate cap スケーリング、単元丸め、利用可能現金に応じたスケールダウン機構を実装。
  - portfolio.risk_adjustment
    - apply_sector_cap(): セクター集中制限（既存保有を考慮して当日新規候補を除外）。
    - calc_regime_multiplier(): マーケットレジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
- Research / ファクター計算
  - research.factor_research
    - calc_momentum(), calc_volatility(), calc_value(): DuckDB (prices_daily / raw_financials) を用いたファクター計算を追加（MA200, ATR20, リターン等）。
    - DuckDB SQL を活用した高効率実装（窓関数、集計）。
  - research.feature_exploration
    - calc_forward_returns(): 将来リターン（複数ホライズン）計算を追加。
    - calc_ic(): スピアマンランク相関（IC）計算を追加（ランク関数含む）。
    - factor_summary(): 基本統計量の算出機能を追加。
- AI ニュース NLP（実験的）
  - ai.news_nlp
    - raw_news を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルに書き込む処理の骨格を追加。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST → UTC で変換） calc_news_window() を提供。
    - バッチサイズ、最大記事数／文字数によるトークン肥大対策、レスポンス検証、スコアクリッピング（±1.0）、リトライとバックオフ方針を設計。
    - 注意: 実装はフェールセーフ設計（API失敗はスキップ・部分書き換え）を想定。現状コードが一部で切れている（実装継続の余地あり）。
- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を参照し、稼働率・注文成功率・送信率・P95 レイテンシ等を出力。閾値に基づく PASS/FAIL 判定、コマンドライン引数 (--from, --to, --db) に対応。
    - P95 計算、各種クエリの堅牢化（テーブル未存在時に例外を吸収して N/A を返す）。
- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX の差分を吸収して優先度設定を行う。失敗時は警告ログにフォールバック。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 固定を実装（存在しない環境ではスキップし警告）。
- パッケージ初期化
  - __init__.py にバージョン定義 __version__ = "0.1.0" を追加。

### Changed
- .env ロード動作
  - 自動読み込み時に OS 環境変数を保護する（.env/.env.local の上書きを制御）。
  - プロジェクトルート探索を __file__ から辿る方式で実装し、CWD に依存しないロードを実現。

### Fixed
- 安全性向上 / フォールトトレラント化
  - MONITOR_POLL_INTERVAL が不正（非数値や 0 以下）の場合はデフォルトにフォールバックして警告を出す（run_monitoring）。
  - process_priority の権限エラーや未サポート系 OS での例外を捕捉してログ出力にフォールバック。
  - paper_verification_report の各クエリはテーブルがない場合に sqlite3.OperationalError を捕捉して N/A を返すようにし、レポート生成が中断しないように改善。
  - position_sizing の aggregate スケーリングで端数割当を再現性ある順序で行うよう調整（残差ソートの安定化）。

### Known issues / Notes
- run_monitoring は「環境にかかわらず本番 sqlite_path を使用する」挙動があるため、テストや paper_trading 環境で監視 DB を分離したい場合は注意が必要です。
- ai/news_nlp モジュールは設計が詳細に書かれているものの、ソースが途中で切れている箇所があります（実装・テストが未完の可能性あり）。使用時は最新実装を確認してください。
- position_sizing / risk_adjustment の一部ロジックは価格欠損時のフォールバック（前日終値等）をまだ実装しておらず、price が欠損するとエクスポージャーが小さく見積もられる可能性があります（TODO コメントあり）。
- DuckDB を使用するファクター計算は prices_daily / raw_financials テーブルに依存します。テーブルスキーマやデータ整備に注意してください。

### Security
- なし

---

今回のリリースはアプリケーションのコアとなる多くの機能（設定管理、実行・監視エントリポイント、ポートフォリオ構築、リスク制御、研究用ファクター計算、ニュースNLP の骨格、運用ツール）を追加するものです。各モジュールは単体でのテストや運用検証を推奨します。
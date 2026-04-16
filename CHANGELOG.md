CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
（以下の履歴は提供されたソースコードから推測して作成した初回リリース向けの要約です。）

Unreleased
----------

- なし

[0.1.0] - 2026-04-16
--------------------

Added
- 初期リリースを追加。
- コア機能
  - portfolio: 銘柄選定・配分・株数算出の純粋関数群を実装。
    - select_candidates: スコア降順で候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重計算（スコアが全て0の場合は等配分にフォールバック）。
    - calc_position_sizes: risk_based / equal / score の各方式に対応した発注株数算出（単元株丸め・aggregate cap スケーリング・コストバッファ対応）。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
  - research: DuckDB を利用した研究用モジュール群。
    - factor_research: モメンタム（1M/3M/6M, MA200乖離）、ボラティリティ（ATR20、平均出来高等）、バリュー（PER, ROE）を計算。
    - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（calc_ic）、統計サマリ（factor_summary）等の研究ユーティリティ。
  - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化し ai_scores に書き込むバッチ処理ロジック（ウィンドウ算出、チャンク化、リトライ、レスポンス検証、スコアのクリップ等）。
  - tools.paper_verification_report: Paper Trading 向け検証レポート生成 CLI（稼働率、注文成功率、レイテンシ、リスク却下数の集計・判定）。日付フィルタ・DB パス指定対応。
  - 実行スクリプト
    - run_execution: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用して本番 DB と分離。BrokerClientFactory を介したブローカ抽象化、リスクマネージャー・オーダーマネージャー等の組み立て、停止フラグ／PID ファイル管理、スレッド実行。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き、停止フラグ検知で終了。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
  - utils: OS に依存しないプロセス優先度・CPU affinity 設定ユーティリティ（set_process_priority, set_cpu_affinity）。Windows / POSIX の差分吸収とアクセス権限例外処理を実装。
  - config: 環境変数管理（.env 自動ロード、.env/.env.local の優先順、エスケープ・クォート・コメント処理、保護された OS 環境変数の上書き制御）。Settings クラスで各種設定値（DB パス、閾値、API トークン等）を提供しバリデーションを実装。

Changed
- （初回リリースのためリファクタや既存コードの変更履歴は無し。コード上の設計方針として以下を明示）
  - Paper Trading と本番 DB を明確に分離（PAPER_TRADING_SQLITE_PATH のサポート）。
  - 監視プロセスは KABUSYS_ENV に依存せず本番の監視 DB を参照する仕様に設計。
  - 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索し、CWD に依存しないように実装。

Fixed
- 入力バリデーションと堅牢性の強化
  - MONITOR_POLL_INTERVAL が不正な値の場合にデフォルトにフォールバックする処理を追加（負値や非数値による time.sleep の例外を回避）。
  - PAPER_FILL_MODE の許容値チェックを実装（不正値で ValueError）。
  - KABUSYS_ENV / LOG_LEVEL の許容値チェックを追加。
  - .env のパース処理でクォート内のエスケープ処理、コメントの取り扱いを改善。
  - DuckDB/SQLite クエリ周りでデータ欠損時（テーブルがない、NULL の伝播など）に安全に N/A を返すガードを実装（tools と research の各クエリで例外処理）。
  - process_priority / cpu_affinity で権限不足や未対応プラットフォームを警告してスキップするようにし、起動時の致命的エラーとならないように改善。

Security
- API キー類（OpenAI, J-Quants, kabu API など）は Settings で必須化・参照する実装になっており、未設定時は ValueError を送出して明示的に失敗する設計。

Documentation / Notes
- 各モジュールに詳しい docstring を追加し、設計意図（PortfolioConstruction.md / StrategyModel.md 等に準拠していること）や TODO（例: price のフォールバック戦略、銘柄ごとの lot_size 拡張）を明記。
- tools.paper_verification_report は CLI 引数で日付範囲・DB パスを指定可能。出力は判定基準（稼働率・成功率・レイテンシ閾値）と Pass/Fail を明示。
- ai.news_nlp は OpenAI API 呼び出しで指数バックオフや部分失敗時の部分更新戦略（影響を受けるコードのみ DELETE→INSERT）を取ることで堅牢性を高める設計。

Known limitations / TODO
- 一部の挙動は注記付きで将来的な改善を想定（例: price が欠損時のフォールバック、銘柄別 lot_size の導入）。
- ai.news_nlp の実装ファイルが途中で切れている箇所がある（提供コードの末尾が途中で truncation されているため、完全な処理フローの実装は今後補完が必要）。

免責
- 本 CHANGELOG は提供されたソースコードの内容から推測して作成したものであり、実際のコミット履歴・変更差分に基づくものではありません。正式なリリースノートを作成する場合は Git の履歴やリリース手順に基づいて更新してください。
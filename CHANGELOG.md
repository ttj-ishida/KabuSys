# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
主なカテゴリ: Added, Changed, Fixed, Deprecated, Removed, Security。

## [Unreleased]
- ドキュメント・内部注記の整備やロギングの強化を予定。

## [0.1.0] - 2026-04-16
初回リリース。日本株自動売買システム "KabuSys" の基本機能を実装しました。以下はコードベースから推測される主要な追加・修正点の概要です。

### Added
- 実行・監視エントリポイント
  - run_execution.py: 実行エンジン（ExecutionEngine）を起動する CLI ラッパーを追加。環境変数に応じて paper_trading 用 DB に切り替え、BrokerClientFactory 経由でブローカークライアントを生成。エンジンは別スレッドで実行され、停止フラグ（data/stop_requested.flag）や実行 PID（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL によるポーリング間隔上書き、起動時にプロセス優先度を設定する仕組みを実装。

- 設定管理
  - config.py: .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml）を実装。.env / .env.local の読み込み順と上書きルールを整備。export プレフィックス・クォート・インラインコメントのパースに対応。Settings クラスで各種設定（DB パス、Paper Trading 用設定、監視閾値、環境名検証など）を提供。

- 実行系コンポーネント（概要）
  - ExecutionEngine の起動に必要なコンポーネント群を組み立てるコードを追加（OrderRepository / OrderManager / RiskManager / Reconciler 等の初期化）。
  - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、broker.get_available_cash() を初期ポートフォリオ値として利用。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio/position_sizing.py: 各配分方式（risk_based / equal / score）に基づく株数計算、単元株（lot_size）丸め、aggregate cap によるスケールダウンを実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。

- リサーチ / ファクター計算
  - research/factor_research.py: Momentum、Volatility、Value ファクターを DuckDB 上の prices_daily / raw_financials から計算する関数を実装（MA200、ATR20、各種リターン等）。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic = Spearman ρ）、ランク変換（rank）、ファクター統計サマリ（factor_summary）を実装。
  - research/__init__.py で主要ユーティリティをエクスポート。

- ニュース NLP（AI 統合）
  - ai/news_nlp.py: raw_news と news_symbols から銘柄ごとの記事を集約し OpenAI（gpt-4o-mini）でセンチメントを評価、ai_scores テーブルへ書き込む処理を設計。バッチ処理（最大バッチサイズ）、文字数・記事数のトリム、API エラーに対する指数バックオフリトライ、レスポンス検証・スコアクリッピングなどの方針を実装。
  - OpenAI API キーの必須チェックを行い、未設定時は ValueError を送出。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力する CLI。期間フィルタ（--from / --to）と DB パス指定（--db）対応。複数の SQL クエリに対するエラー（テーブル未作成など）を安全にハンドリング。

- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度（Windows: HIGH_PRIORITY_CLASS 等 / POSIX: nice 値）と CPU affinity 設定を行うユーティリティを追加。権限不足や未対応プラットフォームを安全にスキップしログ出力。

- 初期 DB セットアップ
  - 各起動スクリプトで init_monitoring_db を呼び出し、監視テーブルが存在することを保証（冪等）。

### Changed
- 実行/監視の DB 利用ポリシーを明文化
  - run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する旨の仕様（監視データは本番 DB を対象）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用し、本番 DB と完全に分離する仕様を追加（paper_trading による独立した検証が可能）。

- .env 自動読み込みの振る舞い
  - OS 環境変数を保護する protected 機能を追加し、.env/.env.local の上書きルールを制御。

- 各種計算での安全ガードを追加
  - calc_score_weights: 全銘柄スコアが 0.0 の場合に等金額配分へフォールバックし WARN を出す。
  - factor_research / volatility 等: ウィンドウ内のデータ数が不足する場合に None を返す等、欠損データに寛容な挙動を実装。
  - calc_forward_returns: horizons の検証（正の整数かつ最大 252 日）を追加。

### Fixed
- エラーハンドリングとログの改善
  - 起動ループ中の monitor.check_once() 呼び出しで例外発生時に例外内容をログ出力してループを継続するように変更（run_monitoring）。
  - process_priority の設定で psutil の例外（AccessDenied / NotImplemented）発生時に警告ログを出してスキップするように変更。

- レポート/集計の堅牢化
  - paper_verification_report: DB にテーブルが存在しない場合の sqlite3.OperationalError を捕捉してデフォルト値を返す処理を追加。P95 計算で空データ時は None を扱うようにした。

- ポジションサイズ計算の安全弁
  - calc_position_sizes: price が欠損・0 の場合はスキップし、aggregate cap スケール時の丸め・端数処理で単元株（lot_size）単位の調整を行うロジックを改善。

### Deprecated
- なし（初回リリースのため該当なし）。

### Removed
- なし（初回リリースのため該当なし）。

### Security
- ai/news_nlp.py: OpenAI API キー未設定時に明確にエラーを返すように変更（誤った無限リトライや無条件の API 呼び出し防止）。
- .env 読み込み時に OS 環境変数を保護（protected set）することで、システム側の重要な環境変数が意図せず上書きされるリスクを低減。

---

備考:
- 多くのモジュール（research, portfolio, execution, monitoring, ai）が「DB 参照なし／純粋関数」または「DuckDB/SQLite 接続を受ける」設計で分離されており、単体テストやローカル検証がしやすい構造になっています。
- ai/news_nlp.py の末端での処理（記事集約 → API 呼び出し → DB 書き込み）については、実装方針とエッジケース（レスポンス検証、部分失敗時のデータ保護）が明記されていますが、一部コードがスナップショット上で途中まで切れている可能性があります。運用前に API 呼び出し・DB 書き換え部分の統合テストを推奨します。

もし特定ファイルごとにより詳細な変更点の追記や、バージョン分割（パッチ・マイナー・メジャー）での振り分けを希望される場合は、対象ファイルや想定の過去リビジョン（差分）を教えてください。
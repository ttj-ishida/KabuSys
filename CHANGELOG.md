CHANGELOG
=========

このファイルは「Keep a Changelog」形式に準拠しています。  
バージョン履歴は主にソースコードから推測して作成しています（実装コメント／TODO／ログ文などに基づく）。

Unreleased
----------

### 追加予定 / 注意事項
- ai/news_nlp モジュールの実装は途中（ソースが途中で切れている箇所あり）。OpenAI 呼び出し周りの処理や記事フェッチの続き実装が必要。
- position_sizing / risk_adjustment にいくつかの TODO が残る（銘柄別 lot_size、価格フォールバックなど）。
- DuckDB に対する一部操作で executemany 等の扱いに注意喚起コメントあり（部分失敗時の保護など）。
- OS・権限によってはプロセス優先度 / CPU affinity の設定がスキップされる（ログに警告が出る実装）。

0.1.0 — 2026-04-16
------------------

Added
- パッケージ基盤
  - kabusys パッケージを追加。__version__ = "0.1.0"。
  - モジュール群をエクスポート（portfolio, research, ai, monitoring, execution, tools, utils 等）。

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - export KEY=val 形式、シングル／ダブルクォートやバックスラッシュエスケープ、行内コメント対応の堅牢な .env パーサーを実装。
  - 環境変数の必須チェック（_require）と各種設定プロパティ（DBパス、KABUSYS_ENV 検証、PAPER_FILL_MODE 検証など）を提供。
  - OS 環境変数を保護するための読み込み優先度と上書き制御を導入。

- 実行エンジン起動スクリプト（kabusys.run_execution）
  - ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と完全分離。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てを行い、ExecutionEngine をスレッドで実行。
  - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の扱い、停止時の安全停止処理を実装。
  - RiskConfig のデフォルト値を明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）し、初期ポートフォリオ値を broker.get_available_cash() から取得して注入。

- 監視起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor 用ポーリングループ起動スクリプトを追加。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の実装（monitoring DB 初期化呼び出しを含む）。
  - プロセス優先度を起動時に設定し、例外時もループ継続する安全策を用意。

- データベース初期化（monitoring_db 参照）
  - monitoring 用テーブルの冪等な初期化処理を呼び出す箇所を各起動スクリプトに統合（監視テーブルの存在を保証）。

- ユーティリティ（kabusys.utils.process_priority）
  - プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority）。
  - CPU affinity 固定関数 set_cpu_affinity を追加。権限や未対応 OS の場合は安全にスキップしてログ出力。
  - Windows/Linux/macOS（POSIX）向けの既定値マッピングを実装。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全0時のフォールバック警告あり。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。unknown セクターの扱い、レジーム不明時のフォールバックを実装。
  - position_sizing: allocation_method（risk_based / equal / score）に応じた発注株数計算（単元株丸め、max per stock、aggregate cap のスケーリング、cost_buffer の考慮）を実装。残余キャッシュ配分のための端数処理（fractional remainder）も導入。
  - 上記関数は純粋関数（DB 参照なし）でメモリ内計算のみ行う設計。

- リサーチ／ファクター計算（kabusys.research）
  - factor_research: Momentum（calc_momentum）、Volatility（calc_volatility）、Value（calc_value）を実装。DuckDB 接続を受け、prices_daily / raw_financials テーブルを参照して SQL ベースで計算。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージのエクスポートを整備（zscore_normalize を data.stats から取り込み）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を使って銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ格納する処理を追加（バッチサイズ、トークン肥大化対策、スコアクリップ、リトライ／バックオフ等の設計を反映）。
  - タイムウィンドウ計算（JST→UTC）やレスポンスバリデーション、部分失敗時に既存スコアを守るための部分置換戦略を導入。
  - API キー未設定時は例外（ValueError）を送出。

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 用検証レポート生成スクリプトを追加。コマンドライン引数で期間指定（--from/--to）および DB パス指定（--db）に対応。
  - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、レイテンシ（avg/max/P95）等を算出し、閾値に基づく PASS/FAIL 判定を出力。
  - P95 計算、日付フィルタ生成、テーブル存在エラーに対する保護（OperationalError 捕捉）を実装。

Changed
- 環境とデータ分離
  - paper_trading 環境では SQLite を本番と分離（settings.paper_sqlite_path を使用）。実行スクリプトは環境に応じた DB 接続を切り替えるよう設計。

Fixed
- .env の自動読み込みで OS 環境変数が上書きされないよう保護（protected キー群を導入）。

Security
- OpenAI API キーは明示的な引数または環境変数 OPENAI_API_KEY を要求。未設定時は例外を投げることで誤った無認証呼び出しを防止。

Notes / Known limitations
- ai/news_nlp の実装が途中で切れており、記事フェッチや API 呼び出しの続き実装が必要。現状のファイルは設計と一部実装を含むが完成には至っていない。
- position_sizing の将来拡張（銘柄別 lot_size、price フォールバックなど）は TODO コメントあり。
- 一部機能は権限（プロセス優先度、CPU affinity）やプラットフォーム依存の動作によりスキップされる場合がある（ログで通知）。
- DuckDB/SQLite のスキーマ前提（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs 等）が存在することが前提。

参考
- コード内の docstring / TODO / ログメッセージを元に上記を作成しています。実際のリリースノートとして利用する際は、リリースごとの差分やテスト結果・マイグレーション手順等を補記してください。
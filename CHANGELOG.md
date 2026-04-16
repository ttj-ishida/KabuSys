CHANGELOG
=========

フォーマットは「Keep a Changelog」準拠。
このファイルは、コードベースから推測できる実装内容・設計決定に基づいて作成しています。

Unreleased
----------

- （現在のワーキングツリーに未リリースの変更はありません）

0.1.0 - 2026-04-16
------------------

Added
- 基本アプリケーションを実装（初回リリース）。
  - kabusys パッケージ（__version__ = 0.1.0）。
- 実行エントリ / ランナー
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - エンジンを別スレッドで実行し、data/stop_requested.flag による安全な停止制御。
    - 起動前に停止フラグが立っている場合は起動せず終了。
    - 実行用 PID ファイル（data/execution.pid）を利用。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト: 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。KeyboardInterrupt を捕捉して正常終了。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.Settings による環境変数ラッパーを実装。
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）を行い、OS 環境変数を上書きから保護する仕組みを導入。
    - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 環境変数の必須チェック (_require) と各種検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、PID/kill flag パス、監視閾値等のプロパティを提供。
- Portfolio モジュール（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順による候補選定（同点時に signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分 / スコア正規化配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を抑えるための候補除外ロジック。既存保有のセクターエクスポージャを計算し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム（"bull"/"neutral"/"bear"）に基づく投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: 重み・候補・現金・制約（max_position_pct, max_utilization, lot_size, cost_buffer 等）に基づき発注株数を計算。risk_based / equal / score の方式をサポート。aggregate cap 超過時のスケーリングと端数処理（lot 単位での再配分）を実装。
- Research / ファクター・解析モジュール
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（MA200）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials を使った PER / ROE の計算（target_date 以前の最新財務データを使用）。
    - 全て DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得。
    - calc_ic: ファクター値と将来リターンのスピアマン（ランク）相関（IC）計算。データ不足時は None を返す。
    - factor_summary / rank: 基本統計量計算・ランク変換ユーティリティ。
  - research パッケージは zscore_normalize を data.stats からエクスポート。
- AI ニュース NLP（部分実装）
  - ai.news_nlp モジュールを実装（OpenAI API を用いたニュースセンチメント集約・スコア化）。
    - ニュース収集ウィンドウ計算（JST ベース → UTC 変換）を提供（calc_news_window）。
    - バッチ処理（最大 _BATCH_SIZE=20）、出力クリッピング（±1.0）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）の方針を実装。
    - JSON mode を期待するシステムプロンプトを定義し、レスポンス検証・部分更新（対象コードのみ DELETE→INSERT）方針を採用する設計（実装途中の箇所あり）。
- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）を吸収したプロセス優先度設定（psutil を利用）。権限不足や未対応 OS の場合は警告してスキップ。
    - set_cpu_affinity: 最初の N コアにプロセスを固定する機能。引数チェックと失敗時に警告。
- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数等。
    - PASS/FAIL 判定のしきい値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - DB がない場合やテーブルが存在しない場合に耐性を持つ（OperationalError を補足して N/A を出力）。
    - コマンドライン引数 (--from, --to, --db) をサポート。
- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db の呼び出しにより監視テーブルの冪等な初期化を行う（monitoring 側で常に呼ぶことでテーブル存在を保証）。

Changed
- 設計ドキュメント準拠
  - PortfolioConstruction.md / StrategyModel.md / Research の設計思想に沿った純粋関数の分割と副作用排除（多くの関数はメモリ内計算のみで DB 参照なしと明示）。
- .env 読み込み
  - .env/.env.local の優先度と OS 環境変数保護を明確化（.env.local は override=True で読み込み、OS 環境変数は protected として上書き禁止）。
  - export KEY=val 形式やクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いをサポートする堅牢なパーサを実装。

Fixed
- 安全性 / 堅牢性の強化
  - run_execution / run_monitoring で finally ブロックにより sqlite/duckdb 接続を確実に close するように実装。
  - calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバック（WARNING を出力）。
  - position_sizing: 価格欠損時のスキップや lot_size 単位での丸め処理、aggregate cap 超過時のスケーリングと端数処理を実装して破綻を防止。
  - tools.paper_verification_report: P95 計算、日付フィルタの SQL 生成、テーブル欠如時のフォールバック（N/A）を実装。
  - utils.process_priority: 権限不足や未対応 OS の場合に例外を抑えて警告するように修正。
  - ai.news_nlp: API キー未設定時に ValueError を投げ、呼び出し側で明確に扱えるようにした（score_news）。

Security
- 環境変数の扱いに注意する旨を各所で明示（API キーやパスワードは必須チェックあり）。.env の自動ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）にしてテスト等での制御を容易に。

Notes / Important
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計になっています。運用上の分離を期待する場合は注意してください（paper_trading と監視 DB を別にしたい場合は設定変更が必要）。
- ai.news_nlp モジュールは設計方針・多数の堅牢性対策（バッチ、リトライ、検証、部分置換）を備えていますが、一部処理（全文実装・エラーハンドリング周り）はコード断片により途中の可能性があります。実運用前に完全動作確認を推奨します。
- .env パーサは Bash スタイルの単純な実装であり、極端に複雑なシェル埋め込み等は想定していません。

今後の予定（想定）
- ai.news_nlp の完全実装と単体テスト（API エラーの細かい分類・再試行ロジックの拡充）。
- ExecutionEngine / SystemMonitor の統合テストおよび e2e の運用検証。
- 銘柄別 lot_size や取引手数料モデルの拡張（stocks マスタからの読み込み等）。
- ドキュメント（README / 操作手順 / 環境構築）の整備。

---
この CHANGELOG はコード内のコメント、関数シグネチャ、ログメッセージ等から推測して作成しています。実際のリリースノートとして利用する場合は、実装者が変更点を確認のうえ必要に応じて補正してください。
CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
変更はセマンティックバージョニングに従います。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-17
------------------

Added
- 初期リリース。以下の主要機能・モジュールを実装。
  - 実行系 / 監視系起動スクリプト
    - run_execution.py: ExecutionEngine 起動処理を実装。BrokerClientFactory 経由でブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、別スレッドでエンジンを実行します。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用して本番 DB と分離します。起動前に停止フラグ（data/stop_requested.flag）をチェックします。
    - run_monitoring.py: SystemMonitor をポーリングする監視ループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する点に注意。
    - 両スクリプトとも起動直後にプロセス優先度を "high" に設定するユーティリティを呼び出します（utils.process_priority.set_process_priority）。
  - 設定管理
    - config.py: .env / .env.local の自動読み込みを実装（OS 環境変数を保護）。.env パーサは export プレフィックス、引用符付き文字列、エスケープ、インラインコメントなどに対応。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。Settings クラスを提供し、各種設定（DB パス、PaperTrading 用パス、閾値、環境チェックなど）をプロパティとして取得できます。値検証（例: KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL）を行い、無効値のときは ValueError を送出します。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（スコア降順・タイブレーク）と等金額・スコア加重配分を実装。スコアが全て 0 の場合は等配分へフォールバックして警告を出力。
    - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。sell_codes 引数で当日売却予定銘柄の除外に対応。未知レジームは 1.0 でフォールバック。
    - portfolio.position_sizing: allocation_method（risk_based / equal / score）に応じた株数決定ロジックを実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）および remainder による追加配分ロジック、cost_buffer による保守的コスト見積りを実装。
  - リサーチ / ファクター計算
    - research.factor_research: DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）を実装。prices_daily / raw_financials を参照し、MA200、ATR、平均売買代金、PER/ROE などを計算。ウィンドウ不足のときは None を返す設計。
    - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、rank・統計サマリーを実装。外部依存（pandas 等）に頼らない純 Python 実装。
  - ニュース NLP（AI スコアリング）
    - ai.news_nlp: raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ書き込む処理を実装。バッチ処理、トークン肥大化対策、429/5xx/タイムアウト等のリトライ（指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（指定コードのみ置換）等が設計に含まれます。calc_news_window ユーティリティでニュース収集ウィンドウ（JST→UTC 変換）を提供。API キーは引数または OPENAI_API_KEY 環境変数で指定。
  - ユーティリティ
    - utils.process_priority: Windows / POSIX（Linux/Mac/FreeBSD）の差分を吸収してプロセス優先度を設定するユーティリティ（set_process_priority）を実装。CPU affinity を最初 N コアに固定する set_cpu_affinity も実装（アクセス拒否等は警告でスキップ）。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを実装。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数等を集計し、閾値判定（PASS/FAIL）を行います。P95 計算、SQLite ファイル存在チェック、OperationalError のフォールバックを実装。

Changed
- n/a（初回リリース）

Fixed
- n/a（初回リリース）

Deprecated
- n/a（初回リリース）

Removed
- n/a（初回リリース）

Security
- n/a（初回リリース）

注意 / Migration Notes
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。監視データを分離したい場合は sqlite_path を明示的に指定してください。
- Paper Trading（KABUSYS_ENV=paper_trading）は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）を使用して本番 DB とデータ分離しています。Paper 環境で実行する際は環境変数の設定を確認してください。
- .env 自動ロードはデフォルトで有効です。テスト等でご自身で環境を管理したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。
- Settings のいくつかのプロパティは入力値検証を行います（例: KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL）。無効な値を設定すると ValueError が発生しますので、環境変数の値を確認してください。
- ai.news_nlp は OpenAI API キー（OPENAI_API_KEY）を必要とします。未設定の場合、score_news は ValueError を送出します。

既知の制限 / TODO
- ai.news_nlp の完全実装ではエラー処理や DB 書き込み周りでさらに細かなロバストネス確認が必要（コード断片の状態により未完部分あり）。
- portfolio.position_sizing: 現在 lot_size は全銘柄共通の取り扱い。将来的に銘柄別 lot_map に拡張予定（コメントあり）。
- apply_sector_cap のエクスポージャー算出で price が欠損（0.0）の場合は過少見積りになる旨の注記あり。フォールバック価格（前日終値等）の導入を検討。

開発者向けメモ
- DuckDB 接続を受けてクエリを投げる処理が多数あるため、prices_daily / raw_financials 等のスキーマ整備が前提です。
- ログレベルは Settings.log_level によって制御されます。デフォルトは INFO。

以上。今後の変更は Unreleased セクションに追記し、リリースごとにバージョンヘッダを追加してください。
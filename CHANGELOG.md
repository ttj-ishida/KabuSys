CHANGELOG
=========

すべての注目すべき変更をこのファイルに記載します。
このプロジェクトでは「Keep a Changelog」仕様に従っています。

[0.1.0] - 2026-04-17
-------------------

Added
- 初期リリース：KabuSys のコア機能群を導入。
  - 実行系
    - run_execution.py: ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
      - エンジンは別スレッドで実行され、 data/stop_requested.flag によるグレースフル停止に対応。
      - 実行 PID を data/execution.pid に書き込む想定（設定により変更可能）。
  - 監視系
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を参照して監視データを記録。
      - data/stop_requested.flag による停止検知、KeyboardInterrupt のハンドリング、DB 接続クローズ処理を実装。
  - 設定管理
    - config.py: 環境変数／.env ファイル読み込みユーティリティと Settings クラスを実装。
      - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づき .env/.env.local を自動ロード（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
      - .env パーサは export 形式、クォート、インラインコメント等に対応。
      - 各種設定プロパティ（DB パス、Paper Trading 設定、監視しきい値、ログレベル、環境判定 等）を提供。
      - 入力値のバリデーション（例: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE）を行い、不正な値は例外を送出。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py: シグナル選別と重み計算（等金額・スコア加重）。
    - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap スケールダウン、cost_buffer による保守的見積もり。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）。
    - モジュール __init__ により上記関数を公開。
  - 監視／ユーティリティ
    - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度設定と CPU affinity 固定機能を提供（psutil を利用）。Windows / POSIX を考慮し、権限不足等は警告で安全にスキップ。
  - リサーチ
    - research/factor_research.py: ファクター計算（Momentum, Volatility, Value）を DuckDB を用いて実装。prices_daily / raw_financials テーブルを参照。
    - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）・ランク関数・ファクター統計サマリ（factor_summary）を実装。外部ライブラリに依存せず純粋 Python + DuckDB の方針。
    - research/__init__.py で主要関数を公開。
  - AI ニュース NLP
    - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込む処理の設計と多くの実装。
      - スコアは -1.0〜1.0 にクリップ。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST = UTC の前日 06:00 ～ 23:30）を厳密に計算する calc_news_window を実装し、ルックアヘッドバイアス対策として datetime.today()/date.today() を参照しない設計。
      - バッチ（最大 20 銘柄）で API に送信、429/ネットワーク/5xx/タイムアウトに対して指数バックオフでリトライ。
      - レスポンスの厳密なバリデーションと部分更新戦略（成功したコードのみ置換）を想定。
      - API キー未設定時は ValueError を送出。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成 CLI スクリプト。
      - 稼働率・注文成功率・送信率・レイテンシ（P95）等の指標を SQLite（paper_trading.db デフォルト）から集計して標準出力にレポートを出力。
      - 合格基準（しきい値）を定義（稼働率 99% など）、Fail/Pass の判定を出力。
      - 日付フィルタ（--from / --to）、--db オプション対応。
  - ドキュメント／コメント
    - 各モジュールに設計意図、注意点、TODO 等の詳細な docstring コメントを付与。

Fixed / Hardened behaviors
- 設定や入力の堅牢化
  - MONITOR_POLL_INTERVAL の不正値（整数変換失敗・0 以下）を検出して警告ログを出力しデフォルトにフォールバック。
  - .env パーサはクォート内のエスケープやインラインコメントの扱いを慎重に実装。
  - 各 Settings プロパティで不正値は明示的に例外を投げることで早期失敗を促進（fail-fast）。
- DB 初期化
  - init_monitoring_db 呼び出しにより監視用テーブルが存在することを保証（冪等性）。

Security
- ニュース NLP の設計でルックアヘッドバイアスを回避するため、処理は target_date ベースで明示的にウィンドウを計算し、内部で現在時刻を参照しない設計を採用。
- OpenAI API キーの取り扱いは引数優先 → 環境変数 OPENAI_API_KEY の順。未設定時は明示的にエラー。

Notes / 備考
- 依存:
  - python 標準ライブラリ（sqlite3, threading, logging, datetime 等）
  - duckdb
  - psutil
  - openai（ai/news_nlp 実行時）
- デフォルトの DB パス:
  - monitoring: data/monitoring.db
  - duckdb: data/kabusys.duckdb
  - paper_trading: data/paper_trading.db
- 停止フラグ / PID:
  - 複数スクリプトで data/stop_requested.flag を用いた停止制御を採用。
  - 実行系は data/execution.pid を PID ファイルとして扱う想定（設定により変更可）。
- 既知の TODO / 改善点:
  - position_sizing.calc_position_sizes: price が欠損（0.0）の場合のフォールバック価格戦略は TODO コメントとして存在。
  - 将来的に lot_size を銘柄別に管理する拡張（stocks マスタへの lot_size 保持）を想定。
  - ai/news_nlp は設計・多くの実装を含むが、外部 API の挙動に合わせた詳細なエラー復旧や実運用向けのレート制御の微調整が必要。
  - research モジュールは DuckDB のテーブル構成（prices_daily, raw_financials 等）に依存するため、データ品質に起因する NULL 考慮やフェールセーフを要確認。

Breaking Changes
- なし（初期公開）。

ライセンスや貢献方法などの追記は別途 README 等に記載してください。
Keep a Changelog
================

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています（日本語）。

バージョン表記
-------------
- 当リポジトリの初回リリースは 0.1.0 として記載しています（コードベースから推測してまとめています）。
- 日付はコード提出時点の日付を使用しています。

[Unreleased]
------------
- （今後の変更履歴をここに記載してください）

[0.1.0] - 2026-04-13
-------------------

Added
- 基本パッケージ構成を追加
  - kabusys パッケージの初期バージョンを導入（__version__ = "0.1.0"）。
  - サブパッケージ: portfolio, research, ai, execution, monitoring, tools, utils 等を含む。

- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite DB を使用し Mock ブローカークライアントを利用する旨をサポート（本番 DB と分離）。
    - 実行前にプロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
    - ExecutionEngine の組み立てに BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler を使用する。
    - RiskManager のデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を定義。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視処理は KABUSYS_ENV に依らず本番 sqlite_path を使用する（監視は本番 DB の状態を監視する想定）。
    - 例外発生時はログに例外を出力して次ポーリングに継続するフェイルセーフ設計。
    - KeyboardInterrupt での終了処理と DB のクローズを保証。

- 設定管理
  - config.py を導入し環境変数と .env ファイルの自動ロード機能を実装。
    - プロジェクトルート（.git または pyproject.toml を基準）を自動検出し、.env/.env.local を読み込む（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env の細かいパース実装（export プレフィックス対応、クォート処理、インラインコメント処理、保護キー(既存 OS 環境変数)の扱い）を追加。
    - 必須 env の取得（_require）や設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を提供。
    - デフォルトパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）とモニタ閾値（CPU/MEM/DISK）プロパティを提供。

- 監視関連
  - monitoring_db.init_monitoring_db を利用して監視用テーブルの初期化を行う（冪等化）。
  - SystemMonitor を実行するポーリングループを提供（run_monitoring）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレークに signal_rank を使う候補選定。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（スコア全0 の場合はフォールバックで等金額配分し警告出力）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別の既存エクスポージャーを計算し、上限超過セクターの新規候補を除外するロジックを実装。"unknown" セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づいた発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（投下合計が利用可能現金を超える場合のスケールダウン）、cost_buffer（手数料・スリッページ見積り）をサポート。
    - リスクベース算出（risk_pct, stop_loss_pct）と安全弁（max_position_pct, max_utilization）を実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value: DuckDB 上の prices_daily/raw_financials を使ったファクター算出を SQL + Python で実装（MA200, ATR20, 各種モメンタム期間等）。
    - 大域定数で窓長を定義し、必要データ不足時は None を返す設計。
  - research/feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターンを計算（horizons 検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）では None。
    - factor_summary, rank: 基本統計量とランク付けユーティリティを提供。
  - research/__init__.py で zscore_normalize を含めた公開インターフェースを定義。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を銘柄別に集約し OpenAI (gpt-4o-mini) を用いてセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む機能を実装。
    - ニュース時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正確に計算するユーティリティ calc_news_window。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、記事数/文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）、スコアの ±1.0 クリップを実装。
    - API 呼び出しでの 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装（上限 _MAX_RETRIES）。
    - API キー未指定時は ValueError を送出。
    - レスポンス検証と部分更新（失敗時でも他銘柄の既存スコアを保護するための部分削除→挿入戦略）を明記。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX (Linux/Darwin/FreeBSD) を吸収しプロセス優先度を設定。アクセス権限不足等を捕捉して警告出力し失敗をフェイルセーフでスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数へ CPU affinity を設定（検証・例外処理あり）。
    - クロスプラットフォームの安全な実装により起動スクリプトで早期に呼び出す設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。SQLite（PAPER_TRADING_SQLITE_PATH）を読み取り、稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタオプション（--from/--to）、DB 存在チェック、SQL エラー時のフォールバックを実装。

Changed / Design notes
- 多くのモジュールは「副作用なし（純粋関数）」「DB 参照箇所を限定」する設計方針を採用。
  - portfolio モジュールはメモリ内計算のみ（DB 未参照）。
  - research モジュールは DuckDB の prices_daily / raw_financials のみ参照し外部 API に依存しない。
  - ai/news_nlp は外部 API を用いるが、呼び出し周りはフェイルセーフ（リトライ・部分更新）で堅牢化。
- 環境変数の自動ロードはプロジェクトルートを起点に行うため、CWD に依存しない（パッケージ配布後も動作）。
- 監視処理は意図的に本番 sqlite_path を参照（監視は本番対象の観察が目的のため）。
- run_execution では paper_trading 環境時に DB を完全分離して操作（テスト/検証と本番の分離）。

Fixed / Robustness improvements
- env ファイル読み込み失敗時に警告を出す（warnings.warn）。
- .env の詳細なパース（クォート・エスケープ・コメント処理）により多様な .env フォーマットに対応。
- プロセス優先度や CPU affinity 設定で権限不足や未対応プラットフォームの場合にログ警告で安全にスキップ。
- ポーリングループでの例外を捕捉してログ出力後に継続することで監視の耐障害性を確保。
- 各種 DB 接続は finally ブロックで確実にクローズ。

Security
- .env ロード時に OS 環境変数（既存のキー）を保護する仕組みを導入（override、protected 引数）。
- OpenAI API キーの扱いは明示的に指定または環境変数を参照し、未設定時は明示的エラーを出す。

Deprecated
- なし（初回リリース）。

Removed
- なし（初回リリース）。

Notes / 注意事項（推測に基づく）
- 設定値やしきい値（例: risk / stop loss / thresholds）はコード内で既定値が定められており、運用環境では環境変数や構成で上書きすることが想定される。
- 一部 TODO（例: price 欠損時のフォールバック、lot_size の銘柄別対応）がコード中に記載されており、将来的な改善ポイントとして意図されている。
- DuckDB を利用した大規模な履歴データ処理が前提のため、prices_daily / raw_financials 等のテーブル整備が前提。

作成者注
- 上記 CHANGELOG は提供いただいたソースコードから動作や設計意図を推測して作成しています。実際のリリース履歴やバージョン管理履歴（git のコミットメッセージ等）がある場合は、それに基づいて差し替えることを推奨します。必要であれば、コミット履歴風により細かく分割した CHANGELOG への変換も対応します。
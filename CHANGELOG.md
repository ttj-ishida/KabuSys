# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。追跡可能な変更のみを記載し、内部実装の細かな変更は省略しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-12

Added
- 基本アプリケーション骨格を追加
  - パッケージバージョン: `kabusys` __version__ = `0.1.0`
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI 実装。
    - 環境に応じて paper_trading 用 DB を分離して使用（KABUSYS_ENV=paper_trading の場合は専用 SQLite を利用）。
    - BrokerClientFactory によりブローカークライアントを生成（モック/実ブローカーの切替想定）。
    - OrderRepository/OrderManager/RiskManager/Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - 起動時にプロセス優先度を "high" に設定。
    - DuckDB / SQLite 両方の接続管理を含む。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視機能は環境に関わらず本番 sqlite_path を使用（監視用 DB の利用方針）。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - .env / .env.local の自動ロード（プロジェクトルート検出ロジック: .git または pyproject.toml を基準）。
    - 行パーサー `_parse_env_line` により export 構文、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮。
    - Settings クラスを提供し、環境変数やデフォルト値を型変換してアクセス可能にした（例: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, 各種閾値やフラグ）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - 入力検証あり（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。
- 監視関連
  - monitoring_db 初期化呼び出し（init_monitoring_db を使用して冪等にテーブルを保証）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（全銘柄スコア 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限による候補除外ロジック（既存保有時価を考慮、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - portfolio/position_sizing.py
    - calc_position_sizes: weight / risk_based 等の方式に基づく発注株数計算。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap、cost_buffer による保守的見積り、スケーリングと端数処理（remainder による追加配分）を実装。
- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収してプロセス優先度（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値）を設定。
    - CPU affinity を最初の N コアにピン留めする set_cpu_affinity を提供。
    - 権限不足や未サポート OS の場合は警告して安全にフォールバック。
- リサーチ / 特徴量
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value: DuckDB 上の prices_daily / raw_financials を参照し、各種ファクター（モメンタム、ATR 等）を計算。
    - 各関数は日数窓やデータ不足時の None ハンドリングを考慮。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - factor_summary / rank: 基本統計量とランク変換（タイの平均ランク処理を含む）。
  - research/__init__.py にエクスポートを追加（zscore_normalize を含む）。
- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を銘柄毎に集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を取得し ai_scores に書き込む処理を実装。
    - バッチ処理（最大 _BATCH_SIZE=20）、記事文字数上限、記事数上限の実装、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスのバリデーション、スコアの ±1.0 クリップを実装。
    - 書き込みは部分失敗に耐える方式（対象コード群のみを置換）。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を提供する calc_news_window。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ指標（平均/最大/P95）を集計して判定（PASS/FAIL）を表示。
    - 日付フィルタ、DB パス指定オプションをサポート。
    - P95 計算や欠損値の N/A 表示を実装。
- データベース
  - DuckDB と SQLite の併用を前提にした接続・クエリ実装を各所に追加（research や ai モジュールなど）。

Changed
- 新規リリースのための初期実装群。既存の外部インタフェースやプロトコルの変更履歴はまだなし。

Fixed
- 起動設定・環境変数の扱いに関する堅牢化
  - MONITOR_POLL_INTERVAL の不正値は警告してデフォルトにフォールバック。
  - PAPER_FILL_MODE のバリデーション追加（不正値で ValueError）。
  - LOG_LEVEL / KABUSYS_ENV のバリデーション（不正な値で ValueError）。

Security
- 環境変数自動ロード時に OS 環境を protected として扱う（.env.local の override でも OS 環境変数を上書きしない）。

Notes / Known limitations / TODO
- portfolio/risk_adjustment.apply_sector_cap: price が 0.0 の場合にエクスポージャーが過少見積りされる旨の TODO が残る（将来的に前日終値等でフォールバックする方針）。
- position_sizing.calc_position_sizes: 将来的な拡張として銘柄別の lot_size (単元株) を受け取る設計にすべきという TODO がある（現状は全銘柄共通 lot_size）。
- news_nlp の処理は OpenAI API 利用のため API キー管理・レート制限回避が運用上の注意点。api_key 未指定かつ環境変数未設定の場合は ValueError を送出。
- CPU affinity / process priority の設定はプラットフォーム依存であり、権限不足時には警告してスキップする（安全設計）。
- テスト・CI・ドキュメントは別途整備が必要（このリリースは実装主体の初期版）。

デフォルト値（重要）
- MONITOR_POLL_INTERVAL: 60 秒（run_monitoring）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- PAPER_FILL_MODE: "instant"

参照
- 各モジュール内の Docstring とコードコメントをソース可読ドキュメントとして参照してください。

--- 

（注）本 CHANGELOG は提供された現在のコードベースからの推測に基づいた初期リリース記録です。実際のコミット履歴や変更差分がある場合は、該当のコミットメッセージ／差分に基づき更新してください。
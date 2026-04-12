# Changelog

すべての変更は Keep a Changelog の形式に従い、重要な変更はセマンティックバージョニングに基づいて記載しています。

リンクや比較は未設定です。

## [Unreleased]

## [0.1.0] - 2026-04-12

Added
- プロジェクト初回リリース。
- 基本パッケージ構成とエントリポイントを追加。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。起動時にプロセス優先度を設定し、SQLite / DuckDB に接続してセッションを実行する。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
- 設定管理モジュールを追加（kabusys.config）。
  - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env / .env.local の読み込み順序と OS 環境変数保護機構を実装。
  - Settings クラスで多数の設定値をプロパティとして提供（DB パス、API トークン、監視閾値、PID/kill flag パス、環境種別判定など）。
  - 必須環境変数未設定時に明確なエラーメッセージを送出する _require() を実装。
- 監視系
  - monitoring_db 初期化フック（init_monitoring_db の呼び出し）を実行開始時に追加し、監視テーブルの存在を保証。
  - SystemMonitor を使った定期チェックループを実装（例外はログ出力して次サイクルへ継続）。
- Execution 系
  - BrokerClientFactory によるブローカークライアント作成を導入。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用して本番 DB と完全分離。
  - OrderRepository / OrderManager / Reconciler / RiskManager を組み合わせて ExecutionEngine を起動する流れを実装。
  - RiskManager の初期設定（max_position_pct / max_utilization / rate_limit_per_sec / circuit_breaker 等）を具体値で提供し、初期ポートフォリオ値を broker.get_available_cash() から取得。
- Portfolio 構築モジュール
  - portfolio_builder: シグナル選別（select_candidates）、等配分・スコア配分（calc_equal_weights / calc_score_weights）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
  - position_sizing: 株数計算（calc_position_sizes）を実装。リスクベース、等配分/スコア配分方式をサポート。単元株（lot_size）丸め、aggregate cap によるスケーリングや残差配分ロジックを実装。
- Research / ファクター計算
  - research.factor_research: モメンタム / ボラティリティ / バリュー各ファクターを DuckDB SQL ベースで実装（prices_daily/raw_financials を参照）。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、Spearman ランク相関での IC 計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク付けユーティリティ（rank）を追加。
  - 標準ライブラリのみで動作するよう設計（pandas 等に依存しない）。
- News NLP（AI）モジュール
  - ai.news_nlp: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄毎のセンチメントスコアを ai_scores に書き込む処理を実装。
  - バッチサイズ、最大記事文字数・記事数制限、JSON Mode でのレスポンス検証、スコアクリップ（±1.0）、429/タイムアウト/5xx の指数バックオフリトライなどの堅牢性設計を導入。
  - API キー未設定時は明確な ValueError を送出。
- CLI ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。SQLite の trade_logs / system_status / risk_logs などから集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を出力する。コマンド例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- ユーティリティ
  - utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。アクセス権限や未対応プラットフォーム時は警告を出して安全にスキップ。

Changed
- 監視ループの動作と構成:
  - MONITOR_POLL_INTERVAL 環境変数を導入。無効な値（0 以下や整数以外）の場合はデフォルト 60 秒にフォールバックし、警告ログを出力するように変更。
  - 監視（monitoring）は KABUSYS_ENV に依存せず常に本番 sqlite_path を使用する方針を明記（run_monitoring.py）。
- .env 自動読み込みポリシー:
  - OS 環境変数を保護するため .env/.env.local 読み込み時に既存の OS 環境変数を上書きしない（.env.local は override=True だが protected によって OS 環境変数は保護）。
- position_sizing の挙動:
  - cost_buffer を計算に組み込み、手数料・スリッページ見積りを保守的に加味するように変更。
  - aggregate cap 超過時のスケールダウン処理と残差の lot_size 単位での追加配分ロジックを実装。
- risk_adjustment の挙動:
  - apply_sector_cap は sector_map に存在しないコードは "unknown" 扱いとしてセクター上限の適用対象から除外する仕様。
  - calc_regime_multiplier は未知レジームを検出したら警告ログを出して 1.0 でフォールバックする挙動を追加。

Fixed
- 環境変数パースの堅牢性向上:
  - .env の行パースで export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いを正しく処理するよう改善。
  - PAPER_FILL_MODE のバリデーションを実装し、不正値で ValueError を送出するようにした（有効値: instant|partial|never|reject）。
- プロセス優先度 / CPU affinity のエラー処理:
  - psutil による優先度設定・cpu_affinity の際に AccessDenied / NotImplementedError 等が発生した場合、警告ログに詳細を出してスキップするように対応。
- レポートツールの堅牢性:
  - paper_verification_report は該当テーブルが存在しない場合に sqlite3.OperationalError を捕捉してデフォルト値で継続するように修正（DB が存在しない場合は明示的にエラー表示）。

Security
- API キー / トークン取り扱い:
  - 必須の API トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が未設定の場合に明確なエラーを出すことで起動時ミスを早期に検出。
  - OpenAI API を使用するニューススコアリングは明示的に API キーを要求。未設定時に ValueError を送出。

Documentation / Notes
- パスとデフォルト:
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）
  - 本番 SQLite (monitoring): data/monitoring.db（環境変数 SQLITE_PATH で上書き可）
  - Paper Trading SQLite: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH）
  - PID ファイル / kill flag のデフォルトパスを Settings で提供（PID_FILE_PATH, KILL_FLAG_PATH）
- 実行順序上の注意:
  - run_* スクリプトは起動直後に set_process_priority("high") を呼び出すため、環境によっては権限不足で警告が出る可能性があります（影響はログのみでプロセスは継続）。
- 依存ライブラリ:
  - duckdb, psutil, openai（OpenAI Python クライアント）を使用。

今後の予定（例）
- news_nlp の部分的な未完部分（例: レスポンス書き込み完了部など）の完成。
- stocks マスタに単元株情報を持たせ、銘柄別 lot_size サポートに拡張。
- ポートフォリオ構築およびリスク管理ロジックのさらに厳密なユニットテスト追加。

以上。
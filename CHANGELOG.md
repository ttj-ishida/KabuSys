CHANGELOG
=========

すべての重要な変更点を記録します。本ドキュメントは「Keep a Changelog」形式に準拠しています。

フォーマット:
- Unreleased: 現行作業中の変更（存在する場合）
- バージョン: リリース日（YYYY-MM-DD）
- セクション: Added / Changed / Fixed / Deprecated / Removed / Security

Unreleased
----------
（現時点では未リリースの変更はありません。）

[0.1.0] - 2026-04-12
--------------------

Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"）。
- 設定管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local 自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - export KEY=... やクォート・コメントのある .env 行を適切にパース。
  - 多数の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
    - PAPER_FILL_MODE（instant|partial|never|reject、デフォルト: instant）
    - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
    - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
  - Settings クラスおよびグローバル settings オブジェクトを提供。
- 実行用スクリプトを追加:
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの抽象化、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせて ExecutionEngine を起動。
    - duckdb 接続を受け取りデータ参照を可能にする設計。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB（monitoring）は環境にかかわらず本番 sqlite_path を使用する設計。
- モニタリング DB 初期化ユーティリティ（init_monitoring_db）への呼び出し箇所を提供（実行・監視双方で冪等に初期化）。
- process_priority ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - Windows と POSIX (Linux, Darwin, FreeBSD) を吸収し、プロセス優先度（high/normal/low）および CPU affinity の設定を提供。
  - 権限不足や未サポート環境では警告を出してスキップするフェイルセーフを実装。
- Portfolio 構築モジュール（src/kabusys/portfolio/）を追加:
  - portfolio_builder.py: 候補選定（select_candidates）、等金額／スコア加重の重み計算（calc_equal_weights / calc_score_weights）。
  - risk_adjustment.py: セクター上限適用（apply_sector_cap）、レジーム乗数計算（calc_regime_multiplier）。
  - position_sizing.py: 各銘柄の発注株数計算（calc_position_sizes）。risk_based / equal / score の方式、単元丸め、aggregate cap スケーリングを実装。
  - __init__ から公開関数をエクスポート。
- リサーチ・ファクターモジュール（src/kabusys/research/）を追加:
  - factor_research.py: モメンタム・ボラティリティ・バリュー系ファクターの DuckDB ベース計算（calc_momentum, calc_volatility, calc_value）。
  - feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリ（factor_summary）、ランク関数（rank）。
  - いずれも DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する純粋関数群。
  - 外部依存を抑え、標準ライブラリのみで統計処理を実装。
- AI ニュース NLP モジュールを追加（src/kabusys/ai/news_nlp.py）。
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores テーブルへ書き込み。
  - バッチ処理（最大 20 銘柄/呼び出し）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、応答バリデーション、スコアクリッピングを実装。
  - 時間ウィンドウ計算（JSTを基準にUTCへ変換）を提供（calc_news_window）。
  - API キー未設定時に明示的なエラーを出す設計。
- CLI ツールを追加（src/kabusys/tools/）:
  - paper_verification_report.py:
    - Paper Trading の検証レポートを生成。PAPER_TRADING_SQLITE_PATH（または --db）を指定して実行可能。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）等を算出して表示。
    - 合否基準（閾値）と判定メッセージを組み込み（稼働率 99%、fill_rate 90% 等）。
- ユーティリティ・パッケージの骨組みを追加（src/kabusys/utils/__init__.py, src/kabusys/tools/__init__.py）。

Changed
- 各モジュールはデータ欠損や例外時に None を返す/除外するなど、実運用を考慮した堅牢化がなされている（例: ファクター計算・レイテンシ計算・paper_verification_report の SQL 呼び出し例外ハンドリング等）。
- .env 読み込みロジック:
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数を保護する protected 機構を導入（.env.local が OS 環境を上書きしない等の制御）。
- run_monitoring/run_execution の起動フロー:
  - 起動時に process priority を high に設定する処理を先頭で呼び出すように統一。
  - duckdb と sqlite のクローズを finally で確実に行うように変更。

Fixed
- .env パーサーの複雑なケース（クォート内のバックスラッシュエスケープ、インラインコメントの扱い、export プレフィックス）への対応を追加し、誤ったパースによる環境設定漏れを防止。
- paper_verification_report の統計取得時にテーブルが存在しない場合の例外（sqlite3.OperationalError）を捕捉し、レポート生成を継続するようにした。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーや他の機密情報は Settings で環境変数経由で管理する設計とし、ログ等でキーそのものを出力しない方針が採られている（モジュールの docstring / 実装に基づく）。

マイグレーション / 運用メモ
- 環境変数の一覧（主なもの）
  - KABUSYS_ENV: development | paper_trading | live（実行モード切替）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60。1 未満は無視してデフォルトを使用）
  - PAPER_FILL_MODE: paper_trading のモック約定動作（instant|partial|never|reject）
  - OPENAI_API_KEY: news_nlp 用 API キー（必須でないが score_news を使う場合に必要）
  - その他: PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT 等
- run_execution.py を paper_trading モードで実行すると、paper_trading 専用 DB（data/paper_trading.db 等）を使用して本番データと完全に分離されます。
- run_monitoring.py は監視データのために常に本番 sqlite_path を使用する点に注意してください（環境に依らず本番監視を想定）。
- OpenAI を用いる機能は API の呼び出し失敗時に個別チャンクをスキップして継続する設計だが、API キー未設定時は例外を送出します。

既知の制限 / TODO（ドキュメントから推測）
- position_sizing は単元株数を全銘柄共通の lot_size（デフォルト 100）で処理。将来的に銘柄別 lot_size を導入予定。
- apply_sector_cap は price が欠損（=0.0）の場合にエクスポージャーを過少見積もる可能性があり、フォールバック価格戦略の検討が必要（コメント参照）。
- news_nlp の score_news は DuckDB 内の raw_news/news_symbols 構造に依存するため、スキーマ変更には注意。
- 一部の関数は入力データ不足時に None を返す（NULL ロジック）。呼び出し側での None ハンドリングが必要。

---

本 CHANGELOG は、コードベース（src/ 以下のファイル群）の現状を元に機能追加・変更点を推測してまとめたものです。必要であれば、個別ファイル単位の差分やリリースノート用のより詳細な説明（例: SQL スキーマ、API 仕様、起動コマンド例など）を追加します。どのレベルの追記が必要か教えてください。
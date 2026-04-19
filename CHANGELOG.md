# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

履歴
- 未発表の変更はここに記載します。

[0.1.0] - 2026-04-19
========================================
Added
- 初期リリースを追加。
- 起動スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、ブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のデーモンスレッド実行と停止フラグ処理、paper_trading 環境時の専用 SQLite DB（data/paper_trading.db）使用を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検知、sqlite3 / DuckDB 接続および監視 DB 初期化処理を実装。
- 設定・ヘルパー:
  - config.py: Settings クラスを実装。.env 自動ロード（.env → .env.local、OS環境変数優先）、プロジェクトルート自動検出、各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH 等）取得ロジックを提供。paper_trading/production のパス分離や PAPER_FILL_MODE の検証を含む。
  - config_setup.py: 対話式 .env ウィザードを追加。既存 .env 読込・編集、保存機能。
  - validate_config.py: 簡易設定検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、YAML 設定ファイルの存在・パースチェック（PyYAML が利用可能な場合）、本番環境向けの追加ガード、--strict オプションをサポート。
- ロギング・プロセス管理:
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。コンソール出力（stdout）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成や既存ハンドラのリセット処理、環境変数によるログレベル/ディレクトリ指定をサポート。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。Windows/Linux/macOS に対応し、nice 値や Windows の優先度クラスを利用。CPU affinity を固定する set_cpu_affinity() も提供。
- ポートフォリオ構築（純粋関数群）:
  - portfolio/portfolio_builder.py: 候補選定（score 降順、signal_rank によるタイブレーク）、等分配・スコア加重配分アルゴリズムを実装。全てメモリ内計算の純粋関数。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。unknown セクターの扱いやフォールバックロジックを明示。
  - portfolio/position_sizing.py: position sizing（risk_based / equal / score）アルゴリズムを実装。単元株（lot_size）丸め、1銘柄上限・アグリゲートキャップのスケーリング、cost_buffer による保守的見積り、残余キャッシュを用いた端数処理等をサポート。
  - portfolio/__init__.py にて上記関数群をエクスポート。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を SQLite のテーブル（system_status / trade_logs / risk_logs 等）から集計し、閾値による PASS/FAIL 判定を出力。P95 計算ユーティリティを含む。コマンドライン引数で期間指定（--from, --to）と DB パス指定（--db）をサポート。
- research:
  - research/factor_research.py: ファクター計算モジュール（Momentum, Value, Volatility, Liquidity に関する設計と一部実装）を追加。DuckDB 接続を受け prices_daily / raw_financials を参照する設計。モメンタム計算関数の骨組みを実装（注: 一部実装が続く想定）。
- パッケージ初期化:
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- 監視・実行の挙動:
  - 監視 (run_monitoring) は KABUSYS_ENV に依存せず「本番」用 sqlite_path を使用する旨を明示（monitoring 用テーブルの一貫性確保）。
  - 実行 (run_execution) は paper_trading 環境時に専用 DB を使用して本番 DB と分離する設計（settings.is_paper に基づく）。
- .env 読み込み:
  - .env のパース処理を強化（export プレフィックス、クォート付き値のエスケープ処理、インラインコメントの扱いなど）。読み込み優先度と保護キー（OS 環境変数）の扱いを明確化。
- ログ出力先:
  - logging_setup は stdout を使用するように変更（stderr ではなく）。ログファイルは日次ローテーションで 30 日分保持。
- プロセス優先度:
  - 起動スクリプトは初期化直後に set_process_priority("high") を呼び出し、重要プロセスとして優先度を上げる。

Fixed
- エラーハンドリング/堅牢化:
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げた場合に loop を破壊せず例外情報をログ出力して次のポーリングを継続するように調整。
  - run_execution: 停止フラグ存在時はエンジンを起動せず安全に終了するガードを追加。
  - logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップして console のみで継続するように改善。
  - process_priority: アクセス拒否等の例外を捕捉して警告ログを出し、起動を継続するように改善。

Security
- 機密情報の扱い:
  - config_setup.py と .env 処理において、シークレット値はウィザード画面でマスク表示されるなど、誤ってログや画面に平文で出さない配慮を追加。
  - README や注釈で .env を絶対に Git にコミットしない旨を明記。

Notes / Known limitations
- research/factor_research.py は設計方針と一部実装（モメンタム計算の骨組み）を含むが、ファイル末尾に実装の続きが想定される断片（途中終了）が見られます。完全実装は今後のリリースで追加予定。
- 一部 TODO コメント（例: position_sizing における価格フォールバックロジック、lot_size の銘柄別対応など）が残っています。
- Paper Trading の検証閾値（稼働率・成功率等）は現時点の基準値が固定で定義されています。運用に合わせて調整してください。

以上。
# Changelog

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全ての変更はセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-24

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - src/kabusys/__init__.py にバージョン情報を追加。
- 起動スクリプト:
  - run_monitoring: システム監視ポーリングループの起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルで制御。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する設計。
    - SQLite / DuckDB に接続し、監視データベース初期化（init_monitoring_db）を行う。
    - 監視処理は SystemMonitor.check_once() を呼び出すループ実行。例外は捕捉して次のポーリングへ継続。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper trading DB を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを作成（MockBrokerClient を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知時に安全にエンジンを停止する。
    - 実行時 PID を data/execution.pid に書き込む仕組みを想定（pid_file 引数で指定）。
- 設定管理:
  - Settings クラスを追加（src/kabusys/config.py）。
    - 環境変数から各種設定を取得するプロパティを提供（J-Quants/J-Quants token, kabu API, DB パスなど）。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値のチェック）。
    - paper_trading 用の paper_sqlite_path をサポート。
    - ユーティリティ settings オブジェクトをエクスポート。
  - .env 自動読み込み機能を実装:
    - プロジェクトルート（.git または pyproject.toml を基準）を検出し、.env/.env.local を自動ロード。
    - 既存 OS 環境変数は保護され、.env.local による上書きや .env の初期ロード順を処理。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト等で利用）。
  - .env パース機能の強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理など。
- 設定検証ツール:
  - validate_config CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML が利用可能な場合）パース検証。
    - --strict モードで警告を FAIL 扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START 設定など）を実装。
- .env 作成ウィザード:
  - config_setup CLI を追加（src/kabusys/config_setup.py）。
    - 対話式に .env を生成・更新するウィザードを提供。
    - シークレット項目をマスクして表示、Enter で既存値／デフォルト再利用、保存前の確認を実装。
    - .env の書式を規定（ファイルヘッダ、項目セクション）。
- ログ関連ユーティリティ:
  - setup_logging を追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ファイル書き込み失敗時はコンソール出力のみで継続。
- プロセス優先度ユーティリティ:
  - set_process_priority / set_cpu_affinity を追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差異を吸収して nice / priority を設定。権限不足時は警告を出してスキップ。
- ポートフォリオ構築関連:
  - portfolio モジュールを追加（kabusys.portfolio.*）:
    - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を実装（スコア降順、等比率・スコア重み）。
    - risk_adjustment: apply_sector_cap（セクター集中上限を適用）、calc_regime_multiplier（市場レジームに基づく乗数）を実装。
    - position_sizing: calc_position_sizes を実装（risk_based / equal / score の配分ロジック、lot_size 単位丸め、aggregate cap スケーリング、cost_buffer を考慮）。
- Paper Trading 検証ツール:
  - tools/paper_verification_report を追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite DB からシステム安定性（稼働率）、注文成功率、送信率、リスク却下数、レイテンシ（P95 等）を抽出してテキストレポート出力。
    - デフォルト DB パスは data/paper_trading.db。--from/--to/--db オプションをサポート。
    - 判定基準（スレッショルド）を定義し PASS/FAIL 判定を出力。
- 研究用ファクター計算（初期実装）:
  - research/factor_research.py を追加（Momentum / Value / Volatility / Liquidity を想定、DuckDB 接続を受け取る設計）。（ファイルは途中まで実装）
- DB 初期化ユーティリティ:
  - init_monitoring_db の呼び出しを run_monitoring/run_execution 内で行い、監視テーブルが存在することを保証（冪等処理）。

### Changed
- ログの標準出力先を stderr ではなく stdout に設定（cron 等でリダイレクトしやすくするため）。
- logging の既存ハンドラは再設定時に一旦 flush/close して削除するように変更（多重ハンドラ設定を防止）。
- .env の上書きルール:
  - .env.local は OS 環境変数を保護しつつ優先的に上書きされる（override=True だが protected により OS 環境変数は保持）。

### Fixed
- run_monitoring の MONITOR_POLL_INTERVAL が 0 以下や不正文字列の場合に time.sleep に渡して ValueError となる問題に対処:
  - 0 以下や不正な値は警告ログを出力してデフォルト（60秒）にフォールバックする実装を追加。

### Security
- .env を生成する際に明示的に「.env は絶対に Git にコミットしないこと」をファイルヘッダに記載（config_setup の出力ファイル）。

### Notes / Known limitations
- research/factor_research.py は設計ドキュメント（StrategyModel.md / PortfolioConstruction.md 等）に基づく初期実装であり、一部未完成（ファイル末尾が途中で切れている）。
- position_sizing の price 欠損時の挙動は TODO コメントあり（価格欠損によるエクスポージャー過少見積りの問題）。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合は警告ログを出力してスキップする設計。
- config/*.yaml の自動生成は scripts/generate_config.py を想定（未提供の環境向けに validate_config は警告を出す）。

---

このリリースは基盤となる CLI、設定周り、監視・実行エントリポイント、ポートフォリオ構築ロジック、検証ツールを一通り揃えた初期版です。今後は research の完成、テスト追加、ドキュメント整備、各モジュールの拡張（lot size 毎銘柄対応、フォールバック価格、より厳密なリスク管理等）を予定しています。
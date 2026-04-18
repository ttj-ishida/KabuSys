# Changelog

すべての変更は Keep a Changelog の形式に従います。  
日付は @release 時点の想定日（コードベースから推測）です。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース相当。以下の主要コンポーネントと機能を追加しました。

### Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を利用したデータ格納・分析基盤を組み込み（設定でパス指定可能）。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、本番 DB と完全に分離する挙動を実装（環境変数/Settings.paper_sqlite_path を参照）。
    - BrokerClientFactory により実行時にブローカークライアントを生成（モック実装を差し替え可能）。
    - ExecutionEngine を別スレッドで実行し、デーモン化されたセッション管理／停止フラグ（data/execution.pid, data/stop_requested.flag）に対応。
    - 各種依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てる起動フローを実装。
    - RiskManager に渡す RiskConfig のデフォルト設定（max_position_pct, max_utilization 等）を組み込み。初期ポートフォリオ値は broker.get_available_cash() から取得。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番の sqlite_path を使用する旨の設計（paper_trading モードでも別 DB ではなく監視は本番 DB に接続）。
    - stop フラグ（data/stop_requested.flag）検知で安全にループを終了。
    - check_once() 実行で例外が発生してもログ出力しループ継続。
- 設定・環境管理
  - config.py
    - .env 自動読み込みロジック（プロジェクトルート検出: .git または pyproject.toml を基準）を追加。
    - .env/.env.local の読み込み順序（OS 環境を保護する protected set）に対応。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化できる。
    - .env のパースは export プレフィックス、クォート値（エスケープ対応）、インラインコメントの扱い等に対応する堅牢な実装を追加。
    - Settings クラスを導入し、環境変数アクセスをラップ。複数のプロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, 各種しきい値、env/log_level 等）を提供。値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実施。
    - KILL_FLAG_CLEAR_ON_START フラグの bool 解釈を導入。
  - config_setup.py
    - .env を対話的に作成/更新するウィザードを追加。既存値読み込み、シークレットマスク、選択肢・デフォルト、保存確認をサポート。
    - 書き込み時に .env のテンプレートヘッダを付与し、Git へのコミット禁止コメントを明記。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性判定、DB パス存在チェック（親ディレクトリの警告）、config/*.yaml の存在と（PyYAML があれば）構文チェックを実施。
    - --strict オプションで警告を FAIL 扱いできる。
    - 本番（KABUSYS_ENV=live）時の追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険値など）を追加。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログディレクトリの解決（引数 > 環境変数 LOG_DIR > デフォルト logs/）と作成処理を実装。作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラのクリア処理を行い重複を防止。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）をクロスプラットフォームに設定するヘルパーを実装（psutil に依存）。
    - Linux/macOS 等 POSIX 系では nice 値を設定、Windows では HIGH_PRIORITY_CLASS 等を使用。アクセス権限が無い場合は警告を出力してスキップ。
    - set_cpu_affinity により最初の N コアにピン留めする機能も追加（権限不足時は警告を出力）。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークに signal_rank）を追加。
    - 等分配 calc_equal_weights とスコア正規化 calc_score_weights（全スコアが 0 の場合は等分配にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（max_sector_pct）を適用する関数を追加。既存ポジションのセクター別時価を算出し、上限超過セクターの新規候補を除外するロジックを実装（unknown セクターは除外対象にしない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じて投下資金乗数を返すユーティリティを追加。未知レジームは警告を出し 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: 多様な配分方式（risk_based / equal / score）に対応し、単元株（lot_size）丸め、per-position および aggregate cap、cost_buffer を考慮したスケーリングロジックを実装。
    - aggregate cap 超過時にはスケールダウンと端数ロジック（lot 単位での残差配分）を実装。
- リサーチ
  - research/factor_research.py（ファクター計算モジュール）
    - モメンタム、MA200乖離、ATR、出来高系等ファクター計算の骨組みと定数を追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。
    - 候補となる各種期間定数（1M/3M/6M, MA200, ATR20 等）とスキャン範囲の定義を実装。関数のシグネチャと目的ドキュメントを記載（部分実装あり）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み取り、稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL を判定する。
    - デフォルトしきい値（稼働率 99%、成功率 90%、送信率 95%、P95 latency 200 ms）を定義。
    - 空データやテーブル未存在時に堅牢に動作するフォールバックを実装（sqlite3.OperationalError を捕捉して N/A 扱い）。
- monitoring
  - monitoring.monitoring_db.init_monitoring_db を使用して監視用テーブルの存在を保証する処理を各起動スクリプトに組み込み（冪等性を重視）。

### Changed
- ログ出力の挙動
  - すべての起動スクリプトから setup_logging(app_name=...) を呼ぶ設計に統一し、ログファイル名を app_name ベースに分離（例: logs/execution.log, logs/monitoring.log）。
  - 標準エラーではなく標準出力（stdout）へ StreamHandler を設定（外部からリダイレクトしやすくするため）。
- 環境ファイル読み込みの挙動
  - .env/.env.local のロード順序を明確化（OS 環境 > .env.local > .env）し、既存 OS 環境変数を保護する実装に変更。
  - .env のパース機能を強化し、export プレフィックスやクォート内部のエスケープ、インラインコメントの取り扱いを改善。
- Execution / Monitoring の DB 接続ルール
  - run_execution: paper_trading モード時は paper_sqlite_path を使用するように変更（paper/trading DB と本番 DB を分離）。
  - run_monitoring: 監視は常に設定された sqlite_path（本番監視 DB）を使用（監視対象は本番設定に合わせる判断）。
- Process priority の適用タイミング
  - 起動直後に set_process_priority("high") を呼び出して、重要なデーモン処理の優先度を上げるように統一。

### Fixed
- .env パーサの脆弱なコメント処理を改善し、値内の '#' を誤検出しないように修正（クォート有り/無しの扱いを明確化）。
- logging_setup: ログディレクトリ作成失敗時にルートロガー未構成で警告を出す実装を追加し、ファイルハンドラ作成失敗時はコンソール出力のみで継続するように安定化。

### Notes / Implementation details
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数（秒）でループ間隔を制御。1 未満や不正値はデフォルト 60 秒にフォールバック。
- config.Settings により、PAPER_FILL_MODE の妥当性チェックが組み込まれ、有効値は {"instant","partial","never","reject"}。
- position_sizing と risk_adjustment の関数群は純粋関数として設計され、DB 参照なしでメモリ計算のみを行うため単体テストが容易。
- paper_verification_report は P95 を求める独自実装を含む（サンプル数に応じたインデックス計算）。
- validate_config の YAML 構文チェックは PyYAML がインストールされている場合のみ有効（未インストールなら警告を出す）。
- research/factor_research はファクター計算の設計を含むが、一部実装が未完（ファイル末尾で途中終了している可能性あり）。実行前に必要な SQL テーブル（prices_daily/raw_financials 等）の準備が必要。

### Security
- .env ファイルの生成テンプレートに「絶対に Git にコミットしないこと」を明記。
- secret 項目（トークン・パスワード）は設定ウィザードでマスク表示することで誤表示を抑制。

---

今後の提案（検討事項）
- research/factor_research の完全実装とユニットテスト追加。
- ポジションサイズ計算で銘柄別 lot_size をサポートする拡張（現在は全銘柄共通 lot_size）。
- monitoring と execution のログ/メトリクスを Prometheus 等にエクスポートする機能追加。
- run_monitoring の監視対象 DB を paper/live で切り替えるオプション（現在は monitoring は常に sqlite_path を使用する仕様）。
- 主要処理の単体テストと CI の整備。

お問い合わせや追加の変更履歴生成が必要であればお知らせください。
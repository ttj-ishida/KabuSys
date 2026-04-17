# CHANGELOG

このプロジェクトの変更履歴は「Keep a Changelog」形式に従います。  
バージョンと日付は、ソース内の初期バージョン情報および本日付（2026-04-17）に基づいて付与しています。

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動用の CLI スクリプト。
    - プロセス優先度を "high" に設定するユーティリティ呼び出しを導入。
    - 環境に応じて SQLite の接続先を切り替え（paper_trading 用は専用 DB を使用し、本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててエンジンを起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）でプロセス管理。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ検知で graceful にループ終了。check_once() の例外はログ出力後次ポーリングへ継続。

- 設定管理・セットアップ・検証ツールを追加
  - config.py
    - .env 自動読み込みロジック（プロジェクトルートを .git/pyproject.toml から探索）。
    - .env の行パースロジックを実装（export 形式、クォート・エスケープ、インラインコメント処理、保護された OS 環境変数の扱い）。
    - Settings クラスを実装して環境変数を型付きプロパティで提供（DB パス、PID パス、しきい値、PAPER_FILL_MODE のバリデーションなど）。
  - config_setup.py
    - 対話式ウィザードで .env の生成・更新を支援。
    - 各設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークンなど）に対するプロンプトと保存処理を提供。
  - validate_config.py
    - .env と config/*.yaml の設定を起動前に検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML がない場合は警告）を実施。
    - --strict フラグで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコアで上位選定（タイブレーク処理あり）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。スコア合計が 0 の場合は等分へフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存ポジションのセクター集中を計算し、上限を超えるセクターの新規候補を除外。
    - calc_regime_multiplier: market regime に対応する投下資金乗数を返す（bull/neutral/bear、未知はフォールバックで 1.0 として警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケーリング処理を実装。手数料やスリッページを考慮する cost_buffer オプションあり。

- 研究・データ処理モジュールを追加
  - research/factor_research.py
    - モメンタム、ボラティリティ等のファクター計算ロジック（DuckDB を用いた SQL 実装）。
    - 200 日移動平均、1/3/6 ヶ月リターン、ATR20、20 日平均売買代金等を計算する関数を提供。

- ユーティリティを追加
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数。
    - 権限不足や未対応プラットフォーム時には警告を出して安全にスキップ。

- 管理ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計。
    - デフォルトの合格基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を定義して PASS/FAIL を判定。
    - 日付フィルタ、DB パス指定（環境変数または --db）に対応。

- パッケージ化情報
  - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- （初期リリース）内部 API 設計と責務分離を実施
  - Execution / Monitoring / Portfolio / Research / Utils が明確な責務で分離され、各モジュールは可能な限り純粋関数（副作用なし）または外部接続を注入する設計を採用。
  - .env 自動読み込みはプロジェクトルートが検出できない場合に自動でスキップするよう保守（配布後の動作を安全化）。

### Fixed
- 環境変数・ファイルパースに対する堅牢性向上
  - config._parse_env_line で export、クォート、バックスラッシュエスケープ、インラインコメントを正しく処理するよう実装。
  - MONITOR_POLL_INTERVAL の負の値や非整数値を検出してデフォルトにフォールバックする処理を追加（警告ログ出力）。

### Security
- 機密情報取扱いに関する注意
  - config_setup で生成される .env に対し「.env を絶対に Git にコミットしないこと」を強調するヘッダを追加。
  - Settings の必須鍵（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）未設定時は ValueError を送出することで起動前に失敗させる（誤った本番起動を防止）。

### Notes / Details
- DB の扱い
  - 監視（monitoring）は環境に関わらずデフォルトの sqlite_path（data/monitoring.db）を使用する設計（運用上の注意点としてログや監視が一元化される）。
  - paper_trading 環境は専用の PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使い、本番 DB と完全分離することで試験運用を安全に実行可能。
- 停止制御
  - run_execution.py / run_monitoring.py はプロジェクト内 data/stop_requested.flag（停止フラグ）を監視し、検知時に安全に停止する。
- ロギングとエラーハンドリング
  - 各起動スクリプトは基本的に logging.basicConfig(level=logging.INFO) を用い、例外発生時はログ出力してリトライ/続行可能な箇所では継続する設計。
- 互換性
  - 既知の破壊的変更はありません（初期リリース）。

---

今後のリリース案内（例）
- 0.2.0: Strategy 実装、ExecutionEngine の詳細なテスト、trading ブローカークライアントのモック/実装強化、単体テスト追加
- 0.1.x: バグ修正、ドキュメント整備、config.yaml のテンプレート強化

（終）
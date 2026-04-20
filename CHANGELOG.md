# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

---

## [0.1.0] - 2026-04-20

### Added
- 基本アプリケーション初期実装を追加（初回リリース）。
  - パッケージ情報
    - パッケージバージョン: `kabusys.__version__ = "0.1.0"`

- 実行・監視用エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine をスレッドで起動し、 data/stop_requested.flag による外部停止（Stop Flag）に対応。
    - 起動時にプロセス優先度を "high" に設定する処理を導入。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトを使用。
    - 監視は実行環境にかかわらず本番の sqlite_path（監視 DB）を使用する設計。
    - stop フラグ（data/stop_requested.flag）でループ終了。KeyboardInterrupt をハンドルしてクリーンに終了。

- 設定管理・ウィザード・検証
  - config.py
    - 環境変数の読み込みと Settings クラスを提供。
    - .env 自動読み込み機能（プロジェクトルート自動検出）。読み込み順: OS 環境 > .env.local > .env。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env 行のパース強化:
      - `export KEY=val` 形式をサポート
      - シングル/ダブルクォート内のバックスラッシュエスケープ対応
      - クォートなしの行で `#` をインラインコメントとして扱う判定を改善
    - 各種設定プロパティを提供（J-Quants トークン、kabuAPI、DB パス、Paper Trading 設定、監視閾値、環境判定など）。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - 既存 .env 読み込み、シークレット項目はマスク表示、保存前の確認を実施。
  - validate_config.py
    - 起動前に .env および config/*.yaml の基本チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML が存在する場合）。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加。
    - stdout へ StreamHandler を出力（cron/Task Scheduler での一本化を想定）、加えて TimedRotatingFileHandler で日次ローテーション（デフォルト logs/、30 日保持）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続するフォールバックを実装。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト "INFO"。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加（Windows/Linux/macOS 等対応）。
    - `set_process_priority(level: "high"|"normal"|"low")` を実装。
    - `set_cpu_affinity(cpu_count)` によりプロセスを最初の N コアにピン留め可能（利用可能なコア数を超える場合は全コア使用）。
    - psutil による例外（権限不足等）を安全にハンドルし、問題時は警告でスキップ。

- ポートフォリオ構築関連（純粋関数群、DB非依存）
  - portfolio/portfolio_builder.py
    - BUY シグナルから候補抽出 select_candidates（スコア降順、タイブレーク: signal_rank）を実装。
    - 等分配 calc_equal_weights とスコア重み calc_score_weights（全スコア 0 の場合は等分配にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター上限チェック apply_sector_cap（既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外）。
    - レジーム乗数 calc_regime_multiplier（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各方式（"risk_based", "equal", "score"）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer による保守的なコスト見積りをサポート。残余キャッシュに基づく端数配分ロジックを実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily / raw_financials を基にモメンタム・ボラティリティ・バリュー等のファクター計算を行うモジュールを追加。（設計・定数・P95 等のユーティリティを含む）
    - 設計方針: DuckDB + SQL/Python による完結型の計算。外部 API を呼ばない。結果は (date, code) キーの dict リストで返却。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 指標（稼働率、注文成功率、送信率、レイテンシ P95 など）を算出し、閾値に基づく PASS/FAIL 判定を提供。
    - P95 計算、日付フィルタ（--from/--to）、DB 存在チェックを実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注:
- 上記は現行コードベースから推測できる機能・設計に基づく CHANGELOG です。実際のリリースノートではユーザに影響のある既知の制限や移行手順（例: .env の取り扱い、KILL フラグの取り扱い等）を補足することを推奨します。
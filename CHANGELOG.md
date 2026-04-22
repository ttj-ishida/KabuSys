# Changelog

すべての notable な変更をこのファイルに記録します。

フォーマットは Keep a Changelog に準拠します。
（https://keepachangelog.com/ja/1.0.0/）

---

## [0.1.0] - 2026-04-22

初回リリース。

### Added
- 一般
  - パッケージの初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - プロジェクト全体の基本 CLI / 実行スクリプトを追加:
    - run_execution.py: ExecutionEngine 起動スクリプト（スレッド実行、停止フラグ監視、PID ファイル対応）。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（停止フラグ検出、MONITOR_POLL_INTERVAL による間隔制御）。
- 設定関連
  - config.py:
    - .env 自動読み込み機構を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env ファイルのパース機能を実装（export 付き形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
    - 環境変数の保護（OS 環境変数を上書きしない仕組み）。
    - Settings クラスを実装し、アプリケーション設定をプロパティ経由で提供。以下の設定を含む:
      - J-Quants / kabu API 関連（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL）
      - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - Paper Trading 用の paper_fill_mode（instant/partial/never/reject の検証）
      - 監視・プロセス管理用ファイルパス（pid_file_path, kill_flag_path, kill_flag_clear_on_start）
      - 閾値設定（cpu/memory/disk）
      - KABUSYS_ENV（development / paper_trading / live）とログレベル検証
  - config_setup.py:
    - インタラクティブな .env 作成・更新ウィザードを追加（対話式プロンプト、既存値の再利用、シークレットマスキング、.env 出力）。
    - デフォルト項目と説明を定義（KABUSYS_ENV、API トークン、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）。
- 設定検証ツール
  - validate_config.py:
    - .env や config/*.yaml の起動前検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在/パースチェック（PyYAML があれば内容を検証）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険値の警告）。
    - --strict モードで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ設定関数 setup_logging を提供。
    - stdout への StreamHandler（stderr ではなく stdout を使用）と、日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。ログディレクトリ自動作成（失敗時はファイル出力をスキップしてコンソールのみ）。
    - ログレベル解決順の明記（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py:
    - set_process_priority(level) を実装。Windows / POSIX（Linux, macOS 等）で適切な優先度に設定し、権限不足や未対応 OS の場合は警告して安全にフォールバック。
    - set_cpu_affinity(cpu_count) を実装（指定なしは何もしない）。権限や未対応 API 時は警告してスキップ。
- Execution 系
  - run_execution.py:
    - Paper Trading 環境 (KABUSYS_ENV=paper_trading) の場合、専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離する設計。
    - BrokerClientFactory によるブローカークライアント生成（paper/live での差異を吸収）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動処理（RiskConfig のデフォルト値を含む）。
    - 停止フラグ検出で安全にエンジンを停止するループ（スレッド実行、最大待機タイムアウト）。
- Monitoring 系
  - run_monitoring.py:
    - SystemMonitor の初期化とポーリングループ実装。MONITOR_POLL_INTERVAL 環境変数で間隔を調整可能（デフォルト 60 秒）。不正な値（0 以下や整数変換失敗）は警告してデフォルトへフォールバック。
    - 監視用 DB は環境（development/paper_trading/live）に関係なく本番 sqlite_path を参照する仕様（監視データの一元化）。
    - SQLite と DuckDB の接続確立、監視 DB 初期化処理の呼び出し。
- Portfolio / ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - 選定・重み計算関数を追加:
      - select_candidates: スコア降順、signal_rank をタイブレーク基準に上位 N を選択。
      - calc_equal_weights: 等金額配分を計算。
      - calc_score_weights: スコア比率に基づく配分。全スコアが 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用。既存保有のセクター露出が閾値を超える場合、そのセクターの新規候補を除外する。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた資金乗数を返す（デフォルトフォールバックと警告を含む）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数決定ロジックを追加（allocation_method: risk_based/equal/score）。
    - 単元株（lot_size）丸め、1 銘柄上限や aggregate cap（利用可能現金）によるスケーリング、cost_buffer（コスト/スリッページ見積り）を考慮した安全な切り詰めと再配分ロジックを実装。
    - 入力が欠損・0 の銘柄はスキップしてログ出力。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）などを SQLite から集計して表示。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）と、Pass/Fail 判定ロジックを実装。
    - --from / --to / --db オプションをサポート。DB 未発見時のエラーメッセージ。
- research
  - research/factor_research.py:
    - DuckDB を使ったファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、ボリューム関連の定数と関数定義の開始）。（ファイルは途中まで実装）

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
- run_monitoring と run_execution はそれぞれ stop フラグファイル（data/stop_requested.flag）や kill フラグの存在を見て安全に終了する設計。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存（30 日保持）。ログディレクトリ作成失敗時はコンソール出力のみ動作する。
- 安全上の注意:
  - KABUSYS_ENV=live の設定は本番運用に直結するため、validate_config での確認を推奨。
  - .env ファイルは絶対に Git にコミットしないこと（config_setup のヘッダにも明記）。

---

今後の予定（例）
- factor_research の完全実装（Momentum, Value, Volatility, Liquidity の計算）。
- ExecutionEngine / Broker クライアントの詳細なテストとモックの充実。
- ロギングや監視指標の拡張（LINE 通知連携など）。

---
# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
注: コードベースから推測して記載しています。

## [0.1.0] - 2026-04-22

初期リリース相当の機能群を追加しました。主に自動売買システムの実行・監視・設定関連ユーティリティ、ポートフォリオ構築ロジック、調査用モジュールを含みます。

### 追加 (Added)
- 実行・監視用エントリポイントスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) を監視し、検知時に安全に停止する。
    - 起動時に PID を data/execution.pid に記録する想定（Engine に渡す）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
- 設定管理・自動ロード
  - config.py
    - Settings クラスを提供し、環境変数から各種設定を取得するプロパティを実装。
    - .env 自動読み込み機能をプロジェクトルート（.git / pyproject.toml 基準）から実行。優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 各種検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装し、不正な値は例外を投げる。
    - 新たにサポートされた環境変数例:
      - MONITOR_POLL_INTERVAL（run_monitoring 用）
      - PAPER_FILL_MODE（paper trading の MockBroker 動作モード、instant/partial/never/reject を許容）
      - PAPER_TRADING_SQLITE_PATH（paper trading 用 DB）
      - KILL_FLAG_CLEAR_ON_START, KILL_FLAG_PATH, PID_FILE_PATH など監視/キルスイッチ関連
      - DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, LOG_DIR など
- 設定ウィザード CLI を追加
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新するツール。secret 区分のマスキング表示、既存値の再利用、選択肢提示などを実装。
    - python -m kabusys.config_setup で実行可能。
    - .env に書き込むテンプレートと注意書きを出力。
- 設定検証 CLI を追加
  - validate_config.py
    - .env と config/*.yaml の存在・基本的妥当性を検査するツール。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検査を実行。
    - --strict オプションで警告を FAIL 扱いにできる。
    - python -m kabusys.validate_config で実行可能。
- ログ設定ユーティリティを追加
  - utils/logging_setup.py
    - setup_logging(app_name, log_dir, level) を提供。
    - stdout 出力 (StreamHandler) と日次ローテーションファイル出力 (TimedRotatingFileHandler: logs/<app_name>.log) をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の解決順、既存ハンドラを一旦クリアする挙動、ログディレクトリ作成失敗時のフェールバック（コンソール出力のみ）を実装。
- プロセス優先度 / CPU affinity ユーティリティを追加
  - utils/process_priority.py
    - set_process_priority(level: "high"|"normal"|"low")：Windows/Linux(Mac含む) を吸収してプロセス優先度を設定。psutil を利用し失敗時は警告でスキップ。
    - set_cpu_affinity(cpu_count: int | None)：指定コア数にプロセスを固定。
- ポートフォリオ構築関連の純粋関数群を追加
  - portfolio/portfolio_builder.py
    - select_candidates：BUY シグナルをスコア降順で上位 N 件抽出。
    - calc_equal_weights：等金額配分の重みを計算。
    - calc_score_weights：スコア比率で重みを計算（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap：セクター集中を防ぐため、既存保有により上限を超えているセクターの新規候補を除外するロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数（フォールバック実装あり）。
  - portfolio/position_sizing.py
    - calc_position_sizes：weights / candidates / portfolio_value 等を元に注文株数を計算。allocation_method に "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash） によるスケーリング、cost_buffer を考慮した保守的見積り、残余配分のフェアネス処理を実装。
  - portfolio/__init__.py に主要関数をエクスポート。
- 調査・分析モジュール（作業中含む）
  - research/factor_research.py
    - DuckDB 接続を受け取り、momentum/value/volatility/liquidity などのファクター計算を行う設計を追加（関数 calc_momentum の実装を含むが一部ファイルは切れているため継続実装が想定される）。
- ペーパートレード検証レポートツールを追加
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・API レイテンシ（平均/最大/P95）等を算出して PASS/FAIL を判定する CLI。
    - P95 計算、閾値 (稼働率 99% 等) を定義しレポートを標準出力に出力。python -m kabusys.tools.paper_verification_report で実行可能。
- パッケージメタデータ
  - __init__.py に __version__ = "0.1.0" を追加。

### 変更 (Changed)
- なし（初期リリースのため新規追加が中心）

### 修正 (Fixed)
- なし（初期リリースのため）

### その他（運用上の注意 / マイグレーション）
- .env の自動読み込みが有効（プロジェクトルートが見つかった場合）。テスト時に自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視データのため常に sqlite_path（デフォルト data/monitoring.db）を使用します。実行環境に関わらず本番監視 DB を参照する設計になっています（運用に応じて注意してください）。
- Paper Trading 実行時は paper_trading 用の SQLite を使用して本番データと分離します。PAPER_TRADING_SQLITE_PATH を利用してパスを変えられます。
- PAPER_FILL_MODE の値は "instant" / "partial" / "never" / "reject" のいずれかを設定してください。不正値は例外になります。
- ログ出力先ディレクトリ作成に失敗した場合はファイル出力をスキップしコンソールログのみで動作します。運用環境では logs ディレクトリ（または LOG_DIR 指定）に書き込み権限があるか確認してください。
- process_priority や CPU affinity の設定は psutil の権限や OS に依存します。権限不足時は警告でスキップされます。
- validate_config と config_setup を併用して初期設定を作成 → 検証するワークフローを推奨します。

---

本 CHANGELOG はコード内容から推測して作成しています。実際のリリースノート作成時は追加の詳細（既知の制限、既存 API の互換性、テストカバレッジ、既知バグなど）を追記してください。
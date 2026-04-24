# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
翻訳・記載はコードベースの内容から推測して作成しています。

全体バージョンはパッケージ定義 (src/kabusys/__init__.py) に従い 0.1.0 としています。

## [0.1.0] - 2026-04-24

### 追加 (Added)
- 基本コア機能を初期実装（日本株自動売買システムの初期公開）。
  - パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクト直下 data/stop_requested.flag ファイルで行う。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 起動時に process priority を "high" に設定（src/kabusys/utils/process_priority.py を利用）。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離。
    - 起動時に process priority を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) 検知で安全にエンジン停止。
    - エンジンの PID を data/execution.pid に管理。
    - ExecutionEngine は Reconciler・OrderManager・RiskManager などの依存を組み立てて起動。

- 設定管理・ヘルパー
  - src/kabusys/config.py: Settings クラスを実装。
    - .env の自動読み込み機構（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 読み込み優先順: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - .env パースは export のサポート、クォート・エスケープ・インラインコメント処理を実装。
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE など）を提供。入力検証含む。
    - settings のインスタンスをエクスポート。

  - src/kabusys/config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 質問ごとに既存値を表示（シークレットはマスク）。
    - .env を自動生成するヘッダ付きファイル出力。
    - デフォルト値や選択肢を提供（KABUSYS_ENV、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）。

  - src/kabusys/validate_config.py: 設定検証 CLI を追加。
    - .env および config/*.yaml の存在チェックと簡易検証（PyYAML がインストールされている場合は YAML のパース検証を行う）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パス親ディレクトリ存在チェック、KABUSYS_ENV=live 時の追加ガード。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順で BUY シグナルを選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を提供。全スコアが 0 のとき等配分にフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック。既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックして 1.0）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数決定（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、リスクベース計算、1 銘柄上限、aggregate cap（利用可能現金を超える場合はスケールダウン）を実装。
    - cost_buffer を使った保守的コスト見積もりと残余キャッシュに対する端数配分ロジックを実装。

- 監視・解析ツール
  - src/kabusys/tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - データベース（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を計算してレポート出力。
    - PASS/FAIL 判定基準を実装（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - コマンドラインで日付範囲や DB パスを指定可能。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なログ設定ユーティリティを提供。コンソール（stdout）と日次ローテートのファイルハンドラをルートロガーに追加。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして続行。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度設定（Windows と POSIX の差分吸収、psutil を利用）。
    - set_cpu_affinity を実装（最初の N コアに固定する）。権限不足等は警告でスキップ。

- データベース接続
  - SQLite / DuckDB を利用するコードを多数に実装（monitoring テーブル初期化呼び出し init_monitoring_db の利用を含む）。
  - 起動スクリプトは sqlite3 と duckdb 両方の接続を確立して使用。

### 変更 (Changed)
- ログ出力ポリシー
  - logging_setup で stdout を StreamHandler に使用（stderr ではなく stdout）。Task Scheduler/cron 等でのログリダイレクトを考慮。

- 環境変数ロードの保護
  - .env 読み込み時に OS 環境変数を protected として上書きを制御（.env.local は override=True だが protected は上書きしない）。

### 修正 (Fixed)
- 入力検証・エラーハンドリング
  - MONITOR_POLL_INTERVAL の不正値（0以下・非整数）に対してデフォルトにフォールバックし、ログ出力で通知（run_monitoring.py）。
  - PAPER_FILL_MODE の不正値に対して明示的な ValueError を送出（Settings.paper_fill_mode）。
  - process priority / cpu affinity の権限不足・未実装関数等のエラーを捕捉してログで警告し、処理を続行するように変更（utils/process_priority.py, utils/logging_setup.py）。
  - config_setup ウィザードでシークレットをマスク表示し、途中キャンセル・EOF を扱う。

### ドキュメント・メッセージ (Documentation)
- 各モジュールに日本語ドキュメント文字列と設計注釈を多数追加（各 .py の先頭 docstring）。
- PortfolioConstruction.md / StrategyModel.md 等を参照する旨のコメントで実装の根拠を明示（コード内コメント）。

### 既知の問題 / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過小見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する必要あり。
  - lot_size の将来的拡張（銘柄別単元対応）は TODO。
- research/factor_research.py:
  - ファイルが途中で切れている（calc_momentum の実装途中で終了）。ファクター計算群は未完（Momentum, Value, Volatility, Liquidity の完全実装が必要）。
- monitoring_db / ExecutionEngine 等の詳細実装はこの差分に含まれている想定だが、本 CHANGELOG は表示されているファイル群に基づく推定であり、実行時の挙動は実環境での検証が必要。
- 一部の外部ライブラリ（psutil, duckdb, PyYAML）の存在に依存。インストールされていない場合は機能制限や警告が発生する。

---

この CHANGELOG は、提示されたソースコードからの推定に基づいて作成しています。実際のリリースノート作成時には、コミット履歴・ pull request・テスト結果に基づく正確な差分確認を推奨します。必要であれば、各機能ごとにより詳細な変更点（関数シグネチャ、既知のバグフィックス一覧、互換性注意点など）を生成します。どの粒度を希望しますか？
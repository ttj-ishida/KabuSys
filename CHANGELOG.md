CHANGELOG
=========

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。
リリース日付はリポジトリ内のバージョンとコード変更から推定しています。

Unreleased
----------

- （現在のスナップショットは 0.1.0 の初期リリース相当です。次の変更はここに記載します。）

0.1.0 - 2026-04-19
------------------

Added
- 基本パッケージを追加（初期リリース）。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔をオーバーライド可能（デフォルト: 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルで検知。
    - 監視用 DB は KABUSYS_ENV に依らず Settings.sqlite_path（本番相当のパス）を使用。
    - duckdb と sqlite3 の接続作成、init_monitoring_db 呼び出しを行う。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBroker を利用し paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に完全分離して記録。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）および実行時 PID ファイル（data/execution.pid）に対応し、安全にスレッドを停止可能。

- 設定・環境読み込み
  - config.py
    - Settings クラスを追加（環境変数経由で各種設定を取得）。
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（条件付き）を考慮。
    - 主要プロパティ:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
      - PAPER_FILL_MODE（有効値: instant | partial | never | reject、デフォルト: instant）
      - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
      - CPU/MEM/DISK 閾値（デフォルト値あり）
      - KABUSYS_ENV の検証（development / paper_trading / live）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- 設定関連ツール
  - validate_config.py
    - .env および config/*.yaml の存在・基本整合性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの存在確認、YAML パーサが利用可能なら config/*.yaml のパース検査を実施。
    - --strict オプションで警告を失敗扱いにできる。
  - config_setup.py
    - .env を対話式に生成・更新するウィザードを追加。
    - 秘匿値は表示をマスク、保存前に確認プロンプトあり。
    - .env の既存値読み込み・デフォルト提示・書き込みロジックを実装。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - setup_logging を提供。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログディレクトリが作れない場合はファイルハンドラを省略してコンソール出力にフォールバック。
    - LOG_LEVEL / LOG_DIR / 引数での上書きをサポート。
  - utils/process_priority.py
    - set_process_priority(level) を提供（high/normal/low）。
    - Windows と POSIX (Linux, Darwin, FreeBSD) を透過的に扱う実装。アクセス権限不足などの場合は警告を出して安全にスキップ。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定（未指定なら無効化）。エラー時は警告でスキップ。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で重みを計算。全銘柄スコアが 0 の場合は等金額にフォールバック（警告あり）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限をチェックし、上限を超えるセクターの新規候補を除外（unknown セクターは除外対象に含めない）。
    - calc_regime_multiplier: market_regime に応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に基づいて発注株数を計算（risk_based / equal / score をサポート）。
    - lot_size（単元）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）を考慮。
    - cost_buffer により手数料・スリッページを保守的に見積もる。必要に応じてスケーリングと残差処理で lot_size 単位に再配分。
    - 設計上の注記: 銘柄別 lot_size を将来追加する余地あり（TODO コメント）。

- 取引検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から指標を集計して検証レポートを生成する CLI を追加。
    - 収集指標: 稼働率（system_status）、Created/Filled/Sent 件数（trade_logs）、リスク却下数（risk_logs）、レイテンシ（avg/max/P95）。
    - 判定基準（デフォルト）:
      - 稼働率 >= 99.0%
      - 注文成功率 (Filled/Created) >= 90.0%
      - 送信率 (Sent/Created) >= 95.0%
      - P95 レイテンシ <= 200 ms
    - コマンドライン引数: --from, --to, --db（db は環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- DuckDB / SQLite の統合
  - run_* スクリプト、ポートフォリオ・リサーチ系で duckdb と sqlite を利用するための接続パターンを導入（duckdb_path / sqlite_path の Settings 経由解決）。

- 研究用モジュール（骨子）
  - research/factor_research.py
    - モメンタム等のファクター計算のための定数・設計を追加（MA/ATR/VOLUME 関連の定数、calc_momentum 関数の骨子を追加）。
    - 実装は DuckDB 上の prices_daily テーブルを前提とした計算を想定（処理の一部は継続実装の箇所あり）。

Changed
- —（初回リリースのため、過去の変更はありません）

Fixed
- —（初回リリースのため、過去の修正はありません）

Removed
- —（初回リリースのため、削除はありません）

Notes / 重要な運用情報
- 環境変数の自動読み込み
  - プロジェクトルートが見つかれば .env を自動で読み込み (.env.local は .env 上書き)。ただし OS 環境変数は保護され、既定では上書きされません。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、Execution は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全に分離します。監視（run_monitoring）は環境にかかわらず Settings.sqlite_path を参照します（設計上の注意）。
- ログ出力
  - コンソールログは stdout に出力され、ファイルは logs/<app_name>.log に日次ローテーション（30日保存）で出力。ログディレクトリ作成不可時はファイル出力は無効化され、コンソールのみで継続します。
- プロセス優先度
  - 起動スクリプトは起動直後にプロセス優先度を "high" に設定します。設定に失敗した場合は警告を出してスキップします（権限による）。
- 停止制御
  - すべての長時間稼働プロセスは data/stop_requested.flag（プロジェクトルートの data ディレクトリ内）で外部停止を受け付けます。Execution は PID ファイルを書きます（data/execution.pid）。
- 設定検証
  - validate_config.py により起動前に設定の基本チェックが可能です。--strict を使うと警告も失敗と見なします。

開発者向け注釈（既知の TODO）
- position_sizing: 銘柄別の単元（lot_size）を銘柄マスタ等から取得する対応が将来的に望ましい（README にも TODO コメントあり）。
- research/factor_research: calc_momentum 等の実装が続き（ファイル末尾で切れている箇所あり）、追加実装が必要。

ライセンス／その他
- この CHANGELOG はリポジトリ内のコードと docstring から推測して作成しています。実際のリリースノートとして利用する場合は、実際のコミット履歴やリリース手順に合わせて調整してください。
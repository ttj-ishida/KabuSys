CHANGELOG
=========

すべての注目すべき変更を記録します。形式は "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-04-28
--------------------

初回リリース。KabuSys の基本的な実行エントリポイント、設定管理、検証ツール、レポート生成機能、ペーパートレード検証ツール、およびレポート/フォーマッタモジュールを含みます。

### Added
- パッケージ初期バージョンを追加
  - パッケージバージョン: __version__ = "0.1.0"

- 実行 / 監視用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI エントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - 起動時に現金・ポジションを照合して総資産を算出。
    - RiskConfig を config/risk_config.yaml から読み込み・バリデーション（値範囲・整合性チェック）。
    - 起動時に Reconciler を実行し、Execution Startup Summary を生成・保存（失敗しても起動は継続）。
    - 実行エンジンは別スレッドで開始され、 data/stop_requested.flag により安全に停止可能。
    - 実行中の PID を data/execution.pid に出力（Engine に渡す）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用（監視データは共通 DB へ）。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
    - 停止は data/stop_requested.flag ファイル検出で行う。

- レポート / 集計用スクリプト
  - run_signal_queue_report.py
    - DuckDB から翌営業日のシグナルを収集して Signal Queue Confirmation View を生成する CLI。
    - オプション: --date (対象日指定), --save (artifacts に保存), --json (JSON 出力)。
    - 出力結果のステータスに応じて終了コードを返す (READY -> 0, それ以外 -> 非ゼロ)。

  - run_pre_market_report.py
    - Pre-Market Report を生成する CLI。
    - DuckDB / SQLite を参照して前日バッチやシグナルキューの状態を評価。
    - --save / --json オプションに対応。BLOCKED 状態の場合は終了コード 1 を返す。

- 設定管理 / ウィザード / 検証
  - config.py
    - 環境変数ラッパー Settings クラスを追加。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。読み込み順: OS 環境 > .env > .env.local（.env.local は override=True）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
    - .env パースの堅牢化: export 形式、クォート文字列、エスケープ、インラインコメントの扱いを正しく処理。
    - 多数のプロパティを提供（J-Quants, kabu API, DuckDB/SQLite パス, paper_trading 用パス, PID/KILL フラグパス, リソース閾値, env/log_level 判定等）。
    - PAPER_FILL_MODE（paper_trading の MockBrokerClient の fill_mode）に対する入力検証（許容値: instant/partial/never/reject）。
    - KABUSYS_ENV の有効値チェック（development, paper_trading, live）。

  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加。
    - 入力項目の一覧とデフォルト、説明、選択肢、シークレット扱いを定義。
    - 生成される .env テンプレートはコミットしないよう注意書き付きで出力。

  - validate_config.py
    - .env および config/*.yaml の検証 CLI を追加。
    - 必須環境変数 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD) のチェック、値のプレースホルダ検出、KABUSYS_ENV / LOG_LEVEL / DB パスの簡易チェック、YAML ファイル存在とパース検証（PyYAML が無ければ YAML 検証をスキップして警告）。
    - KABUSYS_ENV=live の場合の追加注意チェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性など）。
    - --strict オプションで警告を FAIL 扱いにできる。

- レポート生成ライブラリ（純粋関数）
  - operations/signal_queue_report.py
    - DuckDB からシグナルを取得する collect_signals()。
    - SignalQueueReport dataclass を提供し、build_report(), CLI/JSON/Markdown 用フォーマッタ、保存用 save_report() を実装。
    - save_report は artifacts/signal_queue/{date}/ に summary.json, report.md, warnings.json を出力。

  - operations/execution_startup_report.py
    - Reconciler の結果から ExecutionStartupReport を組み立てる関数を提供。
    - READY / READY_WITH_WARNINGS / BLOCKED の判定ロジックと警告生成ロジックを実装。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率/送信率、リスク却下数、レイテンシ P95 等）を集計して人間向けレポートを生成。
    - P95 の計算、SQL クエリの日付フィルタ処理、閾値（稼働率 99% など）に基づく PASS/FAIL 判定を実装。
    - コマンドライン引数で期間指定 (--from, --to) および DB パス指定 (--db) に対応。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 実行時の注意
- .env 自動ロード:
  - デフォルトでプロジェクトルートにある .env / .env.local を自動的に読み込みます。OS 環境変数は上書きされません（保護）。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時などに便利）。

- .env の書式:
  - export KEY=val 形式に対応。
  - シングル/ダブルクォート内のエスケープ文字をサポート。
  - クォート無しの場合は、先頭に # があるか、# の直前がスペース/タブであれば以降をコメントとして扱います。

- 実行環境切替:
  - KABUSYS_ENV は development / paper_trading / live のいずれかを指定します。paper_trading は本番 DB と分離された paper_sqlite_path を使用します。

- MONITOR_POLL_INTERVAL:
  - run_monitoring では MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で指定可能（デフォルト 60 秒）。0 以下や非整数は無視され、デフォルトにフォールバックします。

- 停止フラグ:
  - 多くのランナーはプロジェクトルートの data/stop_requested.flag によるグローバル停止フラグに対応しています。自動執行を停止したい場合は当該ファイルを作成してください。

- Paper trading:
  - PAPER_FILL_MODE により MockBrokerClient の振る舞いを制御できます。有効値は instant / partial / never / reject。

### Removed / Deprecated / Security
- （初回リリースのため該当なし）

今後のリリースでは、各モジュールのユニットテスト追加、外部依存（PyYAML など）に関するインストールガイド、ドキュメント強化、ロギング設定の詳細化などを予定しています。
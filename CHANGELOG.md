# CHANGELOG

このファイルは Keep a Changelog のフォーマットに準拠しています。  
主な変更点はコードベースから推測して記載しています（実装時点の挙動・設計に基づく説明）。

全般:
- 初期リリース相当の機能群を追加。プロダクション／ペーパートレードを念頭に置いた設定、起動スクリプト、ポートフォリオ構築ロジック、検証ツール、ログ・プロセス管理ユーティリティ等を含む。

## [0.1.0] - 2026-04-20

### Added
- 基本情報
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。BrokerClientFactory によるブローカ接続生成、OrderRepository/OrderManager/RiskManager/Reconciler といった実行関連コンポーネントを組み立てて ExecutionEngine を起動する。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - エンジンはデーモン スレッドで実行され、停止フラグ（data/stop_requested.flag）を監視して安全に終了可能。
    - 実行中の PID を data/execution.pid に書き出す仕組み（pid_file の指定）をサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - 停止フラグ（data/stop_requested.flag）でループを終了。KeyboardInterrupt（Ctrl-C）にも対応してクリーンに DB をクローズ。

- 設定・環境変数管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートに基づく自動検出、.env と .env.local の読み込み順を考慮）。
    - .env の読み込みは OS 環境変数を保護する（既存値は上書きされない、.env.local は明示的に上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途向け）。
    - .env の各行パースで export プレフィックス・クォート・エスケープ・インラインコメント等に対応。
    - Settings クラスを提供し、各種設定（J-Quants / kabu API / DB パス / PID / Kill Flag / リソース閾値 / env 判定 等）をプロパティ経由で取得できるようにした。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE（fill モード検証）をサポート。
    - kill_flag_clear_on_start 等の設定を提供。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。選択肢・デフォルト・シークレット入力に対応し、最終確認後に .env を書き出す。
    - 書き出し時に機密値はマスク表示（確認画面）される。

  - validate_config.py
    - 起動前チェック CLI を追加（必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在、config/*.yaml の存在と YAML パース（PyYAML がある場合）等）。
    - --strict オプションで警告を致命的扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（score 降順、同点時 signal_rank によるタイブレーク）、等重配分、スコア加重配分（スコアが全て 0 の場合は等重にフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - セクター集中制限（既存保有のセクター比率が閾値を超える場合に新規候補を除外）を実装。sell_codes（当日売却予定銘柄）を考慮してエクスポージャー計算が可能。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知のレジームは警告を出してフォールバック 1.0）。

  - portfolio/position_sizing.py
    - 株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based：リスク許容率（risk_pct）と損切り幅（stop_loss_pct）に基づく株数決定、単元（lot_size）丸め、1 銘柄上限・利用可能現金による集約上限（aggregate cap）を実装。
    - equal/score：重みに基づく配分、max_utilization による per-position 上限、aggregate cap のスケーリングと lot_size 単位での再配分ロジックを実装。
    - cost_buffer によるスリッページ・手数料見積を考慮した保守的なコスト見積りをサポート。

  - portfolio/__init__.py
    - 上記ユーティリティをエクスポート。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）をルートロガーに設定。既存ハンドラのクリア、ログディレクトリの作成処理、LOG_LEVEL / LOG_DIR による上書きをサポート。
    - ファイルハンドラ作成失敗時はコンソール出力のみで継続。

  - utils/process_priority.py
    - psutil を用いて Windows / POSIX（Linux/Mac/FreeBSD）向けにプロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。
    - サポートされない OS では警告を出してスキップ、権限不足時も例外を投げずに警告でスキップ。

- 分析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB を解析して検証レポートを生成するスクリプトを追加。システム稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を採用。期間フィルタ（--from/--to）や DB パス指定（--db）をサポート。
    - P95 の計算ロジック、SQL での集約クエリ、安全なエラー（テーブル不存在）ハンドリングあり。

- データ分析（研究用）
  - research/factor_research.py（初期実装）
    - DuckDB 接続を受けてモメンタム・ボラティリティ等のファクターを計算するための土台を追加（関数 calc_momentum など）。prices_daily/raw_financials の利用を想定。

### Changed
- DB パスの挙動
  - run_monitoring は「環境にかかわらず本番 sqlite_path を使用する」旨の挙動が明記されている（監視は運用 DB を対象）。一方、run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して本番 DB と分離する設計。

- .env 自動読み込みの仕様
  - プロジェクトルート検出 (.git または pyproject.toml) を基準に自動で .env/.env.local を読み込むように変更。既に OS 環境変数に設定があるキーは保護される（上書きしない）が、.env.local は override=True で再設定を許可する。

### Fixed / Improved
- .env パーサーの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い（クォート有無での差分）を実装して、より実用的な .env パースを実現。
- ログ出力の安定化
  - stdout をデフォルトのストリームに使うことで cron 等からの起動時にリダイレクトしやすくした。ファイルハンドラの作成に失敗してもコンソール出力でフォールバック。
- プロセス優先度設定
  - Windows / Linux / macOS などの差分を吸収し、権限不足や未対応 OS の場合でも安全にスキップ（警告）するよう改善。

### Security / Privacy
- config_setup の確認画面でシークレット値をマスク表示（確認時の露出を抑制）。

### Notes / Breaking changes
- 監視（run_monitoring）は意図的に本番用 sqlite_path を使用するため、開発環境で監視データを分離したい場合は設定（SQLITE_PATH）を変更する必要がある点に注意。
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで従来の挙動に戻せる。

---

（今後のリリース案内）
- 今後は Strategy モジュールの実装完了、ExecutionEngine の詳細なテスト・リスク調整の拡張、研究用ファクター計算の完成、CI・デプロイ関連ドキュメントの追加等を予定しています。要望があれば CHANGELOG に反映します。
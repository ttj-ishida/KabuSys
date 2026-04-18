# CHANGELOG

すべての notable な変更は Keep a Changelog のフォーマットに従って記載しています。  
次回リリースでは Unreleased セクションを更新してください。

All notable changes to this project will be documented in this file.

## [0.1.0] - 初回リリース
（初リリース。コードベースから推測して以下の機能・変更点をまとめています）

### 追加
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループ終了。
    - 監視用 DB は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する旨の挙動を実装。
  - run_execution.py
    - ExecutionEngine（注文実行エンジン）起動スクリプトを追加。
    - `paper_trading` 環境では MockBrokerClient を使用し、ペーパートレード専用 DB（data/paper_trading.db または環境変数で指定）に記録することで本番 DB と分離。
    - 実行エンジンは別スレッドで run_session を実行し、停止フラグ（data/stop_requested.flag）を検知して engine.stop() を呼び出す。
    - 起動時に PID ファイル（data/execution.pid）を扱う仕組みを提供。
- 設定管理・ウィザード・検証
  - config.py
    - 環境変数管理クラス `Settings` を追加。
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）を実装。
    - `.env` の自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 複数の設定プロパティを提供（DB パス、API トークン、ペーパートレード用設定、監視しきい値など）。
    - `paper_fill_mode` のバリデーション（有効値: instant|partial|never|reject）。
    - `env`（KABUSYS_ENV）のバリデーション（development|paper_trading|live）。
  - config_setup.py
    - 対話式 .env 設定ウィザードを追加。既存 .env の読み込み・差分表示・保存機能を提供。
    - 複数の設定項目（J-Quants トークン、kabu API パスワード、DB パス、ログレベル等）に対応。
    - 秘匿値はマスク表示。
  - validate_config.py
    - 起動前に .env および config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV の整合性確認、LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML の存在・パース確認、live 環境向けの追加ガード（LINE 通知設定の有無等）を実装。
    - `--strict` オプションで警告をエラー扱いにできる。
- ポートフォリオ構成ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順、タイブレークは signal_rank）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中の上限処理 apply_sector_cap（既存ポジションのセクター比率が上限超過時に新規候補を除外）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームは警告と共に 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を実装。
    - allocation_method に応じた複数方式をサポート（risk_based / equal / score）。
    - 1銘柄上限、単元株丸め（lot_size）、 aggregate cap（利用可能現金を超える場合のスケーリング）や cost_buffer を考慮したスケールダウンロジックを実装。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加（StreamHandler を stdout に、TimedRotatingFileHandler で日次ローテート）。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
    - 既存ハンドラのクリーンアップ（多重登録防止）。
  - utils/process_priority.py
    - プロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）間の差分を吸収する実装（psutil に依存）。
    - 標準レベル: high/normal/low。権限不足等での失敗は警告でスキップ。
- 監視 DB 初期化ユーティリティ（monitoring.monitoring_db への参照があることから存在を想定）
  - run_monitoring と run_execution の起動時に監視テーブルの初期化（init_monitoring_db）を呼んで、冪等的にテーブルが存在することを保証する設計。
- Execution 系の組み立て（設計レベルの追加）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager といった実行関連コンポーネントの組み立てと起動フローを実装（run_execution.py から参照）。
  - RiskConfig のデフォルト値（max_position_pct=0.20、max_utilization=0.80、rate_limit_per_sec=5、circuit_breaker_errors=10、circuit_breaker_window_sec=60、max_drawdown=0.20）を採用。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレードの検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数等を集計して PASS/FAIL を判定。
    - P95 計算、期間フィルタ（--from / --to）、DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
    - しきい値: 稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 レイテンシ <= 200 ms。
- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" に設定。

### 変更
- 監視の DB 接続ポリシー
  - run_monitoring は KABUSYS_ENV に依存せず常に Settings.sqlite_path（いわゆる「本番」monitoring DB）を使用するよう明記。運用者は監視データを環境分離しない点に注意。
- ログの振る舞い
  - logging_setup は stdout にログを出力する設計にしているため、cron やスケジューラからの起動時に stdout/stderr を統一してリダイレクトしやすくしている。
- .env 自動ロードの挙動
  - OS 環境変数は保護され、.env.local は .env の値を上書き可能（ただし OS 環境変数が既に存在するキーは保護される）。

### 修正（挙動上の注意点）
- 環境変数パーサの堅牢化
  - config._parse_env_line はシングル/ダブルクォート内のバックスラッシュエスケープや、クォートなし値でのインラインコメント判定（`#` の前がスペース/タブの場合のみコメントとみなす）に対応した実装に改良。
- logging_setup はログディレクトリ作成に失敗した場合でもアプリが致命的に停止しないようフォールバックを導入。
- process_priority の設定は権限不足や OS 非対応時に警告を出して安全にスキップするよう実装。

### 既知の制限・注意事項
- research/factor_research.py はファクター計算の設計と多くの関数を含むが、ファイル途中で未完の記述（例: calc_momentum の実装途中で切れている）を検出。現状では calc_momentum 等の一部関数が未実装または未完成の可能性があります。実運用前に該当モジュールの完成・単体テストが必要です。
- run_monitoring と run_execution はそれぞれ SQLite / DuckDB 接続を開いたまま長時間動作する想定。DB 接続の同時アクセスやバックアップなど運用面の制約に注意してください。
- process_priority の設定は OS/権限依存で失敗することがあるため、その場合でも正常に起動する設計ですが、期待する優先度が付与されなかった場合のパフォーマンス影響に注意してください。
- apply_sector_cap: price_map に価格が欠損（0.0）がある場合、エクスポージャーが過少見積もりされる可能性があり、将来的にフォールバック価格の導入を検討中（TODO コメントあり）。
- position_sizing の将来的拡張点: 銘柄別の lot_size を導入する設計が挙げられている（現状は全銘柄共通 lot_size を仮定）。

### セキュリティ
- 機密情報（API トークン、パスワード等）は .env に保存する設計。ただし .env を絶対に Git にコミットしないよう README/運用手順で徹底する必要あり（config_setup のヘッダにも注意喚起を記載）。

---

今後の予定（推測）
- research/factor_research の完成（ファクター計算の SQL/集計ロジックの実装完了）。
- Execution / Broker 周りの統合テスト・リスク制御ロジック（Reconciler / RiskManager）の詳細実装とチューニング。
- ログや監視周りの運用ドキュメント追加（ログローテーション方針、DB バックアップ手順など）。

（以上）
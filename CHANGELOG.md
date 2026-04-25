# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
（この CHANGELOG は与えられたコードベースの内容から推測して作成しています）

## [0.1.0] - 2026-04-25

### 追加
- パッケージ初期リリース: `kabusys` (バージョン 0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py にて `__version__ = "0.1.0"`

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルを検知して行う。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用して接続・初期化。
    - DuckDB も併用して分析用データベースへ接続。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の専用 SQLite（data/paper_trading.db デフォルト）と MockBrokerClient を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - OrderRepository, OrderManager, RiskManager（デフォルト RiskConfig を含む）, Reconciler を組み立て ExecutionEngine を別スレッドで実行。
    - 停止フラグ（data/stop_requested.flag）で安全停止し、PID ファイルを用いる構成。

- 環境設定・管理
  - config.py
    - 環境変数／.env 読み込みロジックを実装。プロジェクトルートを .git または pyproject.toml で自動検出。
    - `.env` と `.env.local` の読み込み順と上書きルールを実装（OS 環境変数は保護）。
    - 複雑な .env パースに対応（export プレフィックス、クォート値、バックスラッシュエスケープ、インラインコメントの取り扱い）。
    - `Settings` クラスを提供し、各種設定（DB パス、API トークン、ログレベル、Kill Switch 設定、監視閾値など）をプロパティ経由で取得可能。
    - `paper_fill_mode` の入力値検証（"instant"|"partial"|"never"|"reject"）や `KABUSYS_ENV`/`LOG_LEVEL` のバリデーションを実装。
    - `settings` シングルトンをエクスポート。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - ユーザに分かりやすいラベル・説明付きで項目を順に入力させ、シークレットはマスク表示。既存値読み込みやキャンセル処理あり。
    - 書き出し時はコメント付きヘッダを付加し、.env の Git コミット注意喚起を行う。

  - validate_config.py
    - 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリの存在確認、config/*.yaml の存在・パースチェック（PyYAML があればパース検証を実行）などを行う。
    - 本番環境向けガード（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険な設定など）を実装。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定: `select_candidates`（スコア降順、同点時 tie-breaker）。
    - 重み計算: `calc_equal_weights`, `calc_score_weights`（全スコア 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限: `apply_sector_cap`（既存保有比率算出、売却予定銘柄除外、"unknown" セクター扱いの注意）。
    - レジーム乗数: `calc_regime_multiplier`（"bull"|"neutral"|"bear" マップと未知レジームでのフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算: `calc_position_sizes`（"risk_based"/"equal"/"score" をサポート）。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer 考慮、残差の優先配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - 既存ハンドラをクリアして二重登録を防止。
    - LOG_DIR や LOG_LEVEL の解決ロジック、ログディレクトリ作成失敗時のフォールバックおよび警告出力を実装。

  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定と CPU affinity ユーティリティを実装（psutil 利用）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を考慮した nice 値・優先度のマッピングと、権限不足や未対応環境での安全なフォールバック。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成 CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ（ms）などを算出。閾値に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ（--from/--to）、DB 指定オプション（--db）をサポート。

- 研究モジュール
  - research/factor_research.py（骨組み）
    - DuckDB 接続を受け取るファクター計算モジュールの骨組みを追加。モメンタム／MA200／ATR 等の定義と仕様（関数設計方針）を記述。
    - calc_momentum の実装を開始（対象日ベースでのモメンタム／MA200乖離率算出を想定、DuckDB の prices_daily を参照）。

### 変更
- ログ出力の標準ストリームを stderr ではなく stdout に統一（cron 等でリダイレクトしやすくするため）。
- ログ初期化時に既存ハンドラを明示的に flush/close してから削除するように変更し、二重ハンドラ登録を防止。

### 修正 / 安全化
- run_monitoring のポーリング間隔取得で環境変数の不正値（非整数、0 以下）に対して警告を出しデフォルト値へフォールバックするように実装（time.sleep に不正値が渡ることを防止）。
- process_priority.set_process_priority や set_cpu_affinity で権限不足や未対応 OS の場合に例外を握り潰して警告ログを出すようにして、起動失敗を防止。
- DB 初期化の idempotency を考慮し、監視テーブル初期化（init_monitoring_db）を起動時に呼んで存在を保証するようにした。

### ドキュメント（コード内コメント）
- 各モジュールに設計意図・使用例・注意点を詳述した docstring を追加。特に portfolio モジュールや研究モジュールでは外部依存を持たない純粋関数であること、将来拡張の TODO を明記。

### 既知の制約 / TODO
- research/factor_research.calc_momentum の実装は途中（ソースの末尾で切れている）。完全実装が必要。
- position_sizing の price 欠損（0.0）時のフォールバック価格ロジックは TODO コメントで指摘済み（前日終値や取得原価の利用を検討）。
- 一部ファイルは外部モジュール（例: Engine, BrokerClientFactory, SystemMonitor 等）への参照を含むが、今回のスナップショットではこれらの実装が含まれていないため統合テストが必要。

---

注: 本 CHANGELOG は提供されたソースコードの内容から推測して作成したものです。実際のコミット履歴や変更日付、細かな実装差分はリポジトリの Git 履歴や開発者の記録に基づく正式な履歴と照合してください。
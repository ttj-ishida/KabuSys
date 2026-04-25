# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
重要な設計判断や環境変数の振る舞いなどはコードから推測してまとめています。

フォーマット:
- Unreleased: 未リリースの変更（現在なし）
- 各リリース: 追加・変更・修正点の要約（日本語）

## [Unreleased]

なし

## [0.1.0] - 2026-04-25

初回リリース。日本株自動売買システム「KabuSys」の基本的な実行基盤、設定管理、監視、ポートフォリオ構築、ユーティリティ、検証ツール、リサーチ用モジュールの一式を追加。

### 追加 (Added)
- コア設定
  - Settings クラス（kabusys.config）を導入。
    - .env の自動読み込み機能（プロジェクトルートの自動検出: .git または pyproject.toml）を実装。
    - 必須/任意の環境変数アクセスプロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH など）。
    - 細かな検証ロジック（KABUSYS_ENV の有効値チェック、PAPER_FILL_MODE の検証等）を含む。
  - _parse_env_line により .env のパースを堅牢化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理に対応）。

- 実行エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を "high" に設定（起動時）。
    - DB 接続: 環境が paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離（data/paper_trading.db がデフォルト）。
    - BrokerClientFactory を用いたブローカー切替（paper_trading の場合は MockBroker を利用する想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動フロー（エンジンは別スレッドで実行、停止フラグの監視、PID ファイル処理）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒、無効値はデフォルトにフォールバック）でポーリング間隔を指定可能。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計（監視 DB を固定で参照）。
    - 停止フラグ（data/stop_requested.flag）検知による安全な終了。

- 設定管理 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新するツールを追加。
    - シークレット項目はマスク表示、選択肢・デフォルト値の提示、保存確認を実装。
  - validate_config.py
    - 起動前の設定検証ツールを追加（環境変数の存在確認、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML 利用時））。
    - --strict オプションで警告を失敗扱いにできる。
    - KABUSYS_ENV=live 時の追加ガード（LINE トークン未設定時の警告、KILL_FLAG_CLEAR_ON_START の危険性注意など）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates（スコアと signal_rank に基づく候補選定）
    - calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等金額配分にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap（同一セクターの既存保有比率上限チェックにより候補除外）
    - calc_regime_multiplier（market レジームに応じた投下資金乗数、未知レジームはフォールバック）
  - portfolio.position_sizing
    - calc_position_sizes（allocation_method: risk_based / equal / score をサポート）
    - 単元株（lot_size）丸め、max_per_stock 上限、aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を考慮した保守的見積り、残余配分ロジックを実装

- ユーティリティ
  - utils.logging_setup
    - ルートロガーの統一設定関数 setup_logging を追加。
    - コンソール出力は stdout を使用（cron/Task Scheduler 等で stdout/stderr を一本化しやすくするため）。
    - 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）と 30 日保持。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority
    - set_process_priority（Windows と POSIX を吸収、psutil ベース）、set_cpu_affinity を追加。
    - 権限不足や未対応プラットフォーム時は警告を出し操作をスキップする安全設計。

- 監視/分析 DB 統合
  - SQLite（監視 DB）と DuckDB（分析 DB）両方の接続を各エントリポイントで確立して使用する設計を採用。

- 検証ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を集計し Pass/Fail 判定（閾値はソース内定義）。
    - P95 計算、日付フィルタ（--from / --to）や DB パスのオーバーライド（--db）をサポート。

- リサーチ（骨組み）
  - research.factor_research
    - モメンタム／バリュー／ボラティリティ／流動性ファクターの計算モジュールを追加（DuckDB 接続を受ける設計）。
    - モメンタム計算のための定数やスキャンウィンドウを定義（実装はモジュール内関数で行う設計）。※ファイルは途中まで（スニペットの最後で切れている）。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。
  - portfolio モジュールの __all__ エクスポート整理。

### 変更 (Changed)
- n/a（初回リリースのため既存からの変更はなし）

### 修正 (Fixed)
- n/a（初回リリースのため既知のバグ修正履歴はなし）

### 仕様上の注意点（重要）
- 監視（run_monitoring）は環境にかかわらず settings.sqlite_path（本番監視 DB）を使用する設計です。監視データを paper_trading DB と分離したい場合は設定やコード側での変更が必要です。
- run_execution は paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離するよう配慮されています。
- MONITOR_POLL_INTERVAL に 0 以下や非数を指定するとデフォルト（60 秒）にフォールバックします（time.sleep に渡せない値による例外回避）。
- process priority / cpu affinity の設定は psutil に依存し、権限不足や未対応 OS では警告を出して安全にスキップします。
- .env の自動読み込みはデフォルトで有効。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- LOG のファイル出力はログディレクトリ作成に失敗した場合は無効化され、コンソール出力のみとなります。

### 既知の改善余地 / TODO（コードから推測）
- position_sizing: 銘柄ごと異なる lot_size をサポートするため stocks マスタから lot_size を受け取る設計への拡張検討（コメントで記述あり）。
- apply_sector_cap: price_map に 0.0（欠損）が含まれる場合のエクスポージャー過少見積りを改善するため、前日終値や取得原価等へのフォールバックを検討。
- research.factor_research モジュールは全機能実装（ファクターの SQL 等）を完了する必要あり（現状は骨組み・定数まで）。

### Breaking Changes
- なし

---

（注）本 CHANGELOG は提供されたソースコードの内容から推測して作成したものです。実際のリリースノートとして公開する前に、変更履歴や設計判断、日付等をプロジェクトの実際の履歴に合わせて調整してください。
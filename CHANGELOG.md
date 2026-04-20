# Changelog

すべての重要な変更点は Keep a Changelog の規約に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-20

### 追加
- 初期リリースとして基本機能を実装。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）と MockBrokerClient を利用するよう分離。
  - run_monitoring: SystemMonitor ポーリングループを起動するスクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag によるフラグ検知で行う。
- 設定管理
  - Settings クラスを実装し、環境変数（および自動読み込みされた .env / .env.local）から設定を取得する仕組みを提供。必須値の検証（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）や各種デフォルト値、論理プロパティ（is_live/is_paper/is_dev）を実装。
  - .env 自動読み込み機能を導入（プロジェクトルートを .git / pyproject.toml から検出）。OS 環境変数は保護して上書きしない挙動を採用。自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env のパーサを強化（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、行中コメントの扱いなど）。
- 設定ユーティリティ / CLI
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を追加（秘密値マスク表示、保存確認など）。
  - validate_config: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML がある場合）など。`--strict` オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテーション、30 日保持）を統一的に設定するユーティリティを追加。ログディレクトリの自動作成、作成失敗時はファイル出力をスキップする堅牢な実装。
  - utils.process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加。Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、設定失敗時は警告を出して継続。CPU affinity を設定するヘルパも実装。
- データベース統合
  - DuckDB を分析用途に採用（設定: DUCKDB_PATH）。起動スクリプトから duckdb 接続を注入。
  - 監視用 SQLite DB の初期化ユーティリティ（init_monitoring_db）を呼び出して、監視テーブルの存在を保証する処理を追加（冪等）。
- Execution / Risk / Order 関連（アーキテクチャ）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等のコンポーネントを組み立てて実行スレッドで稼働させる起動フローを実装。ExecutionEngine は PID ファイルを扱い、停止フラグで安全停止可能。
  - RiskManager の初期設定（例: max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をサンプル値で組み込み、ExecutionEngine 起動時に broker.get_available_cash() を利用して初期ポートフォリオ値を設定する仕組みを提供。
- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite DB から期間指定で検証レポートを生成する CLI を追加。システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計し、閾値に基づく PASS/FAIL 判定を行う。閾値はソース内定数で定義（例: 稼働率 >= 99%、P95 <= 200ms 等）。
- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap と、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知レジームはフォールバックで 1.0 を返し警告ログを出す。unknown セクターは上限適用対象外扱い。
  - portfolio.position_sizing: 各銘柄の発注株数計算を実装。allocation_method に "risk_based" / "equal" / "score" をサポート。損切り率や lot_size、cost_buffer（手数料・スリッページの見積り）を考慮した aggregate cap のスケーリング、単元株（lot_size）丸め、残余キャッシュを使った端数配分ロジック等を備える。
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の制約 / 注意点
- Settings の一部プロパティは未設定時に ValueError を投げる（必須環境変数）。デプロイ前に config_setup / validate_config を実行して環境を整えてください。
- run_monitoring は監視データベースとして常に settings.sqlite_path（デフォルト: data/monitoring.db）を利用する設計です。実行環境にかかわらず監視 DB は本番用パスが使われることに注意してください。
- research.factor_research モジュールはモメンタム計算の骨格が実装されているものの、ファイル末尾が未完（処理の一部が継続実装中）です。ファクター計算周りは引き続き実装・検証が必要です。
- process_priority と CPU affinity の設定は権限依存（OS による）で失敗する場合がありますが、その場合はログに警告を出してスキップします。
- ログディレクトリの作成に失敗した場合はファイルロギングを無効化してコンソールのみで稼働します。

---

今後の予定（例）
- research モジュールの各ファクター（Value, Volatility, Liquidity）の実装完了および統合テスト。
- ExecutionEngine / Broker クライアント周りの統合テストとペーパートレード向けの検証強化。
- パフォーマンス測定結果に基づくポジションサイジングやリスク管理ロジックのチューニング。

（必要があれば、各ファイル単位の細かな変更点やコミット単位の履歴に基づいた詳細版 CHANGELOG を作成できます。ご希望を教えてください。）
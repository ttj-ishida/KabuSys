# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
現在のバージョン: 0.1.0 — 2026-04-23

## [0.1.0] - 2026-04-23

初期リリース。KabuSys のコア機能およびユーティリティ群を追加しました。

### 追加
- パッケージ初期化
  - __version__ を 0.1.0 に設定。
  - パッケージ公開用の基本モジュール構成を追加（data, strategy, execution, monitoring などを想定）。

- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - プロセス優先度を起動時に設定（set_process_priority("high")）。
    - KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB を使用し MockBrokerClient を利用（本番 DB と分離）。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）による制御。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立てて起動。
    - RiskManager のデフォルト設定を初期化（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視 DB を必ず監視対象 DB に接続して記録）。
    - stop フラグ検出によりループを安全に終了。
    - SQLite / DuckDB 接続の初期化（init_monitoring_db 呼び出し）。

- 設定管理
  - config.py
    - 環境変数のラッパー Settings クラスを追加。
    - .env 自動読み込み（プロジェクトルート = .git または pyproject.toml を検索）を実装。優先順は OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env の行パースはエクスポート形式、クォート、エスケープ、インラインコメント（スペース前の #）などに対応する堅牢な実装。
    - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH、しきい値系 CPU/MEM/DISK、KABUSYS_ENV/LOG_LEVEL 判定等）。
    - KABUSYS_ENV の許容値チェック、LOG_LEVEL のバリデーション、PAPER_FILL_MODE の許容値チェックを実装。

  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加。
    - J-Quants / kabu API / DuckDB/SQLite パス / LINE 通知 / LOG_LEVEL / Kill Switch の設定項目を対話的に入力・保存可能。
    - 既存の .env を読み込み、Enter で既存値を再利用可能。秘密値はマスク表示。
    - 書き込み時にテンプレート形式で .env を生成。

  - validate_config.py
    - 設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）構文検証を実施。
    - 本番（live）環境向けの追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険性警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング初期化ユーティリティを追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。ファイル出力は LOG_DIR / デフォルト logs/ に配置。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみ継続。
    - ログレベルの解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。

  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows と POSIX を吸収）。
    - set_process_priority(level) による優先度設定（high/normal/low）。
    - set_cpu_affinity(cpu_count) による CPU コア固定機能。
    - psutil による実装で権限不足や未対応環境は警告してスキップ。

- portfolio（ポートフォリオ構築）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定と重み計算機能を追加。
    - select_candidates: スコア降順・同点は signal_rank 小のものを優先。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全スコアが 0 の場合は等金額にフォールバックして警告）。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を追加。
    - apply_sector_cap は既存保有のセクター比率を計算し、上限を超えるセクターの新規候補を除外。unknown セクターは制限免除。
    - calc_regime_multiplier は regime (bull/neutral/bear) に応じた資金乗数を返す（未知レジームは警告して 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - ポジションサイズ（発注株数）算出ロジックを追加。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）を考慮してスケーリング。cost_buffer により保守的にコストを見積もる。
    - スケールダウン時に端数処理（lot 単位での残差分配）を実装。

  - portfolio/__init__.py
    - portfolio モジュールを公開インターフェイスとしてまとめてエクスポート。

- research
  - research/factor_research.py（ファクター計算モジュールを追加。モメンタム・ボラティリティ・バリュー等の計算を設計）
    - DuckDB 接続を受ける設計。prices_daily / raw_financials を参照して各種ファクターを算出する方針を実装（モジュール途中までの実装を含む）。

- tools
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。
    - SQLite（デフォルト data/paper_trading.db）から system_status / trade_logs / risk_logs を読み取り、稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - P95 計算ユーティリティ、各種閾値による PASS/FAIL 判定を実装。
    - コマンドラインオプション: --from, --to, --db。

- 監視・DB初期化
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出して、監視用テーブルが存在することを保証（冪等に初期化）。

### 変更（設計上の決定）
- 監視（run_monitoring）は KABUSYS_ENV に依存せず常に本番用 sqlite_path を使用する設計に明示。
- run_execution は paper_trading モード時に DB とブローカーを完全に分離することで本番注文との混同を防止する設計。

### 既知の制約 / 注意点
- 一部モジュールは外部パッケージに依存（psutil、duckdb, sqlite3 は標準/拡張依存）。config ファイル YAML 検証は PyYAML がないとスキップされる（警告）。
- research/factor_research.py はファイル末尾で未完了箇所があり、追加実装が必要（ファクター計算ロジックの一部が継続実装扱い）。
- .env ファイルには機密情報が含まれるため絶対に Git にコミットしないことを README 等で注意すること（config_setup でも注記あり）。

### セキュリティ
- 設定取得時に必須項目が未設定なら ValueError を送出する実装により、起動前にミスを検出しやすくしています。
- 本番環境向けの安全装置（KILL_FLAG_CLEAR_ON_START デフォルト 0 推奨、LINE 通知未設定の警告等）を用意。

---

今後の予定（例）
- research/factor_research の完了および単体テストの追加。
- ExecutionEngine / SystemMonitor 周りの統合テストと起動時の安全フロー検証。
- 単体テスト・CI 周りの整備とドキュメント（README、デプロイ手順）整備。
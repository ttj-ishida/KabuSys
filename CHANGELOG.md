# Changelog

すべての重要な変更履歴をここに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

注意: この CHANGELOG は与えられたコードベースから機能・挙動を推測して作成しています。

## [Unreleased]

（現在のリリース以後の変更点はここに記載してください）

---

## [0.1.0] - 2026-04-25

初回リリース。システムの起動スクリプト、設定管理、ログ・プロセスユーティリティ、ポートフォリオ構築ロジック、ペーパートレード検証ツール、ファクター計算基盤などの主要コンポーネントを導入。

### Added
- エントリポイント / 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを開始するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループ終了。
    - 監視処理は環境にかかわらず本番用の sqlite_path を使用する仕様。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient（BrokerClientFactory 経由）を利用し、paper_trading 用 DB（data/paper_trading.db）に分離して記録。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う制御を実装。
    - 実行はデーモンスレッドで行い、停止フラグ検知でエンジンを停止する仕組みを提供。

- 設定管理・検証・セットアップ
  - config.py
    - .env の自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）を実装（無効化は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。
    - 柔軟な .env パーサを実装（export 文、クォート、インラインコメント対応）。
    - Settings クラスで各種環境変数をプロパティとして提供（DB パス、API トークン、PAPER_FILL_MODE のバリデーション、閾値など）。
    - 環境（KABUSYS_ENV）とログレベルのバリデーションを実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期生成・更新する CLI を追加。項目のマスク表示、デフォルト・選択肢の提示をサポート。
  - validate_config.py
    - 起動前に .env や config/*.yaml の問題を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスと config YAML の存在・パースチェック、live 専用ガード（LINE 通知設定や Kill Switch の注意）等を実施。
    - `--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 select_candidates（スコア降順・タイブレークロジック）。
    - 重み計算: calc_equal_weights（等分配）、calc_score_weights（スコア正規化、全スコア 0 の場合は等分配フォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック。既存ポジションのセクター比率が閾値を超えると同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す（未知レジームは警告とともに 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash によるスケーリング）および cost_buffer を考慮したスケーリングと残余配分ロジックを実装。
    - risk_based モードでは stop_loss_pct と risk_pct を用いたリスクベース算出をサポート。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ設定。
    - LOG_DIR / LOG_LEVEL の解決優先度、既存ハンドラのクリア処理、ファイル出力作成失敗時のフォールバックを実装。
  - utils/process_priority.py
    - プラットフォーム差分を吸収した set_process_priority（high/normal/low）を実装（Windows の優先度定数と POSIX nice 値を考慮）。
    - set_cpu_affinity によりプロセスの CPU ピン留め（最初の N コア）を設定可能。権限不足などは警告で無効化。

- データベース・分析基盤
  - DuckDB と SQLite の両方に接続する設計を導入（設定は Settings で管理: DUCKDB_PATH / SQLITE_PATH）。
  - 監視テーブル初期化用の init_monitoring_db 呼び出しを各起動時に実行（冪等にテーブル存在を保証）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を解析し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数などを集計してレポートを出力する CLI を追加。
    - 判定基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）が設定されており、PASS/FAIL 判定を表示。
    - 日付フィルタ（--from/--to）や --db で DB パス指定が可能。

- 研究用ファクター計算（基盤実装）
  - research/factor_research.py
    - DuckDB 接続を受けて Momentum / Value / Volatility / Liquidity 系ファクターを計算するための基盤実装（モメンタム計算のための定数やインターフェースを準備）。
    - 設計方針: prices_daily / raw_financials テーブルの参照のみで外部 API へ依存しない純粋関数群として実装予定。

### Changed
- N/A（初回リリースのため変更履歴なし）

### Fixed
- N/A（初回リリースのため修正履歴なし）

### Notes / Implementation details / 環境変数
- 自動 .env 読み込み
  - プロジェクトルートが特定できる場合、`.env` を読み込み（既存 OS 環境変数を保護）、`.env.local` は上書き可能。
  - 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- 重要な環境変数（主要なもの）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development / paper_trading / live）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
  - MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading の fill 動作: instant / partial / never / reject）
  - KILL_FLAG_CLEAR_ON_START（本番での Kill Switch 自動クリア制御）
  - LOG_LEVEL / LOG_DIR
- DB 分離
  - 監視（monitoring）処理は環境を問わず sqlite_path（本番想定）を使用する。
  - 実行エンジンは paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離。
- ログ
  - コンソール出力は stdout を使用（cron/task からのリダイレクトを想定）。
  - ファイル出力は logs/<app_name>.log に日次ローテーションで出力、デフォルト 30 日保持。
- フォールバック / エラーハンドリング
  - 環境変数パースや設定検証で不正値が見つかった場合は適切に警告/例外を発生させる（Settings のプロパティで検査）。
  - プロセス優先度や CPU affinity の設定は権限不足や未サポート OS の場合に安全にスキップしてログ警告を出力。

---

今後の予定（アイデア）
- research/factor_research の完全実装（Momentum 等の具体的 SQL/計算ロジックの追加）。
- Strategy / Execution のさらに細かい単体テストとモジュール分離（ブローカー抽象化の拡張）。
- ファイルベースの設定テンプレート（config/*.yaml）の生成・検証機能の充実。
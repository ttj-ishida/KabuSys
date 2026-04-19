# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリース日付はコードベースの最新状態に基づき推測しています。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除された機能
- Security: セキュリティ修正

## [Unreleased]

- ドキュメント・テスト用のマイナー修正や内部リファクタを想定（現状のコードベースからは未確定）。

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ初期実装を追加。
  - package version: `kabusys` v0.1.0（src/kabusys/__init__.py）。
- 起動用スクリプトを追加:
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 停止はプロジェクトルート/data/stop_requested.flag を監視して行う。
    - 監視用 DB は環境に依らず本番の sqlite_path を使用する実装。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - `KABUSYS_ENV=paper_trading` 時は Paper Trading 用の専用 SQLite DB（data/paper_trading.db をデフォルト）を使用し、Mock ブローカークライアントを利用する想定。
    - 停止フラグ・PID ファイル管理をサポート（data/execution.pid, data/stop_requested.flag）。
- 設定管理と初期化ツール:
  - config.py
    - .env 自動読み込み（プロジェクトルートの .env / .env.local を優先）、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env ファイルのパース実装（コメント、クォート、export 構文対応）。
    - 各種設定プロパティ（DB パス、API トークン、閾値、環境モード判定など）を提供。環境値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を実装。
    - J-Quants / kabu API / DB / LINE 通知など主要項目を対話で設定可能。
  - validate_config.py
    - 起動前の設定検証 CLI を提供（必須環境変数、KABUSYS_ENV 検証、ファイル存在、YAML パース（PyYAML があれば）など）。
    - `--strict` オプションで警告も失敗扱いにできる。
- モニタリング DB 初期化フック（monitoring.monitoring_db への初期化呼び出しが起動スクリプトに組み込まれている）。
- 実行系コンポーネントの組み立て（ExecutionEngine 周り）:
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）などの起動シーケンスを組み立てるコードを実装。
  - RiskConfig のデフォルト値を設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - RiskManager の初期化時に broker.get_available_cash() を用いて initial_portfolio_value を取得する想定。
- ユーティリティ:
  - logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次, 30日分保持）を設定するユーティリティを追加。
    - LOG_DIR / LOG_LEVEL を尊重し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを提供。
    - set_process_priority("high"|"normal"|"low") および set_cpu_affinity をサポート。アクセス拒否等は警告でスキップ。
- portfolio モジュール（ポートフォリオ構築関連の純粋関数群）:
  - portfolio_builder.py
    - select_candidates, calc_equal_weights, calc_score_weights を実装（スコアが全て 0 の場合は等分配へフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap（セクター集中上限チェックによる候補除外）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）を実装。未知レジームは 1.0 にフォールバック。
  - position_sizing.py
    - calc_position_sizes を実装。allocation_method による分配 ("risk_based", "equal", "score")、単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケーリング、cost_buffer を考慮した安全なスケーリング処理を提供。
  - package エクスポート（kabusys.portfolio）を追加。
- tools:
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成 CLI を実装。PAPER_TRADING_SQLITE_PATH（または --db）からデータを集計し、稼働率・注文成功率・送信率・API レイテンシ（P95 等）を計算して PASS/FAIL 判定を出力。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
- research:
  - research/factor_research.py（ファクター計算モジュールの骨組み）
    - Momentum 等の計算を行うための定数と calc_momentum の雛形を追加（DuckDB 接続想定）。実装は継続中の箇所あり（コード断片あり）。

### Changed
- なし（初期リリース）。

### Fixed
- なし（初期リリース）。

### Removed
- なし（初期リリース）。

### Notes / Implementation details
- デフォルトパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite(監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID / stop flag / kill flag: data ディレクトリ下のファイルを想定
  - ログディレクトリ: logs/
- ログ出力は意図的に stdout を使用（cron 等でリダイレクトを想定）。
- .env 読み込みはプロジェクトルートの検出（.git または pyproject.toml）に基づくため、カレントワーキングディレクトリに依存しない。
- Paper Trading と本番 DB は分離される設計（run_execution.py が環境に応じて別 DB を選択）。
- process_priority の設定は権限不足や未対応 OS 上で安全にスキップされる（警告ログのみ）。

---
今後の予定（想定）
- research/factor_research の完全実装（ファクター計算の SQL/集約ロジック）。
- ExecutionEngine 等の詳細実装とテスト整備（ブローカークライアントの具象実装、mock の整備）。
- CI / テストケース追加、ドキュメント整備（API や設定例、運用手順）。

もし CHANGELOG に含めたい追加情報（実際のリリース日やリリースノートの粒度、特定のコミットやイシュー参照など）があれば教えてください。追記・修正して再出力します。
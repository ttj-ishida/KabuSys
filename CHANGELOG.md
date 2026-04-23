KEEP A CHANGELOG に従った CHANGELOG.md を以下に作成しました（日本語）。リポジトリ内のコードから推測して記載しています。必要に応じて日付や文言を調整してください。

---------------------------------------------------------------------
CHANGELOG.md
---------------------------------------------------------------------

# Changelog

すべての注記は Keep a Changelog の方針に従います。  
リリースはセマンティックバージョニングに準拠します。

## [0.1.0] - 2026-04-23

### 追加 (Added)
- 初期リリースを公開。
- 実行用エントリポイントを追加:
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Mock ブローカーを使用し、データベースを paper_trading 用（デフォルト: data/paper_trading.db）に分離。
    - BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、スレッドで engine.run_session を実行。停止フラグ (data/stop_requested.flag) を監視して安全に停止可能。
    - pid ファイル (data/execution.pid) を利用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視用 DB 初期化（init_monitoring_db）を行い、監視は環境に関わらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) による終了制御を実装。

- 設定・環境周り:
  - config.py
    - Settings クラスを実装。環境変数取得のラッパー、バリデーション、デフォルト値を提供。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等のデフォルトやパス解決を実装。
    - PAPER_FILL_MODE の妥当性チェック（"instant" / "partial" / "never" / "reject"）を実装。
    - KABUSYS_ENV の有効値チェック（development / paper_trading / live）。
  - 自動 .env 読み込み実装:
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（OS 環境変数は保護して上書き制御）。
    - .env 行のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応する堅牢な実装。
- 設定支援ツール:
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を実装。
    - J-Quants、kabu API、DB パス、ログレベル、Kill Switch など主要項目を対話入力で設定可能。
- 設定検証ツール:
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検査する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV、LOG_LEVEL、DB パスの存在確認、config YAML のパースチェック（PyYAML がある場合）を行う。
    - --strict オプションで警告も失敗扱いにできる。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）。
- ロギング・プロセス制御ユーティリティ:
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通セットアップを実装。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみで継続。
    - 標準出力に stdout を使用することで外部スケジューラとの連携を考慮。
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - Windows / POSIX の差分を吸収し、psutil の利用で安全に優先度・CPU affinity を設定。失敗時は警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）:
  - portfolio/portfolio_builder.py
    - select_candidates (スコア順ソート)
    - calc_equal_weights (等金額配分)
    - calc_score_weights (スコア加重、全スコア 0 の場合は等金額にフォールバック)
  - portfolio/risk_adjustment.py
    - apply_sector_cap (既存保有を基にセクター集中を抑制するフィルタ)
    - calc_regime_multiplier (market regime に基づく投下資金乗数、既定: bull=1.0, neutral=0.7, bear=0.3)
    - 不足データや未知レジームに対するフォールバック挙動を明記・ログ出力。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate キャップ、cost_buffer による保守見積り、スケールダウン + 残差配分アルゴリズムを実装。
- 研究用ファクター計算:
  - research/factor_research.py
    - モメンタム等のファクターを計算するための骨組み（DuckDB 経由で prices_daily / raw_financials を参照する設計）。計算に必要な定数群を定義。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を参照して検証レポートを生成する CLI。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し、閾値に基づく PASS/FAIL を判定。
    - P95 計算、期間フィルタ、SQL の堅牢なエラーハンドリングを実装。

### 変更 (Changed)
- なし（初期リリース）

### 修正 (Fixed)
- .env 読み込みの堅牢化:
  - export プレフィックス、クォート内エスケープ、インラインコメントの扱いを改善。
  - .env.local を .env より優先して読み込みでき、OS 璁環境変数を保護して上書き制御を行う。
- ロギング:
  - ログのファイル出力失敗時に stderr ではなく stdout/stderr を考慮して警告する動作を安定化。

### 破壊的変更 (Breaking Changes)
- なし（初期リリース）

### セキュリティ (Security)
- .env ファイルは決してリポジトリにコミットしないよう README とウィザード内コメントで注意喚起。

---------------------------------------------------------------------
注意・補足
- run_monitoring と run_execution はそれぞれ単独プロセスとして想定され、共通で duckdb を利用します。
- 実際の ExecutionEngine / SystemMonitor / BrokerClient の具体実装はこの差分に含まれていないため、公開 API の詳細や起動パラメータは実装側に依存します。
- research/factor_research.py はファイル末尾が途中で切れているように見えるため、完全な実装は別途追加が必要です。
- 日付はスナップショット作成日 (2026-04-23) を使用しています。必要に応じて変更してください。

---------------------------------------------------------------------

必要ならば:
- Release ノートを英語で出力
- 各ファイルごとの詳細な変更点や利用例（CLI オプション、環境変数一覧）を別途作成します。どれを希望しますか？
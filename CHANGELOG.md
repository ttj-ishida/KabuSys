# Changelog

すべての変更は「Keep a Changelog」の形式に準拠して記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

（現在の差分はありません）

## [0.1.0] - 2026-04-21

初回公開リリース。本リリースでは日本株自動売買システムのコアユーティリティ、実行・監視用スクリプト、ポートフォリオ構築ロジック、設定管理ツール、検証ツール群、および分析補助モジュールの初期実装を追加しています。

### Added
- 基本情報
  - パッケージメタ情報を追加（__version__ = "0.1.0"）。
- 設定管理
  - Settings クラス（src/kabusys/config.py）を追加し、環境変数経由での設定取得を統一：
    - J-Quants / kabu API / DBパス / ログレベル / 環境モード（development/paper_trading/live）などをプロパティとして提供。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START 等の設定をサポート。
  - .env 自動ロード機能を追加：
    - プロジェクトルート（.git または pyproject.toml を基準）を検出して .env / .env.local を読み込む。
    - OS 環境変数を保護（.env.local の上書き挙動を制御）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 高度な .env パーサを実装（クォート、エスケープ、インラインコメント処理を考慮）。
- 設定ウィザード / 検証 CLI
  - config_setup（src/kabusys/config_setup.py）:
    - 対話式ウィザードで .env を初期作成/更新。
    - シークレット項目のマスク表示、選択肢サポート、保存前の確認を実装。
  - validate_config（src/kabusys/validate_config.py）:
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DBパスの親ディレクトリ確認。
    - config/*.yaml の存在確認（PyYAML がある場合はパース検証を実施）。
    - --strict オプションで警告を Fail 扱いに可能。
- 実行・監視スクリプト
  - 実行エンジン起動スクリプト run_execution（src/kabusys/run_execution.py）:
    - ExecutionEngine の起動／PID 管理、停止フラグ（data/stop_requested.flag）検知、paper_trading 時の DB 分離（data/paper_trading.db）をサポート。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立てを行う。
    - リスク管理用のデフォルト設定値を指定（max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - 監視ループ起動スクリプト run_monitoring（src/kabusys/run_monitoring.py）:
    - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。
    - 監視用 DB（monitoring）は環境にかかわらず本番 sqlite_path を使用する仕様を明示。
    - 停止フラグ検知、例外を捕捉して次ポーリングへフォールバック、KeyboardInterrupt 対応。
- ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）:
    - ペーパートレード履歴（SQLite）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して PASS/FAIL を出力するレポートツールを追加。
    - デフォルト DB パスは data/paper_trading.db。期間指定（--from / --to）対応。
    - P95, 平均, 最大などの集計と、指標閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）に基づく判定を実装。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio モジュールを追加（src/kabusys/portfolio/）:
    - portfolio_builder:
      - select_candidates：スコア降順で候補を選択（タイブレークに signal_rank を使用）。
      - calc_equal_weights / calc_score_weights：等金額・スコア加重の重み算出。全スコアが 0 の場合は等金額へフォールバック。
    - risk_adjustment:
      - apply_sector_cap：セクター集中（max_sector_pct）を超える場合に新規候補を除外。unknown セクターは制限対象外。
      - calc_regime_multiplier：レジーム（bull/neutral/bear）に応じた投下資金乗数（1.0/0.7/0.3）。未知レジームは 1.0 にフォールバック。
    - position_sizing:
      - calc_position_sizes：allocation_method（risk_based / equal / score）に応じた発注株数計算。
      - 単元株（lot_size）での丸め、max_position_pct / max_utilization による per-stock/aggregate 上限、cost_buffer による保守見積り、合計が available_cash を超える場合のスケールダウン処理（端数配分の再割当てを含む）を実装。
- ログ & プロセス管理ユーティリティ
  - logging_setup（src/kabusys/utils/logging_setup.py）:
    - ルートロガーの統一設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログディレクトリの解決順（引数 > LOG_DIR 環境変数 > デフォルト logs/）。ディレクトリ作成が失敗した場合はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラをクリアして二重出力を防止。
  - process_priority（src/kabusys/utils/process_priority.py）:
    - psutil を用いて Windows / POSIX を跨いだプロセス優先度設定（high/normal/low）を実装。set_cpu_affinity も提供。
    - 権限エラーや未対応 OS は警告してスキップするフェールセーフを備える。
- 研究・因子分析補助
  - research/factor_research（src/kabusys/research/factor_research.py）:
    - DuckDB 接続からモメンタム / ボラティリティ / バリュー等のファクターを計算するための骨組みと定数（MA/ATR 等）を追加。DuckDB ベースでの時系列計算を想定した設計。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- なし

### Notes / 実装上の安全策・挙動
- run_execution は paper_trading モード時に paper 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB とデータを分離します。
- run_monitoring は監視 DB に対して本番 sqlite_path を用いる設計で、環境に依存しない監視を実現します。
- .env の自動読み込みは OS 環境変数を上書きしないデフォルト挙動、.env.local は上書き（ただし OS 環境変数は保護）となります。
- logging_setup はログディレクトリ作成失敗やファイルハンドラ生成失敗時にコンソールログのみで安全に動作を継続します。
- process_priority / CPU affinity の設定は権限不足や未対応プラットフォームで失敗してもワーニングを出して処理を継続します。

---

履歴に関する補足や追加で含めたい点（例: 既知の問題、後続リリースで予定している改良点等）があれば教えてください。必要に応じてリリースノートを追記・調整します。
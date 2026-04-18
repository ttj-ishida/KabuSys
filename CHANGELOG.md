# CHANGELOG

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

最新: Unreleased

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18
最初の公開リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築、検証ツール類を導入。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py、バージョン 0.1.0）。
- 起動スクリプト / デーモン類
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポートし、安全に停止を行う。
    - スレッドでエンジンを実行し、停止フラグ検出時に engine.stop() を呼ぶことでグレースフルシャットダウンを実現。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を利用して監視テーブルを初期化。
    - 停止フラグ検出による終了、KeyboardInterrupt による終了をハンドル。
- 設定管理 / 初期化
  - config.py: 環境変数読み込み・管理モジュールを追加。
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env / .env.local の読み込み優先度（OS 環境 > .env.local > .env）。既存 OS 環境変数の保護機構を実装。
    - 複雑な .env 行パース（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い）を実装。
    - Settings クラスでアプリケーション設定をプロパティ経由で取得。PAPER_FILL_MODE バリデーション、パス類の Path 化、env 判定ユーティリティを提供。
- 設定操作 / 検証 CLI
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）。
    - 既存 .env 読み込み、入力の再利用、シークレットマスク表示、保存確認、.env 出力テンプレートを実装。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパースチェック（PyYAML が無い場合はスキップ）。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder.py:
    - シグナル並び替え/候補選定 (select_candidates)。
    - 等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。スコアが全て 0 の場合のフォールバックで警告を出力。
  - portfolio.risk_adjustment.py:
    - セクター集中制限の適用 (apply_sector_cap)。既存保有のセクター別エクスポージャー計算、上限超過セクターの候補除外。
    - 市場レジームに応じた投下資金乗数 (calc_regime_multiplier)（bull/neutral/bear をサポート、未知レジームは 1.0 にフォールバック）。
  - portfolio.position_sizing.py:
    - 発注株数決定ロジック (calc_position_sizes) を実装。risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）対応、最大ポジション比率上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り、端数処理ロジックを実装。
  - portfolio パッケージのエクスポートを整理（__all__）。
- ユーティリティ
  - utils.logging_setup.py:
    - 統一的なログ設定ユーティリティを導入。stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル/ログディレクトリの解決順（引数 > 環境変数 > デフォルト）。
  - utils.process_priority.py:
    - クロスプラットフォームなプロセス優先度設定を追加（Windows の priority class、POSIX の nice 値を抽象化）。
    - set_cpu_affinity でプロセスを最初の N コアに固定可能。権限不足や非対応環境では警告を出力してスキップ。
- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを起動フローに組み込み（冪等にテーブルを作成）。
- データ分析 / 検証ツール
  - tools.paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - システム安定性（稼働率）、注文成功率（fill/send rate）、リスク却下数、API レイテンシ（avg/max/P95）を集計して判定（PASS/FAIL）を出力。
    - P95 計算、期間フィルタ、閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）を実装。
- 研究用モジュール（開発中）
  - research.factor_research.py を追加（モメンタム・ボラティリティ等のファクター計算、DuckDB 経由で prices_daily/raw_financials を参照する設計）。（ファイルは部分実装）

### Changed
- 起動/監視の堅牢化
  - run_monitoring.py / run_execution.py: 起動時にプロセス優先度を最初に設定するようにし、例外発生時のログ出力と再試行/停止検出を行う実装で保守性を向上。
  - run_monitoring.py の MONITOR_POLL_INTERVAL の値検証を追加し、0 以下や不正な値の場合はデフォルトにフォールバックして警告を出す。
- DB ハンドリング
  - run_execution.py / run_monitoring.py: 終了処理で SQLite / DuckDB 接続を確実にクローズする finally ブロックを追加。
  - Paper Trading と本番の SQLite パスを Settings で抽象化し、起動時に適切な DB を選択するように変更（paper_trading は data/paper_trading.db をデフォルトで使用）。
- ログ設定
  - logging_setup: 既存ハンドラがある場合は一旦 flush/close してから再設定することで二重設定を防止。
  - StreamHandler を stdout に出力する方針を明確化（cron 等で stdout/stderr を一本化する運用を想定）。
- .env パーサーの改善
  - config._parse_env_line: クォート文字列内でのバックスラッシュエスケープ、インラインコメントの扱い、export プレフィックス対応などにより .env の多様な書式に耐性を持たせた。

### Fixed
- エッジケースの安全化
  - MONITOR_POLL_INTERVAL が不正値（非数・0・負数）の場合に time.sleep に渡して ValueError が発生するのを防ぐため、検証とフォールバックを実装。
  - process_priority.set_process_priority で権限不足や未実装 API による例外が発生した際にプロセスがクラッシュしないよう例外を捕捉して警告を出すように修正。
  - config_setup の .env 書き出しで必須項目とオプション項目を区別して取り扱う実装により、既存 .env が適切に保持されるようにした。
  - paper_verification_report: データが存在しない場合の sqlite3.OperationalError を捕捉してレポート生成を継続できるように改善。

### Documentation / Notes
- 各モジュールに詳細な docstring と使用例・設計意図を記載。PortfolioConstruction.md / StrategyModel.md などを参照する設計注記（ソース内コメント）。
- config_setup の .env に関して Git 管理しない旨を明記（生成ファイルを Git にコミットしないことの注意喚起）。

### Known issues / TODO
- research.factor_research.py は部分実装（calc_momentum の途中で切れている）。DuckDB を用いたファクター計算は今後の実装継続が必要。
- position_sizing の価格欠損時の扱い（price が 0.0 の場合のフォールバック価格）は TODO コメントあり。前日終値や取得原価によるフォールバック検討。
- 将来的な拡張: 銘柄ごとの lot_size を持つ設計（stocks マスタへの拡張）や per-symbol lot_map の導入。
- config/*.yaml の厳密なスキーマ検証は現時点では未実装（PyYAML によるパースのみ）。必要に応じてスキーマ検証を追加予定。

### Security
- 重要なシークレットは .env に保存する設計だが、config_setup にて「.env は絶対に Git にコミットしないこと」を明記。外部に公開されないよう運用上の注意を促している。

---

このリリースはソースから推測して作成した CHANGELOG です。実際の変更履歴やリリースノートに合わせて適宜更新してください。
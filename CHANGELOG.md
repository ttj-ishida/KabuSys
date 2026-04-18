# Change log

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: リリース日や記載内容はソースコードから推測して作成しています。

## [Unreleased]

- （今後の変更点をここに記載）

## [0.1.0] - 2026-04-18

初回公開リリース。システム全体の起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ユーティリティ、実行エンジン用ユーティリティ群、および Paper Trading 検証レポート生成ツールを含む。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
  - モジュール群のエクスポートを整理（kabusys.__all__）。

- 起動スクリプト / 実行管理
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用専用 SQLite（`data/paper_trading.db` / 環境変数 `PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と分離。
    - エンジンは別スレッドで実行し、プロジェクトルートの `data/stop_requested.flag` による停止検知、`data/execution.pid` への PID 書き込み（Engine 内で利用）に対応。
    - BrokerClientFactory を介してブローカークライアントを生成。RiskManager の初期ポートフォリオ値に broker.get_available_cash() を利用。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用の sqlite_path を利用（監視 DB の初期化を実行）。
    - 停止フラグ（project root/data/stop_requested.flag）を検知してループを終了。
    - KeyboardInterrupt に対する整った終了処理を実装。

- 設定 / 環境管理
  - config.py:
    - .env 自動ロード（プロジェクトルートを .git または pyproject.toml で検出）を実装。OS 環境変数は保護（既存変数は上書きされない）。
    - .env 行パーサーを実装（`export KEY=val`、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等をサポート）。
    - Settings クラスを提供し、必要な環境変数や各種パス・挙動をプロパティ経由で取得（入力検証を含む）。
    - Paper Trading 関連の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）を追加。
    - 監視・しきい値設定（CPU/MEMORY/DISK 閾値）・PID / Kill Flag の設定を追加。
    - KABUSYS_ENV, LOG_LEVEL 等の検証を実装（無効値は ValueError）。

  - config_setup.py:
    - 対話式ウィザードで .env を作成 / 更新する CLI を追加。
    - 秘密値（トークン等）をマスク表示、デフォルト・選択肢対応、書き込みテンプレートの生成を実装。
    - 保存前の確認プロンプトを実装。

  - validate_config.py:
    - 起動前チェック CLI を追加（必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス親ディレクトリの存在確認、config/*.yaml の存在と PyYAML によるパースチェック）。
    - `--strict` フラグで警告を失敗扱いにできる。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定未設定や Kill フラグ自動クリア設定の警告）を実装。
    - PyYAML 未インストール時には YAML 検証をスキップして警告を出す。

- ロギング / プロセス制御
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定する共通初期化関数 setup_logging() を追加。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみで継続する堅牢設計。
    - LOG_LEVEL / LOG_DIR / level 引数の優先順位処理を実装。

  - utils/process_priority.py:
    - プロセス優先度制御ユーティリティを追加（Windows と POSIX を吸収）。
    - set_process_priority(level) で Windows の priority class や POSIX の nice を設定。権限不足や未サポート OS に対しては警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を実装し、利用可能なコア数を超える場合や権限不足時に挙動を調整。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates(): BUY シグナルをスコア降順（同点は signal_rank でタイブレーク）で選択。
    - calc_equal_weights(): 等金額配分を計算。
    - calc_score_weights(): スコア加重配分を計算。全銘柄スコアが 0 の場合は等金額配分にフォールバック（WARNING 出力）。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap(): セクター集中制限。既存保有のセクター時価から上限超過セクターをブロックして候補をフィルタリング（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier(): market レジームに応じた投下資金乗数（"bull"=1.0、"neutral"=0.7、"bear"=0.3）。未知レジームは警告の上 1.0 にフォールバック。

  - portfolio/position_sizing.py:
    - calc_position_sizes(): allocation_method ("risk_based"/"equal"/"score") に基づく発注株数算出を実装。
    - 単元株 (lot_size)、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap とスケーリング処理を実装。
    - ストップロスやリスク割合に基づく risk_based 計算、価格欠損時のスキップ、端数処理（lot_size で丸め）を実装。
    - aggregate スケールダウン時に再配分のための fractional remainder 処理を実装。

- ツール / レポート
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成ツールを追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計してレポート出力。
    - パス/失敗判定基準（稼働率 ≥99%、注文成功率 ≥90%、送信率 ≥95%、P95 ≤200ms）を実装。
    - 日付フィルタ、P95 計算、DB 存在チェック、各テーブルが存在しない場合のフォールバック処理を実装。

- 解析 / リサーチ
  - research/factor_research.py:
    - ファクター計算モジュールの骨子を追加（モメンタム、Value、Volatility、Liquidity 等の設計方針と定数を定義）。
    - DuckDB を利用して prices_daily / raw_financials を参照する想定の実装開始（関数 calc_momentum の冒頭が追加されている）。※一部実装が継続中（コード末尾が途中で切れている）。

### Changed
- なし（初回リリースのため増分のみ）

### Fixed
- run_monitoring.py:
  - 環境変数 MONITOR_POLL_INTERVAL に不正な値が設定された場合に warning を出しデフォルト（60 秒）へフォールバックする挙動を追加して time.sleep に渡す際の ValueError を回避。

- config.py:
  - .env 自動ロード時に OS 環境変数を保護（protected set）することで、既存の環境変数が .env によって意図せず上書きされないようにした。

- logging_setup.py:
  - ログディレクトリ作成に失敗してもアプリケーションを停止させず、ファイルハンドラを設定しない形でフォールバックするように改善。

- process_priority.py:
  - 各プラットフォーム（Windows / POSIX / 未サポート）で例外発生時に警告を出して処理を継続する安全な実装へ修正。

### Security
- セキュリティ機能の初回追加: .env に秘密情報（トークン・パスワード）を含める運用を想定。config_setup の出力に「.env を絶対に Git にコミットしないこと」という注記を追加。

### Notes / Known issues
- research/factor_research.calc_momentum の実装が途中で切れている（ファイル末尾が未完）。完全なファクター計算実装は今後のコミットで追加予定。
- 一部モジュールは外部依存（psutil、duckdb、PyYAML など）に依存。validate_config は PyYAML 未導入時に YAML 検証をスキップするが、実行時の挙動に注意が必要。
- run_execution は BrokerClientFactory 等の下位コンポーネントに依存しており、外部ブローカーや MockBrokerClient の実装が必要。

---

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はコミット履歴やパッケージ差分を参照して調整してください。）
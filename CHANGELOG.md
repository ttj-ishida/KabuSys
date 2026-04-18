# Changelog

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成を追加。
  - パッケージバージョン: `__version__ = "0.1.0"`（src/kabusys/__init__.py）。

- 起動スクリプトを追加:
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（既定: data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag を監視し、停止時にエンジンを安全に停止。
    - 実行中 PID を data/execution.pid に管理（Engine に pid_file を渡す）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告の上でデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番用 `sqlite_path` を使用する設計。

- 設定管理とユーティリティ:
  - Settings クラス（src/kabusys/config.py）
    - 環境変数から各種設定を提供（DB パス、API キー、各種しきい値、環境種別判定など）。
    - 値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）と便利プロパティ（is_live / is_paper / is_dev）。
    - duckdb/sqlite 等のパスは Path オブジェクトで取得。
  - 自動 .env ロード機能
    - プロジェクトルートを .git または pyproject.toml から探索して自動的に `.env` と `.env.local` を読み込む（OS 環境変数を保護して上書き制御）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースはクォート、エスケープ、コメント（#）に対応する堅牢な実装。
  - config_setup.py（対話式ウィザード）
    - `.env` の初期作成・更新を対話式で支援。シークレット項目はマスク表示。書き込みテンプレートと説明を同梱。
    - デフォルト値や選択肢を提示して安全に .env を生成。
  - validate_config.py
    - 起動前の設定検証 CLI。必須環境変数や DB パス、config/*.yaml の存在・パース（PyYAML がインストールされている場合）をチェック。
    - `--strict` オプションで警告を失敗扱いにできる。
  - utils/logging_setup.py
    - 一貫したロギング設定ユーティリティを提供。
    - stdout (StreamHandler) と日次ローテーションのファイルハンドラ (TimedRotatingFileHandler) をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決ルールを定義（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。
    - Windows/Linux/その他 POSIX 対応を考慮し、権限不足や未対応環境では警告を出して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群: DB 参照なし）:
  - portfolio/portfolio_builder.py
    - シグナルの上位選定 select_candidates
    - 等金額配分 calc_equal_weights
    - スコア正規化配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）
  - portfolio/risk_adjustment.py
    - セクター集中上限適用 apply_sector_cap（既存ポジションのセクター別エクスポージャーを計算し上限を超えるセクターの新規候補を除外）
    - レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" に対応、未知レジームはフォールバック）
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を算出 calc_position_sizes（allocation_method: "risk_based" / "equal" / "score"）
    - 単元（lot_size）丸め、per-position および aggregate のキャップ、cost_buffer を考慮したスケールダウンと残差処理ロジックを実装

- Paper Trading 検証ツール（CLI）
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH または --db）から統計を集計し検証レポートを出力。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定する閾値を実装。
    - P95 計算、NULL/欠損データへの耐性、日付フィルタ（--from / --to）対応。

- Research: ファクター計算の基盤を追加
  - research/factor_research.py（モメンタム等のファクター計算基盤を整備、DuckDB 接続を受け取って prices_daily 等のテーブルから指標を算出する設計）

### Changed
- 監視・実行のデフォルト動作と DB の扱いを明確化:
  - 監視（monitoring）は環境にかかわらず本番用 SQLite を参照する設計（安全上の意図があるための明示）。
  - 実行（execution）は `paper_trading` 環境時に paper_trading 用 DB を使用して本番 DB と完全に分離。

- ログ出力周りを統一:
  - 全起動スクリプトは setup_logging を使って統一的にログを初期化するよう変更（app_name によるファイル名分離）。

### Fixed
- env ファイルのパースと読み込みの堅牢化:
  - export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応して .env の解析ミスを減らす実装に改良。

- プロセス制御の堅牢化:
  - 権限不足や未対応 OS での優先度 / affinity 設定失敗時に例外を吐かず警告ログを出すようにして起動の信頼性を向上。

### Security
- .env の取り扱いに注意喚起:
  - config_setup が生成する .env ファイルに「絶対に Git にコミットしないこと」との注意文を明記。

### Notes / Important behavior
- run_monitoring.py は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」点に注意してください（運用上の意図的設計）。
- MONITOR_POLL_INTERVAL の不正値（0 以下や文字列など）はワーニングを出してデフォルト 60 秒にフォールバックします。
- CPU 優先度／affinity の設定は実行環境の権限に依存するため、設定に失敗した場合は警告ログのみが出力され処理は継続されます。
- validate_config は PyYAML 未インストール時には YAML の内容検証をスキップし警告を出します。

---

今後のリリースでは、Strategy/Execution の詳細実装、単体テスト、CI 統合、ドキュメント（PortfolioConstruction.md, StrategyModel.md など）の整備および research/factor_research の完全実装を予定しています。
# Changelog

すべての注記は Keep a Changelog の形式に従います。重要: ここに記載した変更点は、与えられたコードベースの内容から推測してまとめたものです。

## [Unreleased]

### Added
- 実行用エントリスクリプトを追加 / 整備
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用する（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。プロセス優先度の設定、BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てとスレッド実行を行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル（data/stop_requested.flag）検出で安全に終了する。

- 設定管理・ウィザード・検証ツールを追加
  - config.py: 環境変数の読み込みと Settings クラスを実装。プロジェクトルートの検出（.git または pyproject.toml）を行い、自動で .env / .env.local を読み込む仕組みを実装。多くの設定プロパティ（DB パス、PID/kill flag、閾値、paper_fill_mode など）を提供。環境値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL 等）を組み込む。
  - config_setup.py: 対話式ウィザードで .env ファイルを初期作成・更新する CLI を追加。既存値の再利用、シークレットマスク表示、保存確認を実装。
  - validate_config.py: .env と config/*.yaml を起動前に検証する CLI を追加。必須/任意環境変数チェック、ファイルパスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML がない場合はスキップ）、本番環境向けの追加ガードを実装。--strict モードで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティを追加
  - utils/logging_setup.py: ルートロガーに対して統一的なログ設定を行うユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日時ローテーション・日次、30世代保持）を設定。LOG_DIR / LOG_LEVEL 環境変数や引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: cross-platform（Windows / POSIX）でプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity を設定する set_cpu_affinity も提供。アクセス権限や未実装ケースでは安全にフォールバックして警告を出す。

- ポートフォリオ構築 / サイズ決定 / リスク調整モジュールを追加
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全ゼロ時は等配分にフォールバック。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装（allocation_method: risk_based / equal / score）。単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に対するスケーリング、残差を用いた追加配分ロジックを持つ。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap（既存保有を考慮し、上限超過セクターの新規候補を除外）と市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。

- 解析・検証ツールを追加
  - tools/paper_verification_report.py: ペーパートレード SQLite DB を解析して検証レポートを出力する CLI を追加。システム稼働率（uptime）、注文成功率・送信率、リスク却下数、API レイテンシ（avg / max / P95）を集計し、閾値に基づいて PASS/FAIL を判定。日付レンジ指定（--from/--to）と DB パス指定（--db / 環境変数）に対応。

- DuckDB 統合
  - 複数のコンポーネントで duckdb 接続を受け取り分析・計算に利用する設計を採用（Settings.duckdb_path、各実行処理での duckdb.connect を使用）。

### Changed
- 設定読み込みの挙動
  - .env 読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパーサを改善し、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの処理に対応。

- DB 周りの分離と初期化
  - run_execution.py は paper_trading 環境時に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離するように変更。
  - 監視（monitoring）用の DB 初期化は init_monitoring_db を用いて冪等に保証。run_monitoring は環境にかかわらず本番 sqlite_path を使用する設計。

- ログ出力の取り扱い
  - ログはデフォルトで stdout に出力するようにし、ファイルハンドラは作成できる場合のみ追加（ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみで継続）。

- 実行プロセスの扱い
  - 実行中/監視中の停止制御をファイルフラグ（data/stop_requested.flag または data/kill.flag）で行う方式を採用し、安全にスレッド/ループを終了する挙動を追加。

### Fixed
- 設定検証の堅牢化
  - validate_config.py にて PyYAML が未インストールの場合は YAML 検証をスキップして警告を出すようにし、環境に応じたフォールバックを実装。
  - validate_config は必須環境変数のプレースホルダ検出（末尾が "_here" や "your_value"）を警告するようにした。

- エラー耐性の向上
  - run_monitoring のポーリングループで monitor.check_once() に失敗しても例外をキャッチしてログ出力し、次のポーリングで再試行するようにした（単一障害で監視が止まらない）。
  - process_priority / set_cpu_affinity は権限不足や未サポート環境時に例外で落ちないよう try/except で保護し、警告ログを残す。

- 数値計算の安全化
  - portfolio モジュールでゼロ除算・不正値のケースを安全に扱う（スコア合計が 0 の場合はフォールバック、price が 0/None の場合はスキップ等）。
  - paper_verification_report で P95 計算や集計の際、データなしのケースを None / "N/A" 表示にしてクラッシュを回避。

## [0.1.0] - 2026-04-19

（初回公開相当のリリースとして推定）
### Added
- プロジェクト基本構成の実装
  - パッケージ初期化（__version__ = "0.1.0"）
  - 基本ユーティリティ（logging_setup, process_priority）
  - 設定管理（config, config_setup, validate_config）
  - 実行ランチャー（run_execution, run_monitoring）
  - ポートフォリオ構築ライブラリ（portfolio/*）
  - ペーパートレード解析ツール（tools/paper_verification_report）
  - DuckDB / SQLite を利用した分析・監視基盤の枠組み

### Changed
- （なし: 初期リリース）

### Fixed
- （初期リリースのため特定の修正はなし）

---

注意事項:
- 上記はソースコードから読み取れる公開 API・挙動・CLI の説明と推定された変更点をまとめたものです。実際のコミット履歴や設計ドキュメントと差異がある可能性があります。リリースノートとして正式に残す場合は、実際の git コミットメッセージやリリース担当者の確認を推奨します。
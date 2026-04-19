# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。

現在のバージョン: 0.1.0 — 2026-04-19

## [0.1.0] - 2026-04-19

初回リリース。

### Added
- 基本アプリケーションパッケージ kabusys を追加
  - パッケージバージョン: `__version__ = "0.1.0"`

- 実行スクリプト / デーモン関連
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 停止フラグファイル（project/data/stop_requested.flag）を検知してグレースフルに終了。
    - Monitoring は環境 (`KABUSYS_ENV`) に依らず本番用の SQLite パスを使用。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の際はペーパートレード用の MockBrokerClient と専用 SQLite (`data/paper_trading.db` または環境変数で上書き可) を使用して本番 DB と分離。
    - 起動前に停止フラグを確認し、既に立っている場合は起動を中止。
    - 実行時に PID ファイルを書き込む仕組み（`data/execution.pid`）と停止フラグ検知で Engine を停止するループを備える。
    - スレッドで Engine をデーモン実行し、適切に join/停止処理を行う。

- 設定 / 環境読み込み
  - config.py
    - Settings クラスを追加し、環境変数から設定を取得する統一インタフェースを提供（J-Quants, kabuAPI, LINE, DB パス, 監視閾値, システムフラグ等）。
    - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env パースはクォート・エスケープ・コメントに対応。
    - `PAPER_FILL_MODE` のバリデーション（有効値: instant/partial/never/reject）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の有効値チェック（不正値は ValueError）。
    - `is_live`, `is_paper`, `is_dev` プロパティ。

  - config_setup.py
    - .env 初期作成・更新の対話式ウィザードを追加（`python -m kabusys.config_setup`）。
    - デフォルト項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を用意。
    - 既存 .env の読み込み・Enter で既存値再利用、シークレットのマスク表示、保存/キャンセルのフローを実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加（`python -m kabusys.validate_config`）。
    - 必須 / 任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および PyYAML があればパース検証を実施。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 本番時の注意喚起（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の危険性）を追加。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化関数 `setup_logging(app_name, log_dir, level)` を追加。
    - stdout への StreamHandler（stdout を利用）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler、デフォルト logs/<app_name>.log、30日保持）を設定。
    - 既存ハンドラのクリアやログディレクトリ作成失敗時のフォールバック処理を実装。
    - ログレベル / ログディレクトリの解決順を明示。

  - utils/process_priority.py
    - プロセス優先度設定 `set_process_priority(level)` を追加（Windows / POSIX を吸収）。
    - CPU affinity 設定 `set_cpu_affinity(cpu_count)` を追加。
    - 権限不足や未対応 OS 時には警告を出してスキップする安全な実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 `select_candidates`（スコア降順、signal_rank でタイブレーク）。
    - 等重配分 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコアが 0 の場合は等重へフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap`（既存保有比率が上限を超えるセクターの候補除外）。
    - レジーム乗数 `calc_regime_multiplier`（bull/neutral/bear に基づく乗数、未知レジームは警告して 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - 発注株数計算 `calc_position_sizes` を追加。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）、stop_loss_pct、risk_pct、max_position_pct、max_utilization、cost_buffer に基づく計算。
    - aggregate cap（利用可能現金を超える場合のスケールダウン）と lot_size 単位での再配分ロジックを実装。
    - 価格欠損時のスキップや上限の考慮など実運用向けの安全弁を実装。

  - portfolio/__init__.py
    - 上記関数群をトップレベルでエクスポート（使いやすい API を提供）。

- 研究 / ファクター計算
  - research/factor_research.py（部分実装）
    - モメンタム等のファクター計算の枠組みを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計）。
    - 1M/3M/6M リターン、200日移動平均乖離、ATR（20日）、出来高指標等を想定（関数雛形・定数を含む）。※ファイルは途中まで実装（以降の実装継続が想定される）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加（`python -m kabusys.tools.paper_verification_report`）。
    - ペーパートレード SQLite からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計して出力。
    - P95 計算、期間フィルタ（--from / --to）、DB パスの CLI オプション/環境変数対応を実装。
    - 判定基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL を出力。

### Changed
- n/a（初回リリースのため過去変更なし）

### Fixed
- n/a（初回リリースのため過去修正なし）

### Deprecated
- n/a

### Removed
- n/a

### Security
- n/a

注:
- 各起動スクリプトは起動時にプロセス優先度を 'high' に設定する処理を行います（set_process_priority）。
- 多くのモジュールは外部ライブラリ（psutil, duckdb, PyYAML 等）に依存します。環境に応じてインストールしてください。
- .env ファイルは機密情報を含むため、README 等で Git に含めないよう明記することを推奨します（config_setup でも警告を出力）。
- research/factor_research.py はモジュールの枠組み・定数・docstring を備えていますが、いくつかの計算ロジックが未完の可能性があります（今後の実装継続を想定）。

もしリリースノートに含めたい追加の強調点（例えば CLI の使い方や主要な環境変数一覧）があれば教えてください。必要に応じて CHANGELOG を拡張します。
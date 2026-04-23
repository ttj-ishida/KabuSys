# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のバージョンはパッケージの __version__ に合わせて 0.1.0 です。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-23

Added
- 全体
  - プロジェクト初期リリース。コア機能群（設定管理、起動スクリプト、ユーティリティ、ポートフォリオ構築、リサーチ、ペーパートレード検証ツールなど）を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60秒）。不正な値（0 以下や非整数）は警告を出してデフォルトにフォールバック。
    - 監視は、`KABUSYS_ENV` に依存せず常に本番用の `sqlite_path` を使用する設計。
    - 停止制御: プロジェクトルート配下 `data/stop_requested.flag` の存在を検知してループを終了。
    - ログ設定・プロセス優先度設定（High）を行う。
    - SQLite（監視 DB）と DuckDB の接続を確立して SystemMonitor を利用。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用 DB（`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`）を使用し、MockBroker を利用できる設計（BrokerClientFactory に依存）。
    - 起動時にプロセス優先度を High に設定。
    - 停止制御: `data/stop_requested.flag` を検知すると ExecutionEngine を停止。起動時に停止フラグが立っていれば起動せず終了。
    - PID 管理用のファイルパス（`data/execution.pid`）を利用。

- 設定管理
  - config.py
    - 環境変数読み込み・設定ラッパー (`Settings` クラス) を提供。
    - .env 自動ロード機能:
      - プロジェクトルートを `.git` または `pyproject.toml` から探索して特定（CWD に依存しない）。
      - 自動ロード順: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
      - .env のパースはクォート/エスケープとコメント（空白直前の `#` をコメントと判定）に対応。
    - 必須環境変数チェック用の `_require`、各種設定プロパティ（DB パス、PID ファイルパス、kill フラグ設定、閾値、ログレベル、環境種別判定など）を実装。
    - `paper_fill_mode` の検証（有効値: "instant" | "partial" | "never" | "reject"）を追加。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - デフォルト値、選択肢、シークレット入力対応、既存 .env 読み込み、保存確認、`.env` 生成テンプレート機能を実装。
    - 使用例: `python -m kabusys.config_setup`。

  - validate_config.py
    - 起動前チェック CLI を追加。`.env` と `config/*.yaml` の問題を起動前に検出。
    - デフォルトでエラーは exit(1)、`--strict` を指定すると警告も FAIL 扱いにできる。
    - チェック内容: 必須環境変数、KABUSYS_ENV 値、LOG_LEVEL、DB パスの親ディレクトリ、config/*.yaml の存在とパース（PyYAML が未インストールの場合はパース検査をスキップして警告）、本番用の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）等。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）を設定。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト "INFO"。
    - ログディレクトリ解決順: 引数 > 環境変数 `LOG_DIR` > デフォルト `logs/`。ディレクトリ作成失敗時はファイル書き込みをスキップしてコンソールのみ出力。
    - Cron/ジョブ実行を想定し stdout を使う設計。

  - utils/process_priority.py
    - psutil を使ったクロスプラットフォームのプロセス優先度設定ユーティリティを追加。
    - `set_process_priority(level)`（"high"/"normal"/"low"）と `set_cpu_affinity(cpu_count)` を提供。
    - Windows と POSIX（Linux, Darwin, FreeBSD）に対応し、未対応 OS やアクセス権限不足時は警告を出して処理をスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、同点は signal_rank でブレーク）を行う `select_candidates`。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコア 0 の場合は等配分にフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap` を実装。既存保有と当日売却予定を考慮して同一セクターの新規候補を除外。
    - レジーム乗数 `calc_regime_multiplier` を実装（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知は 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - 発注株数計算 `calc_position_sizes` を実装。
    - サポートする配分方式: "risk_based"（リスク許容率とストップロスで株数算出）、"equal" / "score"（weights を用いた算出）。
    - 1 銘柄上限、利用可能資金上限（aggregate cap）、単元株数（lot_size）丸め、手数料/スリッページの保守的見積り（cost_buffer）を考慮したスケーリングと端数処理を実装。

  - portfolio/__init__.py にて公開 API を整理（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

- リサーチ
  - research/factor_research.py（初期追加・未完）
    - DuckDB の `prices_daily` や `raw_financials` を使ったファクター計算モジュールの土台を追加。
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR）、流動性等の計算方針と定数を定義。関数 `calc_momentum` の実装開始（ファイル末尾で途中終了／未完の状態が含まれる）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト `data/paper_trading.db`）を解析し、検証レポートを生成する CLI を追加。
    - 期間指定により `system_status`, `trade_logs`, `risk_logs` から稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を取得して判定を行う。
    - 判定しきい値（デフォルト）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - SQL による集計と P95 算出ロジックを実装。DB 不在やテーブル欠損時の安全なフォールバックを備える。

- モジュール/デザイン注意点（ドキュメント）
  - run_monitoring と run_execution は起動時にプロセス優先度を高く設定するため、権限不足で失敗した場合はログに警告を出して続行する設計。
  - 監視と実行は DB の切り分けを明確化（監視は常に監視 DB、実行は paper_trading 環境で専用 DB を使用）。
  - .env の自動ロードは OS 環境変数を優先し、.env.local で上書き可能。テスト目的などで自動ロードを無効化できるフラグを提供。
  - 一部モジュール（research/factor_research.py）が未完であり、今後の実装・検証が必要。

Fixed
- なし（初期リリース）

Changed
- なし（初期リリース）

Removed
- なし（初期リリース）

Security
- なし

Notes / Upgrade
- 初期リリース。導入手順:
  1. .env を作成する（`python -m kabusys.config_setup` を推奨）。
  2. `python -m kabusys.validate_config` で設定検証を実行。
  3. 監視/実行スクリプトを起動（`python -m kabusys.run_monitoring` / `python -m kabusys.run_execution`）。
- 本番運用前に `KABUSYS_ENV`、LINE 通知設定、KILL フラグの挙動等を十分に確認してください（validate_config の警告を参照）。
- research モジュールは未完の関数が存在するため、本番利用には追加実装・テストが必要です。
CHANGELOG
=========

このファイルは「Keep a Changelog」仕様に準拠しています。
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

全般の注意
----------
- 日付は変更履歴作成時点を使用しています。
- ここに記載した内容は、ソースコード（src/ 以下）から推測した機能追加・振る舞いの要約です。

Unreleased
----------
（未リリースの変更はここに記載）

0.1.0 - 2026-04-19
------------------
Added
- 基盤機能
  - パッケージ初期リリース。モジュール構成を提供。
  - バージョン設定: __version__ = "0.1.0"。

- 実行エントリ / プロセス管理
  - run_execution.py
    - ExecutionEngine を起動するエントリスクリプトを追加。
    - プロセス優先度を最初に "high" に設定（utils.process_priority.set_process_priority を使用）。
    - KABUSYS_ENV=paper_trading の際は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を利用し、本番 DB から分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - エンジンは別スレッドで daemon 実行、stop フラグ（data/stop_requested.flag）検知時に安全停止処理を実行。
    - PID ファイルを data/execution.pid に書き込む仕組み（設定で上書き可能）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告ログ出力後にデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path（デフォルト: data/monitoring.db）を使用する（monitoring 用 DB 初期化を行う）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを抜ける。

- 設定管理
  - config.py
    - Settings クラスによる環境変数ラッパーを提供（各種設定の取得とバリデーション）。
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。.env, .env.local の順に読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 環境変数の必須チェック機能（_require）や enum チェック（KABUSYS_ENV, LOG_LEVEL 等）を実装。
    - Paper Trading 関連設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）、監視閾値（CPU/MEM/DISK）などを含む。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を提供（python -m kabusys.config_setup）。
    - 入力補助、既存 .env 読み込み、シークレットのマスク表示、保存確認などを実装。

  - validate_config.py
    - 起動前検証 CLI（python -m kabusys.validate_config）を追加。
    - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パスの親ディレクトリ存在、config/*.yaml の存在とパース（PyYAML があれば）をチェック。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング / プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を実装。
    - stdout への StreamHandler（stdout を使用）と日次ローテーション（TimedRotatingFileHandler）によるファイル出力（logs/<app_name>.log）を設定。
    - LOG_DIR 環境変数や引数でログディレクトリを指定可能。ファイル出力に失敗してもコンソール出力は継続。
    - 既存のハンドラをクリアして重複出力を防止。

  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定するユーティリティを追加。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足等で失敗した場合は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - calc_score_weights は全スコアが 0 の場合に等配分へフォールバックし警告ログ。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存ポジションからセクター別時価を算出して上限超過セクターの新規候補を除外）。
    - レジームに応じた投資乗数 calc_regime_multiplier を実装（bull/neutral/bear → 1.0/0.7/0.3。未知のレジームは 1.0 にフォールバックして警告）。

  - portfolio/position_sizing.py
    - position sizing（各銘柄の発注株数算出）を実装。allocation_method に "risk_based", "equal", "score" をサポート。
    - lot_size（単元株）に基づく丸め、per-position 上限や aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ想定）の考慮、端数の再配分アルゴリズムを実装。
    - 価格やデータ欠損時のスキップやログ出力を実装。

- 監視・モニタリング
  - monitoring モジュール（run_monitoring から利用）用の DB 初期化（monitoring_db.init_monitoring_db）を呼び出して監視テーブルの存在を保証。
  - SystemMonitor を使って定期チェックを行う設計。

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加（python -m kabusys.tools.paper_verification_report）。
    - SQLite（デフォルト: data/paper_trading.db）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（AVG, MAX, P95）を集計してレポート出力。
    - パス/フェイル閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）と判定ロジックを実装。
    - --from/--to/--db オプションをサポート。

- リサーチ（ファクター研究）
  - research/factor_research.py
    - DuckDB 接続を用いたモメンタム / ボラティリティ / バリュー等のファクター計算モジュールを追加（設計と定数を実装）。
    - calc_momentum 等を実装予定（ファイル末尾で関数の実装開始を確認、実装は継続中の可能性あり）。

Notes / 重要な挙動
- データベース分離
  - 本番監視 DB（monitoring.db）と Paper Trading DB（paper_trading.db）は明確に分離される設計。Execution は KABUSYS_ENV により paper_sqlite_path を使い分ける。
  - Monitoring は「環境にかかわらず」設定された sqlite_path（デフォルト monitoring.db）を使用する旨の注記あり。

- 停止制御
  - 停止フラグ（data/stop_requested.flag）を監視してスクリプト・エンジンを安全に停止する仕組みが導入。
  - Kill Switch（KILL_FLAG_*）や PID ファイル周りの設定がある（Settings.kill_flag_path, pid_file_path, KILL_FLAG_CLEAR_ON_START）。

- 環境変数自動読み込み
  - .env/.env.local の自動読み込みはデフォルトで有効。CI / テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用。

- ログ運用
  - stdout に出力する仕様（cron 等で stdout/stderr をリダイレクトする運用を想定）。
  - 日次ログローテーション（30 日保持）をファイルに行うが、ログディレクトリ作成に失敗するとファイルハンドラはスキップしてコンソールのみ有効にする耐障害性あり。

- フォールバック / エラーハンドリング
  - MONITOR_POLL_INTERVAL の不正値や PAPER_FILL_MODE の不正値等は安全にフォールバックまたは例外を出す（適切なログ・エラーメッセージを出力）。
  - process_priority / cpu_affinity 設定は権限不足や未対応 OS で失敗しても警告を出して処理を継続。

Known limitations / TODO（ソースコメントより）
- sector_exposure 計算で price が欠損（0.0）の場合に過少見積りとなる可能性があり、前日終値や取得原価のフォールバックを検討中。
- position_sizing の lot_size は現状全銘柄共通で固定。将来的には銘柄別単元情報をサポート予定。
- research/factor_research の関数実装が途中で切れている部分がある（継続実装の可能性あり）。

Fixed
- （該当なし — 初回リリース）

Changed
- （該当なし — 初回リリース）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- （該当なし）

付録: 主なデフォルト値（おもな環境変数と既定値）
- KABUSYS_ENV: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- MONITOR_POLL_INTERVAL: 60（秒）
- PAPER_FILL_MODE: instant
- ログディレクトリ: logs/

もし特定モジュールごとの詳細変更履歴（例: portfolio/position_sizing のアルゴリズム差分や CLI の出力例）を、より細かく記載したい場合は対象ファイル・関数を指定してください。
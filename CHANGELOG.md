# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

読み方の注意:
- 日付はリリース日です（YYYY-MM-DD）。
- 記載内容はコードベースから推測して記述しています。実装上の挙動や環境変数の意味などを含みます。

## [Unreleased]
- なし（次回リリースに向けた未反映の変更はありません）

## [0.1.0] - 2026-04-23

### Added
- 実行用スクリプトを追加/整備
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。プロセス優先度設定、DB 接続、ブローカークライアント生成、OrderManager / RiskManager / Reconciler の組立てとエンジン起動を行う。
    - KABUSYS_ENV=paper_trading のときは paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離する設計。
    - 停止フラグ（data/stop_requested.flag）検知で安全にエンジンを停止する仕組みを実装。実行 PID 管理（data/execution.pid）に対応。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視用 DB の初期化と duckdb 接続を行い、停止フラグ検知でループを終了する。

- 設定管理・ユーティリティ
  - config.py
    - Settings クラスを導入し、環境変数をラップして提供。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH などのパスプロパティ、PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の妥当性チェックなどを提供。
    - プロジェクトルート自動検出機能を追加し、.env / .env.local の自動ロード（OS 環境変数保護あり）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加。デフォルト値、選択肢、シークレットマスク表示、保存確認などを提供。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML パース（PyYAML が存在するとき）や本番向けガードチェックを行う。
    - --strict フラグで警告も失敗扱いにできる。
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。stdout に StreamHandler を出力し、日次ローテーション（TimedRotatingFileHandler）で logs/<app_name>.log を保存。ログレベル・ログディレクトリの解決順序を定義。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみで継続するフォールバックを実装。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加。Windows/Linux/macOS に対応し、失敗時は警告を出してスキップする。
    - CPU affinity を設定する set_cpu_affinity も提供。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナルから候補選定（select_candidates）と等配分・スコア加重（calc_equal_weights / calc_score_weights）を実装。スコア全0時は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームは警告を出してフォールバック。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、1銘柄上限・集計上限（available_cash）対応、コストバッファ考慮、スケーリング時の端数配分ロジックを実装。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を元に稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、閾値による PASS/FAIL を判定するレポート生成スクリプトを追加。
    - P95 計算、日付フィルタ、各種 SQL クエリと安全なエラー処理を実装。

- パッケージ基礎
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- ログ出力の一貫化
  - すべての起動スクリプトやユーティリティから setup_logging() を呼び出すことで、コンソールとファイルの出力設定を統一。
  - StreamHandler は stdout に出力するように統一（cron 等の処理で stdout/stderr をまとめて扱いやすくするため）。

- 起動時のプロセス優先度
  - 実行系スクリプト（monitoring / execution）で起動直後に set_process_priority("high") を実行し、重要プロセスの優先度を上げる挙動に変更。

- .env 自動読み込みの挙動
  - プロジェクトルート（.git または pyproject.toml を基準）を基に .env を自動ロード。OS 環境変数（既存値）は保護される（.env.local は上書き可能だが OS 変数は保護）。

- DB 接続方針
  - 監視（run_monitoring）は KABUSYS_ENV にかかわらず監視用の本番 sqlite_path を使用するように明示（監視データは本番 DB を想定）。
  - 実行（run_execution）は paper_trading 環境では paper 用 SQLite を使用し、本番 DB と分離。

### Fixed / Robustness improvements
- 環境変数パースの強化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート値のエスケープ処理、インラインコメント処理（非クォート時は直前が空白ならコメントと判断）を実装し、.env の柔軟な記述に耐えるようにした。
  - _load_env_file: ファイル読み込み失敗時に警告を発するよう改善。

- 不正値に対するフォールバック / 警告処理
  - MONITOR_POLL_INTERVAL が不正（非整数/ゼロ/負）な場合、警告を出してデフォルト 60 秒にフォールバック。
  - PAPER_FILL_MODE の無効値は ValueError を投げて早期検出。
  - calc_score_weights: 全銘柄のスコアが 0.0 の場合は等金額配分にフォールバックして警告ログ出力。
  - logging_setup: ログディレクトリ作成失敗時はファイルハンドラ生成をスキップして標準出力のみ継続。ファイルハンドラ生成失敗時も警告ログを出す。

- CLI エラー/例外安全性
  - validate_config.py / paper_verification_report.py 等で SQLite のテーブルが存在しない場合に OperationalError をキャッチしてデフォルト値で処理を継続するようにした（未データ環境でもツールが壊れない）。

### Security
- 環境変数取り扱いの注意喚起
  - config_setup.py において .env は絶対に Git にコミットしない旨のコメントを明記。シークレット項目は表示時にマスク。

### Notes / Implementation details（要点）
- 停止フラグはプロジェクトの data/stop_requested.flag を用いる設計。起動済みプロセスは定期的にこのファイルの存在を確認して安全に終了できる。
- PID ファイルのパスは Settings.pid_file_path（デフォルト data/execution.pid）で管理され、ExecutionEngine に渡される。
- RiskManager の初期設定（例: max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）は run_execution.py 側で構成可能なデフォルト値を与えている。
- portfolio の position sizing は単元株・コスト・集計上限を考慮したスケールダウンおよび端数配分のロジックを含むため、資金不足時でも再現性のある分配を行う仕様。

---

過去リリースはありません（初版: 0.1.0）。追加で知りたい点（例えば各モジュールの使い方例や環境変数一覧・推奨設定、アップグレード手順など）があれば、CHANGELOG に追記する形で詳述します。
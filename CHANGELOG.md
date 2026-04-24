# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
注: 以下の変更内容は提供されたコードベースの内容から推測してまとめたもので、実際のコミット履歴ではありません。

## [Unreleased]

### Added
- 監視・実行の起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを提供。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能。停止フラグファイル（data/stop_requested.flag）検知で安全に終了する。
  - run_execution.py: ExecutionEngine を起動するエントリポイントを提供。KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite を使用し、本番 DB と分離する。
- 設定関連の CLI / ユーティリティを追加
  - config_setup.py: 対話式ウィザードで `.env` を初期作成・更新するツール。シークレット項目のマスク表示、既存値の再利用、保存確認をサポート。
  - validate_config.py: `.env` と config/*.yaml の設定検証 CLI。必須環境変数チェック、パス存在警告、YAML のパース検証、`--strict` による警告を FAIL 扱いにするオプションを提供。
- 環境変数読み込み改善
  - config.py: プロジェクトルート（.git または pyproject.toml）を自動検出して `.env` / `.env.local` を読み込み。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。`.env` のパースは quoted 値、export プレフィックス、インラインコメントなどに対応。
  - Settings クラスを実装し、アプリ設定値（パス、閾値、環境判定、Paper Trading 用設定など）をプロパティで取得可能に。
- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: stdout への StreamHandler と 日次ローテーションする TimedRotatingFileHandler をルートロガーに設定するユーティリティ。ログディレクトリ作成失敗時はファイル出力をスキップ。ログレベルは引数→環境変数→デフォルトの優先で解決。
  - utils/process_priority.py: psutil を使ったプロセス優先度設定（Windows / POSIX を抽象化）。CPU affinity を最初 N コアにピン留めする機能も提供。権限不足時や未サポート環境は警告を出して安全にスキップ。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py: Paper Trading の SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出し、PASS/FAIL 判定を出すレポート生成スクリプト。コマンドライン引数で期間・DB パスを指定可能。デフォルト閾値を導入（稼働率 99% など）。
- Portfolio 構築 / リスク制御 / ポジションサイジングの純粋関数群を追加
  - portfolio/portfolio_builder.py: シグナルの候補選定（スコア降順、タイブレークルール）と等金額・スコア加重の重み計算。スコア合計が 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（既存保有からセクター別エクスポージャ計算して候補を除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear）を返すユーティリティ。
  - portfolio/position_sizing.py: 重みや候補、ポートフォリオ価値・利用可能現金を元に銘柄ごとの発注株数を算出。risk_based / equal / score の配分方式をサポートし、単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金超過時のスケーリング）、手数料/スリッページの保守的見積り（cost_buffer）を考慮。
- DuckDB と SQLite の連携
  - 各起動スクリプトで DuckDB 接続を生成（Settings.duckdb_path）。監視用の SQLite テーブル（init_monitoring_db）を起動時に冪等的に初期化して保証。

### Changed
- 実行環境の挙動の明確化
  - 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様を明示（運用上の意図）。
  - 実行（run_execution）は paper_trading 環境時に paper_sqlite_path を使用して本番データと完全分離。
- ログ出力の標準化
  - すべての起動スクリプトで setup_logging(app_name=...) を呼び出すことでログ管理を統一。
  - コンソール出力は stdout を使用（cron 等でのリダイレクトを想定）。

### Fixed
- 環境変数パース時の細かな不具合に対応
  - クォート内のバックスラッシュエスケープや、クォートなしでのインラインコメント判定（'#' の直前が空白/タブの場合のみコメントとみなす）に対応し、.env の柔軟な記述を許容。
- プロセス優先度設定の失敗時にスローされる例外をキャッチして起動継続するように変更（権限不足や未実装のケース）。

---

## [0.1.0] - 2026-04-24

初回リリース相当 — 基本機能の実装

### Added
- プロジェクトのバージョンを定義（kabusys.__version__ = "0.1.0"）。
- 基本的なモジュール群を実装:
  - 設定管理: kabusys.config (Settings, 自動 .env ロード)
  - 起動スクリプト: run_execution.py, run_monitoring.py
  - 設定関連 CLI: config_setup.py, validate_config.py
  - ユーティリティ: utils/logging_setup.py, utils/process_priority.py
  - ポートフォリオ構築: portfolio/portfolio_builder.py, portfolio/risk_adjustment.py, portfolio/position_sizing.py
  - Paper Trading レポート: tools/paper_verification_report.py
  - research/factor_research.py の土台（ファクター計算ロジックの骨格、DuckDB 接続想定）
- DB 初期化ユーティリティ（monitoring_db.init_monitoring_db を利用する呼び出しポイント）を各スクリプトで呼ぶことでテーブル整備を自動化。

### Changed
- 起動時にプロセス優先度を高（"high"）に設定するフローを追加（実行・監視ともに最初に呼ぶ）。
- ログファイルのローテーション（30日保持）を導入。

### Fixed
- 起動時の停止フラグ検知（data/stop_requested.flag など）により、デーモン的に実行するコンポーネントを安全に停止できる仕組みを導入。

---

記載した内容はソースコードの構成・コメント・関数シグネチャから推測してまとめた変更履歴です。実際のコミットメッセージや日付を用いた厳密な履歴が必要な場合は、Git のログやリポジトリのコミット情報を提供してください。
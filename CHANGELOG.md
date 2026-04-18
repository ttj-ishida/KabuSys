# Changelog

すべての notable な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお本リリースはコードベースから推測して作成した初回公開相当のまとめです。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。
- 実行スクリプト
  - `run_execution.py`
    - ExecutionEngine を起動する CLI スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）へ記録して本番 DB と分離する挙動をサポート。
    - プロセス優先度を起動直後に "high" に設定する処理を追加。
    - 停止制御用のフラグファイル（data/stop_requested.flag）検知と PID ファイル出力（data/execution.pid）に対応。
    - ExecutionEngine をデーモンスレッドで起動し、停止フラグを検知したら安全に停止するループを実装。
    - RiskManager、OrderManager、Reconciler、OrderRepository 等の組み立て処理とデフォルトリスク設定（max_position_pct 等）を導入。`initial_portfolio_value` をブローカーの利用可能現金から初期化。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用の `sqlite_path` を使用する旨を明記（運用方針）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了し、各 DB 接続を確実にクローズする。
- 設定管理
  - `config.py`
    - .env の自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）を導入。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパースを堅牢化（コメント、export prefix、シングル/ダブルクォート内のエスケープ、インラインコメント処理などを考慮）。
    - 設定アクセス用 `Settings` クラスを導入。J-Quants、kabu API、LINE、DB パス、監視閾値、環境種別（development/paper_trading/live）などをプロパティとして提供。
    - `PAPER_FILL_MODE` のバリデーションを追加（有効値: "instant", "partial", "never", "reject"）。
    - Paper Trading 用 DB パス（`paper_sqlite_path`）や各種閾値プロパティを提供。
- 設定支援 CLI
  - `config_setup.py`
    - 対話式ウィザードで `.env` を初期作成/更新するツールを実装。
    - J-Quants、kabu API、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等の主要項目を対話的に編集できる。
    - 既存 .env の読み込み・マスク表示・デフォルト利用・保存確認の仕組みを実装。
- 設定検証 CLI
  - `validate_config.py`
    - `.env` と `config/*.yaml` の起動前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば内容検証）などを実行。
    - `--strict` オプションで警告を失敗扱いにできる。
- ロギング/プロセスユーティリティ
  - `utils/logging_setup.py`
    - すべての起動スクリプトで共通利用できるログ設定ユーティリティを追加。
    - stdout 出力（StreamHandler）と日次ローテーションファイル出力（TimedRotatingFileHandler, 30 日保持）をルートロガーに設定。ログディレクトリ生成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル決定の優先順（引数 > 環境変数 > デフォルト）をサポート。
  - `utils/process_priority.py`
    - プラットフォーム非依存のプロセス優先度設定ユーティリティを追加（Windows / POSIX に対応）。
    - `set_cpu_affinity` により先頭 N コアへのピン留めを行う関数を提供（存在しない場合は警告を出してスキップ）。
- ポートフォリオ構築モジュール
  - `portfolio/portfolio_builder.py`
    - シグナル選択（score 降順・signal_rank タイブレーク）`select_candidates` を実装。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights` を実装。全スコアが 0 の場合は等金額にフォールバックして警告を出す。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限を適用する `apply_sector_cap` を実装（sell_codes を考慮、"unknown" セクターは除外しない）。
    - 市場レジームに応じた乗数 `calc_regime_multiplier` を実装（"bull":1.0、"neutral":0.7、"bear":0.3、未知は 1.0 フォールバックで警告）。
  - `portfolio/position_sizing.py`
    - 各銘柄の発注株数を算出する `calc_position_sizes` を実装。
    - 複数 allocation_method をサポート（"risk_based", "equal", "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に応じたスケーリング、スケール後の端数を残差に基づき優先配分するロジックを追加。
    - 価格欠損や price <= 0 の銘柄はスキップしてログに記録。
- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI を実装。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを算出し、閾値に基づく PASS/FAIL 判定を出力（閾値はソース内定義: uptime 99%、fill 90%、send 95%、P95 200ms）。
    - 日付フィルタ（--from / --to）および DB パス指定（--db）をサポート。テーブル欠損時は安全に N/A を返す実装。
- 研究モジュールの骨組み
  - `research/factor_research.py`
    - Momentum、Value、Volatility、Liquidity 等のファクター計算設計とパラメータ定義を追加（DuckDB を使用、prices_daily/raw_financials を参照する想定）。一部実装は継続中。

### Changed
- 環境自動読み込みの挙動
  - プロジェクトルートの検出を .git / pyproject.toml に基づいて行うことで、CWD に依存せずに配布後も自動ロードが機能するように設計。
  - OS 環境変数は protected として `.env.local` の上書きから保護する実装に。
- ログ出力の方針
  - コンソール出力は stdout を使用することで、cron 等の出力リダイレクト運用に配慮。

### Fixed
- .env パーサの堅牢化
  - export プレフィックス、クォート内のエスケープ、インラインコメント処理などのケースを正しく処理するよう改善。
- 各種起動スクリプトでのリソースクリーンアップ
  - 例外や KeyboardInterrupt 発生時に SQLite/DuckDB コネクションを確実にクローズするように修正。

### Notes
- Monitoring（SystemMonitor）は「環境にかかわらず本番 sqlite_path を使用する」という運用方針がコード内ドキュメントに明記されています。運用時に意図しない DB に書き込まれないよう注意してください。
- `PAPER_FILL_MODE` や `KABUSYS_ENV` 等は厳密なバリデーションを行うため、`.env` に不正な値を放置すると起動時に例外が発生します。`python -m kabusys.validate_config` による事前チェックを推奨します。
- ログディレクトリ作成やプロセス優先度設定は権限等の理由で失敗する可能性があります。その場合は警告ログを出してフォールバックします。

---

（今後の変更やバグ修正はこのファイルに追記してください）
# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-21
初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理および検証ツールを追加。

### Added
- 全体
  - パッケージ初回導入。バージョンを `__version__ = "0.1.0"` として公開。
- 設定関連
  - Settings クラス（kabusys.config）を追加。環境変数から各種設定を取得する統一インターフェースを提供。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
- 設定操作 CLI
  - 対話式設定ウィザード（kabusys.config_setup）を追加。`.env` の初期作成・更新を支援するウィザードを提供。
  - 設定検証ツール（kabusys.validate_config）を追加。必須環境変数、パス、YAML 設定ファイルの存在・パース検証、KABUSYS_ENV による本番ガードなどを行う。`--strict` による警告を失敗扱いにするオプションあり。
- 起動スクリプト / デーモン化補助
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（`PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - BrokerClientFactory 経由のブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）検出で安全に停止。
    - 実行用 PID ファイルのパス管理（`data/execution.pid` 等）。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用して sqlite に接続し、duckdb も接続。
    - 停止フラグ検知（data/stop_requested.flag）でループ終了。
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を追加。
    - 稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を SQLite の履歴から集計し、PASS/FAIL 判定（閾値をコード内に定義）を出力。
    - `--from` / `--to` / `--db` オプションをサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` も利用可能。
- ログ・プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティ（kabusys.utils.logging_setup）を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログディレクトリ自動作成や作成失敗時のフォールバックを実装。ログレベルの決定順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）を追加。
    - Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定する `set_process_priority` を提供。アクセス権限による失敗は警告でスキップ。
    - `set_cpu_affinity` によるプロセスのコア固定機能を追加。
- ポートフォリオ構築（純粋関数）
  - portfolio モジュールを追加（DB 参照なしでメモリ内計算）。
  - 候補選定: select_candidates（スコア降順、同点は signal_rank で tiebreak）。
  - ウェイト計算: calc_equal_weights、calc_score_weights（全スコアが 0 の場合は等金額にフォールバックして警告）。
  - セクター集中制限: apply_sector_cap（既存保有をもとに上限超過セクターの新規候補排除）。"unknown" セクターは制限対象外。
  - レジーム乗数: calc_regime_multiplier（bull/neutral/bear に対応。未知値は警告の上 1.0 でフォールバック）。
  - ポジションサイズ計算: calc_position_sizes
    - 複数の配分方式をサポート: "risk_based", "equal", "score"。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate 上限（available_cash）を考慮。
    - cost_buffer を加味した保守的な費用見積り、必要に応じてスケールダウンし残差分は lot 単位で再配分するロジックを実装。
- リサーチ / ファクター計算（下書き）
  - factor_research モジュールを追加（duckdb 接続を受け取り prices_daily / raw_financials を参照して各種ファクターを計算する方針を実装）。
  - モメンタムファクター calc_momentum の枠組み（1M/3M/6M リターン、MA200 乖離率など）を追加（実装継続中の箇所あり）。
- DB 初期化ヘルパー
  - monitoring 用テーブルの冪等初期化関数 init_monitoring_db を各起動スクリプトから呼び出すことで監視テーブル存在を保証。

### Changed
- なし（初回リリースのため変更履歴はありません）。

### Fixed
- なし（初回リリース）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- なし。

注記
- Paper Trading（ペーパートレード）と本番（live）DB は意図的に分離されています。paper_trading モードでは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用します。
- 一部モジュール（例: factor_research）の実装は継続中の部分があり、今後のリリースで拡張・完成予定です。
- 環境変数の取り扱いやファイル生成（.env、logs ディレクトリ等）は安全上の注意（.env を Git にコミットしない等）を README や起動手順に従ってください。
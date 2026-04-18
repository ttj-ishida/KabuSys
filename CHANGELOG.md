# Changelog

すべての後方互換性のある変更は、Keep a Changelog の形式に従って記載します。  
日付はリリース日です。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 基本アプリケーションの初期実装を追加しました。
  - バージョン: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル: `data/stop_requested.flag` を監視してループを終了。
    - Monitoring は環境（KABUSYS_ENV）に関わらず本番の `sqlite_path` を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient（BrokerClientFactory 経由）を利用し、Paper Trading 用 DB（`data/paper_trading.db` デフォルト）を使用して本番 DB と完全に分離。
    - 停止フラグ: `data/stop_requested.flag`、PID ファイル: `data/execution.pid` を扱う。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - 環境変数・設定取得用 `Settings` クラスを実装。
    - `.env` / `.env.local` の自動読み込み（プロジェクトルートが見つかった場合）。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` のパーシングは `export KEY=val` 形式、クォート、インラインコメント等に対応。
    - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / PID/kill flag / 監視閾値 / 環境判別など）。
    - `paper_fill_mode`（PAPER_FILL_MODE）を導入。許容値: `"instant" | "partial" | "never" | "reject"`。不正値は ValueError。
    - `paper_sqlite_path`（PAPER_TRADING_SQLITE_PATH）で Paper Trading 用 DB を指定可能。

- 設定補助 CLI
  - config_setup.py
    - 対話式ウィザードで `.env` ファイルを初期作成・更新する CLI を追加。
    - J-Quants / kabu API などの必須項目を対話的に設定可能。シークレットはマスクして表示。
    - `.env` の書き出しテンプレートを実装（Git にコミットしない旨を明記）。

  - validate_config.py
    - 起動前に `.env` や `config/*.yaml` の不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、YAML ファイルの存在とパースチェック（PyYAML が存在する場合）などを検証。
    - `--strict` オプションにより警告を失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用するログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日分保持）のファイル出力をルートロガーに設定。
    - `LOG_DIR` / `LOG_LEVEL` 環境変数や引数での上書きに対応。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - 出力は stdout（stderr ではない）に統一。

  - utils/process_priority.py
    - プロセス優先度（Windows の priority class / POSIX の nice）および CPU affinity 設定ユーティリティを追加。
    - `set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(cpu_count)` を提供。
    - サポート外 OS やパーミッション不足でも安全にフォールバックして警告を出す。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）と重み算出（calc_equal_weights, calc_score_weights）を追加。
    - calc_score_weights は全スコアが 0 の場合、等分配にフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap を追加（売却予定銘柄の除外、"unknown" セクターの扱いなど）。
    - レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear）。

  - portfolio/position_sizing.py
    - 発注株数決定ロジック calc_position_sizes を実装。
    - allocation_method: "risk_based" / "equal" / "score" に対応。
    - lot_size（単元）考慮、max_position_pct、max_utilization、cost_buffer を扱った aggregate cap のスケーリングと端数処理を実装。
    - 現状デフォルト lot_size=100 を想定（将来的に銘柄別拡張予定）。

  - portfolio/__init__.py で主要関数をエクスポート。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - デフォルト DB: `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` 環境変数または --db オプションで上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を計算。
    - 閾値に基づく PASS/FAIL 判定を行う（デフォルト閾値をスクリプト内で定義）。
    - CLI 引数: `--from`, `--to`, `--db`。

- 調査用ファクター計算（初期スケルトン）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（momentum 等の定数、calc_momentum の関数定義開始）。
    - DuckDB での prices_daily / raw_financials 参照を想定した設計。

### 変更 (Changed)
- ログとプロセスの初期化順序設計
  - 起動スクリプトは最初に logging をセットアップし、その直後にプロセス優先度を "high" に設定する標準的な起動フローを採用。

- データベース接続方針
  - Monitoring（run_monitoring）は環境に関わらず `Settings.sqlite_path`（本番監視 DB）を使用する仕様に決定。Paper Trading の分離は Execution 側で行う（`paper_sqlite_path` を使用）。

### 修正 (Fixed)
- .env パーサの堅牢性向上
  - export 句、クォート、バックスラッシュエスケープ、インラインコメントの扱いなどを詳細に実装し、.env 読み込み時の誤判定を低減。

### 注意点 (Notes)
- 破壊的変更 / 想定外の挙動
  - run_monitoring は設計上、KABUSYS_ENV に関係なく本番の sqlite_path を使います。ローカル開発で監視用 DB を分離したい場合は Settings.sqlite_path を上書きするか、環境変数で `SQLITE_PATH` を明示的に指定してください。
  - PAPER_FILL_MODE に不正な値を設定すると起動時に ValueError が発生します。許容値は "instant", "partial", "never", "reject" です。
  - `.env` ファイルは機密情報を含むため絶対にリポジトリにコミットしないでください。config_setup のヘッダにも同様の注意を記載しています。

- 実行コマンド例
  - 監視ループ起動:
    - python -m kabusys.run_monitoring
  - エンジン起動:
    - python -m kabusys.run_execution
  - 設定ウィザード:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config [--strict]
  - Paper 検証レポート:
    - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

- 環境変数の自動ロード
  - デフォルトでプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動的に読み込みます。OS 環境変数は上書きされません（保護）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- ログ出力
  - stdout とファイル（logs/<app_name>.log）に出力します。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続します。

### 既知の制限 / TODO
- portfolio.position_sizing の lot_size は現状グローバルで固定（100）。将来的に銘柄別単元対応を予定。
- research/factor_research は一部実装が開始された段階（calc_momentum の未完実装など）。ファクター群の完全実装・テストは今後の課題。
- 一部の I/O 操作（ファイル/DB/外部 API 呼び出し）はエラーパスのカバレッジを要拡張。

---

（本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は実装差分・コミット履歴・設計文書を参照して必要に応じて補正してください。）
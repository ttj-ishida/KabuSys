# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して自動生成された変更履歴です（実装時点の状態に基づきます）。

## [0.1.0] - 2026-04-19

### Added
- 全体
  - 初期リリースとして基本機能群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト / デーモン
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の `data/stop_requested.flag` ファイルで制御。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の `sqlite_path` を使用する設計。
    - ポーリング中の例外はログに記録してループ継続。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 用の SQLite（`data/paper_trading.db` を既定）を使用し、本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを作成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）に対応。
    - エンジンは別スレッドで実行し、フラグ検知時に安全に停止する仕組み。

- 設定 / 環境管理
  - config.Settings: 環境変数から設定値を取得する集中クラスを追加。
    - DBパス（DuckDB / SQLite）、ログレベル、環境種別（development / paper_trading / live）、paper trading の挙動（PAPER_FILL_MODE）等のプロパティを提供。
    - `KABUSYS_ENV` の検証、`LOG_LEVEL` の検証、paper trading 用の別 SQLite パス (`PAPER_TRADING_SQLITE_PATH`) をサポート。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml）を基準に `.env` と `.env.local` をロード。
    - OS 環境変数を保護しつつ `.env.local` で上書き可能。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - config_setup: 対話式ウィザードで `.env` を初期作成/更新する CLI を追加。
    - シークレット項目のマスク表示、選択肢サポート、保存前確認を実装。
  - validate_config: 設定検証 CLI を追加。
    - 必須環境変数チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML がインストールされている場合）。
    - `--strict` オプションで警告を失敗扱いにできる。

- ログ / プロセス制御ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - `LOG_DIR` / `LOG_LEVEL` 環境変数または引数から設定可能。
  - utils.process_priority: プラットフォーム差を吸収するプロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/macOS/FreeBSD）に対応し、psutil を利用して優先度設定を行う。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補を選択。
    - calc_equal_weights / calc_score_weights: 重み計算を提供（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限超過時に候補を除外するロジック。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear をマッピング、未知レジームはフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 等配分・スコア配分・リスクベース配分に対応した株数決定ロジックを提供。
    - 単元（lot_size）丸め、per-position および aggregate cap、コストバッファ考慮、スケーリングと残差配分アルゴリズムを実装。

- データ解析 / ツール
  - research.factor_research: DuckDB を用いてファクター（モメンタム・ボラティリティ等）を計算するモジュールを追加（設計方針と定数を含む実装）。
    - （ファイルは一部実装が続く構成。DuckDB 接続を受け prices_daily 等テーブルを参照する設計）
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を出力。
    - 環境変数 `PAPER_TRADING_SQLITE_PATH` や `--db` オプションで DB パスを指定可能。
    - デフォルト閾値（稼働率 99%、成功率 90% 等）を定義。

- DB 統合
  - DuckDB と SQLite の両方をサポートする構成を導入（各種モジュールで接続引数を受け取る）。
  - monitoring 用のテーブル初期化ユーティリティ（monitoring.monitoring_db.init_monitoring_db）へ接続して冪等に初期化。

### Changed
- （初期リリースにつき「変更」は特になし／新規導入的な項目）

### Fixed
- 設定/起動時の堅牢性向上（ハンドリング追加）
  - .env パーサ:
    - export プレフィックスへの対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、空行/コメント行の無視などを実装して堅牢化。
    - _load_env_file は既存 OS 環境変数を保護するオプション（protected）を導入。
  - run_monitoring:
    - 環境変数 `MONITOR_POLL_INTERVAL` が不正（非数または 0 以下）の場合、デフォルト 60 秒へフォールバックして警告を出す。
  - utils.logging_setup:
    - ログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、コンソール出力のみで継続するフォールバックを実装。
  - utils.process_priority:
    - 権限不足や未対応プラットフォームでエラーを出さず警告ログでスキップするように改善。
  - run_execution:
    - paper_trading モード時に paper_trading 用 SQLite を使用して本番 DB と分離することで誤操作リスクを低減。
  - validate_config:
    - config/*.yaml のパースチェックは PyYAML が未インストールの場合にスキップし、警告を出す仕様に変更（依存関係がない環境でも実行可能にするため）。

### Security
- 現在のところ特別なセキュリティ修正はありませんが、以下を考慮済み:
  - `.env` ファイルは機密情報を含むため README 等で Git 管理外にする旨を注記（config_setup にその旨のコメントを出力）。
  - シークレット項目は対話式ウィザードでマスク表示。

### Notes / Usage highlights
- 起動:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数の重要項目:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development / paper_trading / live）
  - SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL 等
- 停止制御:
  - プロセスの安全停止はプロジェクト内の `data/stop_requested.flag` を作成することで実現（run_monitoring/run_execution でチェック）。

---

今後のリリース候補（例）
- Unreleased: バグ修正、単体テスト追加、factor_research の完実装、CI/CD 設定、ブローカークライアントのモック実装の強化等。
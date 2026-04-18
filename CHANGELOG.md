# Changelog

すべての注目すべき変更点はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。システムのコア機能、運用用スクリプト、設定ツール、ポートフォリオ構成ロジック、ユーティリティ類、検証・レポートツールを追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor をポーリング実行する監視ループを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクト内の `data/stop_requested.flag` によって行う。
    - 監視は KABUSYS_ENV に依らず本番用の `sqlite_path` を使用する仕様。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は Mock ブローカを使用し、本番 DB と完全分離された `data/paper_trading.db` を使用する。
    - 停止フラグ・PID ファイル処理、スレッドでのエンジン実行と安全停止処理を実装。
- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。`.env` と `.env.local` の優先順位処理を実装。
    - 環境変数パーサの実装（export 付き、クォート、インラインコメント等に対応）。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、監視しきい値、環境判定フラグ等）をプロパティ経由で取得可能に。
    - `PAPER_FILL_MODE`, `PAPER_TRADING_SQLITE_PATH` 等の paper trading 関連設定を追加。
  - config_setup.py
    - 対話式ウィザードで `.env` を生成・更新する CLI を追加。秘密項目はマスクして入力を補助。
- 設定検証ツール
  - validate_config.py
    - `.env` と `config/*.yaml` の存在・基本妥当性をチェックする CLI を追加。
    - `--strict` オプションにより警告を失敗扱いにできる。
    - DB パス親ディレクトリの存在チェック、YAML のパースチェック（PyYAML がある場合）などを実装。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30世代保持）を設定する共通ユーティリティを追加。
    - LOG_DIR / LOG_LEVEL の解決、既存ハンドラの安全なクリア処理を実装。
  - utils/process_priority.py
    - Windows / POSIX を抽象化したプロセス優先度設定ユーティリティを追加。
    - CPU affinity 設定関数も提供（アクセス権限や未サポート OS を考慮して安全にスキップ）。
- ポートフォリオ構成ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順）、等金額配分、スコア重み付け（スコア合計が 0 の場合は等分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - 未知レジームや unknown セクターの扱いに関するフォールバックとログ出力を実装。
  - portfolio/position_sizing.py
    - position sizing（risk_based / equal / score）ロジックを実装。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash 超過時のスケーリング）や cost_buffer を考慮した調整を実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB を解析して検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどの指標を集計し、しきい値判定に基づき PASS/FAIL を出力。
    - DB パスは `--db` オプションまたは `PAPER_TRADING_SQLITE_PATH` 環境変数で指定可能。
- リサーチモジュール（着手）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等のファクター計算方針を実装の方針で追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。（実装はモジュール内で進行中）
- その他
  - execution サブシステム関連のファクトリ / マネージャ / エンジン等の組み立てロジック（BrokerClientFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler, OrderRepository）を起動スクリプトから組み合わせて起動する実装を追加（詳細は起動スクリプトでの組み立てコードを参照）。
  - monitoring 用 DB テーブル初期化ユーティリティ（init_monitoring_db）を run_* スクリプトで使用することで冪等に監視テーブルを保証。

### Changed
- なし（初回リリースのため変更履歴はありません）。

### Fixed
- なし（初回リリースのため修正履歴はありません）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- なし。

---

注意・運用メモ
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup のヘッダにも明記）。
- 監視プロセスは run_monitoring が常に本番用の sqlite_path を参照するため、開発環境で監視を実行する際は sqlite_path を意図した値に設定してください。
- ペーパートレードは本番 DB と分離しており、`KABUSYS_ENV=paper_trading` の場合に `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）が使用されます。
- ログの出力先は環境変数 `LOG_DIR` で変更可能。ファイルハンドラ作成に失敗した場合は標準出力のみで動作します。
- プロセス優先度や CPU affinity の設定には権限が必要な場合があります。無効な環境では警告を出してスキップします。

もし特定機能のリリースノートをより詳細に分割したい場合や、将来の変更点を Unreleased に追加していく形式への変更を希望する場合は教えてください。
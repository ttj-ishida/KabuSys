# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

次の内容はリポジトリ内のソースコードから推測して作成した変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

### Added
- 初期リリースとして以下の主要機能を追加。
- アプリケーションメタ情報
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。
- 設定管理
  - `kabusys.config.Settings`：.env と環境変数からの設定取得を提供。
  - 自動 .env ロード機構（`.env` / `.env.local`、OS 環境変数を保護）を実装。
  - .env ファイルパースの堅牢化（クォート、エスケープ、コメント処理）。
  - 各種設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 関連など）。
- 環境設定／検証 CLI
  - `kabusys.config_setup`：対話式ウィザードで .env の初期作成・更新を支援。
  - `kabusys.validate_config`：起動前の環境変数・設定ファイル（config/*.yaml）の検証ツール。`--strict` オプションをサポート。
- 実行／監視用起動スクリプト
  - `kabusys.run_execution`：ExecutionEngine の起動スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - Broker クライアントのファクトリ経由生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、デーモンスレッドでのエンジン実行、停止フラグ検知による安全停止を実装。
    - 実行 PID 管理（`data/execution.pid`）および停止フラグ（`data/stop_requested.flag`）の利用を想定。
  - `kabusys.run_monitoring`：SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き（デフォルト 60 秒）。
    - monitoring 用 DB は環境にかかわらず本番 sqlite_path を使用する挙動。
    - stop フラグ検知でループ終了、例外時のログ出力と次ポーリング継続。
- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を利用して、監視テーブルの冪等な初期化を実行（起動時に保証）。
- ロギング／プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：
    - stdout ストリームハンドラ + 日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、既存ハンドラのクリア、環境変数 / 引数によるログレベル・出力先解決。
  - `kabusys.utils.process_priority`：
    - Windows / POSIX を吸収したプロセス優先度設定 (`set_process_priority`) と CPU affinity 設定 (`set_cpu_affinity`)。
    - 権限や未対応環境ではフォールバックして警告で継続。
- ポートフォリオ構築（純粋関数群、DB 非依存）
  - `kabusys.portfolio.portfolio_builder`：
    - `select_candidates`（スコア降順で上位 N を選定）
    - `calc_equal_weights`（等重量配分）
    - `calc_score_weights`（スコア正規化配分、全スコア 0 場合はフォールバック）
  - `kabusys.portfolio.risk_adjustment`：
    - `apply_sector_cap`（セクター集中上限に基づく候補除外）
    - `calc_regime_multiplier`（市場レジームに応じた投下資金乗数）
  - `kabusys.portfolio.position_sizing`：
    - `calc_position_sizes`（allocation_method 指定で株数決定、risk_based / equal / score 対応、lot_size（単元）丸め、aggregate cap によるスケールダウン、cost_buffer 考慮）
- リサーチ／ファクター群（骨格）
  - `kabusys.research.factor_research`：モメンタム等のファクター計算モジュール（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。
    - モメンタム等の計算仕様・定数を定義（1M/3M/6M、MA200、ATR、出来高平均 など）。
    - （注）ファイル末尾が途中で切れているため、実装は部分的（続き・完成が必要）。
- ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading 用の検証レポート生成スクリプト（SQLite DB 参照）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力する。
    - デフォルト DB パスは `data/paper_trading.db`、オプションで `--db` 指定可能。
    - 判定基準（デフォルト）：稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
- DuckDB を分析用ストレージとして導入（`Settings.duckdb_path` を通じて接続を受け渡し）。
- DB/ファイルパスのデフォルト値を `data/` 以下に集約（例: `data/kabusys.duckdb`, `data/monitoring.db`, `data/paper_trading.db`）。

### Changed
- （初版のため変更履歴なし）

### Fixed
- （初版のため修正履歴なし）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- （なし）

---

## 既知の制限・注意事項（コードから推測）
- factor_research モジュールはファイル末尾で途切れており、実装が未完了の個所があります（要実装・レビュー）。
- .env の自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml を起点）。プロジェクトルートが検出できないと自動読み込みはスキップされる。
- `set_process_priority` / `set_cpu_affinity` は権限不足や未対応 OS の場合に失敗し、警告でフォールバックする設計（致命的エラーにはしない）。
- logging_setup はログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続する。
- PAPER_FILL_MODE 等、一部環境変数は有効値チェックがあるため誤設定時に例外を投げる（起動前に validate_config の実行を推奨）。
- run_monitoring は常に本番用 sqlite_path を使用する仕様のため、開発環境で別 DB を使いたい場合は設計に注意が必要。
- run_execution は paper_trading を選んだ場合、本番 DB と分離した paper-trading 用 DB を使用する。Paper と Live の DB 分離により誤発注リスクを低減。
- 一部関数で TODO コメントあり（例: セクターエクスポージャー計算で価格欠損時のフォールバックが未実装）。

---

上記内容はソースコードを読み取り推測したものであり、実際のリリースノートはリポジトリ管理ポリシーやコミット履歴に基づいて調整してください。必要であれば、各項目の詳細（影響範囲・使用例・CLI 実行例）を追記します。
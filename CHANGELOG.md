# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
(https://keepachangelog.com/ja/1.0.0/)

## [Unreleased]

## [0.1.0] - 2026-04-21
初回リリース。本リリースでは自動売買システム "KabuSys" のコア機能群の初期実装を追加しました。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 設定管理
  - 環境変数・設定管理モジュール `kabusys.config` を追加。
    - .env / .env.local の自動読み込み（OS環境変数優先、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - .env ファイルのパース機能（コメント、クォート、エスケープ対応）。
    - 必須/任意設定、環境 (`KABUSYS_ENV`)、パス、各種閾値などのプロパティを提供。
    - `settings = Settings()` による簡易利用をサポート。

- 環境セットアップ / 検証 CLI
  - `kabusys.config_setup`：対話式ウィザードで .env を作成・更新する CLI を追加。
    - 複数の設定項目（環境、API トークン、DB パス、ログレベルなど）を対話的に入力。
    - .env の読み取り/書き込みロジックを提供。
  - `kabusys.validate_config`：起動前チェック用 CLI を追加。
    - 必須環境変数のチェック、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェック、DB パス親ディレクトリの確認。
    - `config/*.yaml`（複数ファイル）の存在確認および PyYAML があればパース検証。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行エンジン起動スクリプト
  - `kabusys.run_execution`：ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッド起動。
    - 停止フラグ（`data/stop_requested.flag`）・PID ファイル（`data/execution.pid`）を考慮した停止処理。
    - 初期化時に監視テーブルの整備（`init_monitoring_db`）を行う。

- 監視ループ起動スクリプト
  - `kabusys.run_monitoring`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境にかかわらず本番用 `sqlite_path` を使用して監視 DB として接続（意図的な設計）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してフォールバック）。
    - 停止フラグ検知でループ終了、`KeyboardInterrupt` による終了処理をサポート。

- ロギング / プロセス優先度ユーティリティ
  - `kabusys.utils.logging_setup`：統一ログ設定ユーティリティを追加。
    - stdout に出力する StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリの自動作成、既存ハンドラのクリーンアップ、環境変数 `LOG_LEVEL` / `LOG_DIR` による制御。
  - `kabusys.utils.process_priority`：プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して `set_process_priority("high"|"normal"|"low")` を提供。
    - `set_cpu_affinity(cpu_count)` によるプロセスのコア固定をサポート（サポートされない環境では警告してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選択 select_candidates（score 降順・タイブレークに signal_rank）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制御 apply_sector_cap（既存ポジション + 価格を基にセクター別エクスポージャ算出、上限を超えるセクターの候補除外）。
    - レジーム乗数 calc_regime_multiplier（bull/neutral/bear → 1.0/0.7/0.3、未知レジームはフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 株数決定 calc_position_sizes（risk_based / equal / score の配分方式、lot_size（単元）丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積）。
    - 端数処理のための残差配分ロジックを実装。

- DuckDB / SQLite を使用した分析・レポート
  - `kabusys.tools.paper_verification_report`：ペーパートレード検証レポート生成スクリプトを追加。
    - paper trading SQLite（`PAPER_TRADING_SQLITE_PATH` で指定）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ 等）を集計。
    - 閾値を定めて PASS/FAIL 判定を行う。
    - CLI 引数で期間・DB パスを指定可能。

- 研究用ファクター計算（骨組み）
  - `kabusys.research.factor_research`：DuckDB 接続を受け取りファクターを計算するモジュールを追加（モメンタム等の定義、定数）。
    - モメンタム、MA200、ATR、出来高系などの計算を想定した設計。関数雛形と定数を実装（一部実装中）。

- 監視 DB 初期化ユーティリティ
  - `kabusys.monitoring.monitoring_db`（各スクリプトから呼び出し）を通じて監視テーブルの冪等な初期化を想定。

- その他
  - 各サブモジュールを __all__ でエクスポートして高レベル API を提供（kabusys.portfolio など）。
  - スレッドを使った ExecutionEngine 実行、停止フラグ監視の一般化。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注記 / 既知の制約・TODO
- position_sizing の将来拡張: 銘柄毎の lot_size をサポートするため stocks マスタの導入を検討中（現状は全銘柄共通 lot_size）。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャが過小見積りとなる懸念あり。将来的には前日終値や取得原価などのフォールバック価格を導入予定。
- factor_research モジュールは骨組みが含まれるが、一部実装が途中（モメンタム計算関数の途中で切れている）。今後、DuckDB のクエリ実装と統合テストを追加予定。
- run_monitoring は設計上、監視 DB に本番 sqlite_path を利用する（KABUSYS_ENV に依存しない）。運用上の分離が必要な場合は設定で対応してください。
- ログディレクトリの作成やプロセス優先度設定は環境によって失敗する可能性があり、その場合は警告を出して処理を継続します。

もしリリースノートに追加してほしい詳細（例: 影響を受ける設定例、運用手順、既知のバグの具体的対応策など）があれば教えてください。それに合わせて CHANGELOG を修正します。
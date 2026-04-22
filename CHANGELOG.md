# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このファイルはリポジトリ内のコードベースから推測して作成しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-22

初回公開リリース。主に自動売買システムのコア機能群、運用用ユーティリティ、CLI ツール、ポートフォリオ構築ロジック、監視/実行ランチャーを追加。

### Added

- 全体
  - パッケージバージョンを設定: `kabusys.__version__ = "0.1.0"`。
  - 豊富なモジュール構成とドキュメント付きのコードベースを追加（各モジュールに docstring を含む）。

- 設定・環境管理
  - `kabusys.config.Settings` を追加。環境変数経由で設定を取得する統一 API を提供。
  - プロジェクトルート自動検出と `.env` 自動ロード機能を実装。
  - `.env` のパース機能を強化（export プレフィックス対応、クォートとエスケープ処理、インラインコメント処理など）。
  - `config_setup.py`：対話式ウィザードで `.env` を生成・更新する CLI を追加（項目定義・読み書きロジックあり）。
  - `validate_config.py`：起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース検証（PyYAML が存在しない場合はスキップ）などをチェック可能。`--strict` オプションで警告を失敗扱いにできる。

- ログ・プロセス管理
  - `kabusys.utils.logging_setup.setup_logging` を追加。コンソール（stdout）出力と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーに統一的に設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority` を追加。Windows/Linux/macOS に対応したプロセス優先度設定（`set_process_priority`）と CPU affinity 設定（`set_cpu_affinity`）を提供。psutil を使い、権限不足時は警告してスキップする。

- 実行 / 監視ランチャー
  - `run_execution.py`：ExecutionEngine 起動用スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は Paper 用 SQLite（環境変数またはデフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - Broker クライアントのファクトリ利用、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine をスレッドで実行し停止フラグ（data/stop_requested.flag）を監視して安全停止。
    - 実行 PID を `data/execution.pid` に書き込む仕組み（Engine 側の pid_file 指定）。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はフォールバックして警告を出す。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用する設計（監視データは本番 DB に記録）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。

- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を各起動プロセスから呼ぶことで監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築（pure functions）
  - `kabusys.portfolio.portfolio_builder`：
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全て 0 の場合は等金額にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - apply_sector_cap: セクター集中上限に基づき新規候補を除外（既存ポジションの時価合計を評価、"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。
  - `kabusys.portfolio.position_sizing`：
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づいた株数決定ロジックを実装。単元（lot_size）丸め、1 銘柄上限、aggregate cap スケールダウン、cost_buffer（手数料・スリッページ見積）対応、端数再配分ロジックなどを含む。

- ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading の検証レポートを SQLite（デフォルト `data/paper_trading.db`）から生成する CLI。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を行う。閾値はスクリプト内に定義（稼働率 99%、fill 90%、send 95%、P95 200ms）。

- 研究用（下地）
  - `kabusys.research.factor_research`：ファクター計算モジュールの骨組みを追加。モメンタム等の定義、DuckDB 接続を利用した計算方針、calc_momentum の実装開始（モジュールに計算定数と入出力仕様を定義）。

### Changed

- ロギングの挙動を統一
  - stdout を使用してログを出力（cron/Task Scheduler でのリダイレクトを想定）。
  - 既存ハンドラを再設定する際に flush/close を行って二重登録を防止。

### Fixed

- 環境変数/設定の堅牢性向上
  - `.env` パーサーの問題を軽減（空行/コメント/quoted value の取り扱い改善）。
  - MONITOR_POLL_INTERVAL の不正値（0 / 負値 / 非数）に対するフォールバック処理を追加し、time.sleep による例外発生を防止。

### Notes / TODO

- apply_sector_cap 内で価格（price_map）欠損時のフォールバックは現状未実装（コメントに TODO を残す）。将来的に前日終値や取得原価等のフォールバック導入を検討する必要あり。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄マスタから銘柄別単元を取得する拡張予定。
- research.factor_research の実装は継続中で、一部関数は未完（スナップショットは途中で終端している）。

### Security

- `.env` ファイルは絶対に Git にコミットしない旨を config_setup の出力で明示。

---

今後のリリースでは、Research モジュールの完成、ExecutionEngine・Monitoring の細かい運転監視・回復処理強化、テストカバレッジの追加、ドキュメントの整備（Contribution ガイド等）を予定しています。
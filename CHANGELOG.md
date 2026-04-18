KEEP A CHANGELOG
=================

このファイルは Keep a Changelog の形式に準拠しています。
比較可能な変更履歴を人間が読みやすい形で記録します。

フォーマット
- 重大度: Added / Changed / Fixed / Deprecated / Removed / Security
- 日付は YYYY-MM-DD 形式

Unreleased
----------
- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初版リリースを追加。
  - パッケージバージョン: __version__ = "0.1.0"
- 実行コンポーネント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて本番/ペーパートレードを切替え、ペーパートレード時は専用 SQLite（data/paper_trading.db 既定）を使用する分離を実装。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のデーモンスレッド起動・停止ロジック、実行用 PID ファイル処理を実装。
- 監視コンポーネント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知で優雅に終了。監視 DB 初期化処理を組み込み。
- 設定管理
  - config.py: .env ファイル自動読み込み機能（.env → .env.local の優先順）を実装。安全のため OS 環境変数は保護し上書きされないよう実装。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理などを考慮した堅牢なパース処理を実装。
  - Settings クラスに各種プロパティを実装（J-Quants / kabu API / DB パス / paper_trading 用設定 / 監視閾値 / 環境判定等）。値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を行う。
- 設定ユーティリティ
  - config_setup.py: 対話式 .env 設定ウィザードを追加。既存 .env 読み込み、シークレットのマスク表示、デフォルト提示、保存テンプレートを実装。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、DB パス親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードチェックを実施。--strict モードをサポート。
- ロギング
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ設定。LOG_LEVEL / LOG_DIR の解決順を実装し、ログディレクトリ作成失敗時はファイル出力を安全にスキップするフォールバックを用意。
- プロセス制御
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを追加。権限不足や未対応環境でも警告を出して安全にスキップする。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 銘柄選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）を追加。スコアが全て 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。unknown セクターは上限制約の対象外とする等の仕様を明示。
  - portfolio/position_sizing.py: 各銘柄の発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。単元株（lot_size）丸め、max_position_pct / max_utilization に基づく上限、cost_buffer を考慮した aggregate cap スケーリング（スケールダウン時の再配分アルゴリズム含む）を実装。
- 解析・研究
  - research/factor_research.py: モメンタム等のファクター計算モジュールを追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。（注: ファイル末尾は実装途中の節が存在）
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等を集計し PASS/FAIL 判定を行う。閾値はソース内で定義（稼働率 >= 99% 等）。日付フィルタと DB パス上書きオプションをサポート。

Changed
- すべての起動スクリプトで最初にプロセス優先度を "high" に設定する処理を追加（set_process_priority 呼び出し）。
- run_execution.py: ペーパートレードと本番の DB 分離を明確化（settings.is_paper 判定で paper_sqlite_path を使用）。

Fixed
- .env 読み込みとパースの堅牢性を向上（クォート中のエスケープ、コメント処理、export キーワード対応）。
- run_monitoring.py: MONITOR_POLL_INTERVAL の不正値（0 以下や非数）に対する保護を追加し、デフォルト値へフォールバックするように改善。
- logging_setup: ログディレクトリ作成に失敗した際にファイルハンドラ作成をスキップし、コンソール出力のみで継続するように修正。
- utils/process_priority: 未対応 OS や権限不足に対して例外を捕捉し、警告してスキップするよう変更（起動時に致命的にならない）。

Known issues / Notes
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少推定される可能性があり、コメントに将来のフォールバック価格戦略（前日終値や取得原価）を検討する旨を記載。
- portfolio/position_sizing:
  - 将来的に銘柄ごとの単元株数をサポートする旨の TODO がある（現状は全銘柄共通 lot_size）。
- research/factor_research.py: ファイル末尾が途中で切れている（実装継続の必要あり）。
- 一部処理は外部依存（psutil, duckdb, PyYAML など）あり、環境によっては機能が制限される。validate_config は PyYAML がない場合に YAML 検証をスキップする。

Security
- なし

Removed
- なし

Deprecated
- なし

以上。今後のバージョンでは research モジュールの完成、銘柄別単元対応、価格フォールバック実装、より詳細な監視メトリクス強化等を予定しています。
CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。重要な変更点・機能追加・振る舞いをコードベースから推測して日本語でまとめています。

Unreleased
----------
- （なし）

0.1.0 - 2026-04-19
------------------
Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード DB（data/paper_trading.db）を使用し MockBrokerClient を利用する振る舞いを実装。エンジンは別スレッドで実行、停止フラグ（data/stop_requested.flag）を監視して安全に停止する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に依存せず本番用 sqlite_path を使用する。
- 設定管理・環境変数周り
  - config.py: .env の自動読み込み（.env, .env.local）、ロードロジック（override と protected キー）、.env 行の詳細パース（export 形式、クォート値のエスケープ、インラインコメント処理）を実装。Settings クラスで各種環境変数をラップし、値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を提供。
  - config_setup.py: 対話式ウィザードで .env を生成／更新する CLI を実装。既存値の読み込み・マスク表示・確認・保存機能を持つ。
  - validate_config.py: 起動前チェック CLI を実装。必須環境変数の存在確認、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境時のガードチェックを行う。--strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順）、等重み／スコア加重（スコア合計0時のフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のレジーム時は警告してフォールバック。
  - portfolio/position_sizing.py: position size（発注株数）計算を実装。risk_based / equal / score の配分方式をサポート。単元株（lot_size）丸め、ポジション上限（max_position_pct）、aggregate cap によるスケーリング、cost_buffer を考慮した安全なスケールダウンロジック（端数の再配分アルゴリズム）を実装。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定を提供。stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する。
  - utils/process_priority.py: psutil を使ったプロセス優先度設定（Windows / POSIX の差分吸収）と CPU affinity 設定ユーティリティを提供。権限不足や未対応プラットフォームでは警告を出してスキップ。
- モニタリング関連
  - monitoring 側の DB 初期化（init_monitoring_db を使用）や SystemMonitor の呼び出しが組み込まれた。
- 運用ツール
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を計算してレポート出力。閾値に基づいた PASS/FAIL 判定を実装。--from/--to/--db オプション対応。
- 研究用モジュール（初期実装）
  - research/factor_research.py: ファクター計算モジュール（Momentum, Value, Volatility, Liquidity）の骨格を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計（まだ途中実装の箇所あり）。

Changed
- ログ出力の挙動を統一
  - すべての起動スクリプトから utils.setup_logging を呼び出し、ログの出力先・フォーマット・ログレベル解決を統一。ログファイルは logs/<app_name>.log、日次ローテーションで 30 日分保持。
- .env 自動ロードの安全化
  - OS 環境変数を保護する protected 機構を導入し、.env.local の override を許容しつつ OS 環境変数を上書きしない。

Fixed
- 環境値パースの堅牢化
  - MONITOR_POLL_INTERVAL の不正値（0, 負数、非数）に対してデフォルトへフォールバックし、警告を出すようにした（run_monitoring）。
  - .env パーサでクォート値に含まれるバックスラッシュエスケープ、export プレフィックス、インラインコメントの取り扱いを正しく処理するように改善。
- プロセス制御の安全化
  - run_execution/run_monitoring が起動時にプロセス優先度をまず設定するようにし、優先度設定に失敗してもワークフローが継続するよう例外をハンドリング。

Security
- .env の取り扱いに関する注意を config_setup の出力に明記（.env を Git にコミットしない旨）。

Notes / Implementation details
- run_monitoring は監視 DB に本番用 sqlite_path を常に使用するため、開発環境でも監視データは同じ DB に書き込まれることに注意が必要。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用することで、ペーパートレードと本番 DB を分離している。
- position_sizing の aggregate スケールダウン処理は lot_size 単位で端数を再配分するアルゴリズムを備え、再現性を保つため tie-break にコードを利用する。
- utils/process_priority は psutil に依存し、権限不足で設定できない場合は警告を出してフォールバックする。

その他
- パッケージバージョン: __version__ = "0.1.0"

今後の追加検討点（想定）
- research/factor_research の完全実装（各ファクターの SQL 実装と正規化）
- 個別銘柄の lot_size を銘柄マスタから読み込む対応
- 監視テーブル・ログ周りのメトリクス収集強化（Prometheus など）
- 高可用化のためのプロセスマネージャ連携や systemd ユニットファイル例の追加

----------------------------------------------------------------------

注: 上記は提供されたコードベースの内容から推測して作成した CHANGELOG です。実際のコミット履歴やリリースノートと差異がある場合があります。必要であれば、特定ファイルやモジュール単位でより詳細な変更点（関数一覧、引数変更、例外仕様など）を追加で生成します。
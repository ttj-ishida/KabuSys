CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
各項目はコードから推測できる機能追加・改善・修正点を日本語でまとめたものです。

Unreleased
----------
- （なし）

[0.1.0] - 2026-04-24
--------------------

Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用の MockBrokerClient を使用し、paper_trading 専用 SQLite DB に記録する。停止フラグ検出による安全停止、プロセス PID ファイル出力、デーモンスレッド実行ロジックを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグでループを中断し、例外発生時はログ出力して次のポーリングに継続。

- 設定管理・ウィザード・検証
  - kabusys.config.Settings: 環境変数経由で多数の設定を取得する Settings クラスを実装（DB パス、API トークン、環境種別、しきい値など）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env ロードを無効化可能。
  - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を自動読み込み（OS 環境変数は保護）。
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
  - validate_config.py: .env および config/*.yaml の前提チェックを行う検証 CLI を追加。--strict オプションで警告を失敗扱い可能。本番環境（live）向けの追加ガードチェックを実装。

- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging: stdout 出力用 StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに統一設定するユーティリティを追加。LOG_DIR / LOG_LEVEL の環境設定を尊重し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する堅牢性を有する。
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度（high/normal/low）や CPU affinity を設定するユーティリティを追加。権限不足や未対応環境では警告を出して処理をスキップ。

- データベース関連
  - duckdb および sqlite3 サポートを導入。monitoring 用テーブルの初期化を行う init_monitoring_db を呼び出す実行フローを追加。
  - 実行時の DB パス分離: monitoring は環境に関係なく本番 sqlite_path を参照し、execution は KABUSYS_ENV に応じて paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用するように区別。

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全ゼロ時のフォールバック警告を追加。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装（unknown レジームのフォールバック挙動含む）。
  - portfolio.position_sizing: risk_based / equal / score の配分方式に対応する calc_position_sizes を実装。単元株（lot_size）丸め、per-stock 上限・aggregate cap のスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮した配分ロジックを導入。

- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計してレポート出力する CLI を追加。閾値に基づく PASS/FAIL 判定を提供。

Changed
- .env パーサーの挙動を強化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理（非クォート値における '#' の扱い）、既存 OS 環境変数の保護（protected）など、実用的な .env パースを実装。
  - .env 読み込み順序: OS 環境 > .env.local > .env（.env.local は override=True）。

- ログ出力先を stdout に統一
  - タスクスケジューラや cron との相性を考慮し、StreamHandler は stderr ではなく stdout を使用するよう変更。

- 監視ループ・実行ループの安全性向上
  - 停止フラグファイル（data/stop_requested.flag など）を監視して安全にシャットダウンする挙動を追加。
  - run_monitoring のポーリングループで check_once() の例外を捕捉してループ継続する設計に変更（1回の例外でプロセスが落ちないように）。

Fixed
- 環境変数 MONITOR_POLL_INTERVAL の不正値処理を改善
  - 文字列や 0/負数が指定された場合に警告を出してデフォルト（60 秒）にフォールバックするように修正（time.sleep に渡す不正値でクラッシュしないよう保護）。

- ExecutionEngine の起動制御と停止処理
  - 起動前に停止フラグが立っている場合は起動せずに終了する挙動を追加。
  - 実行中に停止フラグを検知した場合は engine.stop() を呼び出して整然と停止させ、デーモンスレッドを最大タイムアウトで join する安全策を導入。

- 設定検証の堅牢化
  - validate_config において必須環境変数未設定やプレースホルダ値を検出して警告/エラーに分類。PyYAML 未導入時の挙動を明示的にスキップしてユーザーに警告するように修正。

Notes / Known limitations
- research.factor_research モジュールはファイルの最後が切れている（実装途中の可能性あり）。完全実装は今後の対応予定。
- position_sizing の一部（価格欠損時のフォールバック、銘柄別 lot_size のサポート）は TODO コメントあり。将来的な拡張を想定。
- ファイル入出力（ログディレクトリ作成や PID ファイル書き込みなど）で権限不足が発生した場合はフォールバック動作（警告を出して機能を制限）する設計。

謝辞
- このリリースではコアランタイム、構成管理（.env）、運用用ユーティリティ（ログ・優先度・停止フラグ）、ポートフォリオ構築ロジック、検証ツール群を整備しました。今後は research モジュールの完成、テストカバレッジの強化、および BrokerClient 等外部依存部分のモック／抽象化を進める予定です。
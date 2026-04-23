# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
項目は大別して Added / Changed / Fixed / Removed / Deprecated / Security に分類しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-23

初回公開リリース。以下の主要機能・ユーティリティ・CLI を含みます。

### Added
- 実行スクリプト / サービス
  - run_execution: ExecutionEngine を起動する実行スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の別 SQLite DB を使用して本番 DB と分離して実行可能に。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグファイル（data/stop_requested.flag）を監視して安全に終了する挙動を実装。
- 設定関連 CLI / ユーティリティ
  - config_setup: .env を対話式に作成・更新するウィザード CLI を追加。secret 項目のマスク表示や既存 .env の読み込み/再利用に対応。
  - validate_config: .env および config/*.yaml の起動前チェック CLI を追加。必須環境変数チェック、KABUSYS_ENV の整合性チェック、DB パスや YAML パース（PyYAML が存在する場合）などを検査。--strict オプションで警告も FAIL 扱いにできる。
- 分析 / レポート
  - tools/paper_verification_report: ペーパートレード結果の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（Avg/Max/P95）などを算出し PASS/FAIL 判定を行う。期間指定や DB パス指定オプションをサポート。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームに基づく投下資金乗数 calc_regime_multiplier を実装。
  - portfolio.position_sizing: リスクベース／等配分・スコア配分に基づく株数計算 calc_position_sizes を実装。単元（lot_size）丸め・aggregate cap（総投下額が利用可能現金を超える場合のスケーリング）・コストバッファを考慮。
- 設定管理
  - config.Settings: 環境変数ラッパーを追加。デフォルト値、型変換、および入力検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。settings インスタンスをエクスポート。
  - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動読み込み（環境変数で KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env ファイルパーサー: export プレフィックス対応、クォート文字・エスケープ処理、インラインコメントの扱いなど堅牢なパースロジックを実装。
- データベース / 分析
  - duckdb を利用する分析向け接続を各所でサポート（duckdb_path 設定）。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を導入し、起動時に監視用テーブルの存在を保証（冪等）。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定するセットアップ関数を追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils.process_priority: Windows / POSIX を吸収し、プロセス優先度（high/normal/low）と CPU affinity 設定（set_cpu_affinity）を提供。psutil を利用し、権限不足等の例外時は警告を出して安全にフォールバック。

### Changed
- run_monitoring:
  - Monitoring は KABUSYS_ENV に関係なく production の sqlite_path（settings.sqlite_path）を使用する設計に明記。
  - ポーリングループで monitor.check_once() 内の例外を捕捉し、ログ出力して次のポーリングへ復帰する堅牢化を実装。
- run_execution:
  - Paper trading と Live を明確に分離。paper_trading 環境では settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用するように変更。
  - エンジンは別スレッドで実行し、停止フラグ検知時に安全に engine.stop() を呼ぶ制御を追加。PID ファイル等の取り扱いを組み込み。
- logging_setup:
  - デフォルトで stdout を使用するように変更（cron やタスクスケジューラからのリダイレクトを考慮）。
  - ログレベル・ログディレクトリの解決順序を明確化（引数 > 環境変数 > デフォルト）。
- config_setup:
  - 対話ウィザードで既存値の再利用、シークレット項目のマスク表示、保存前の確認プロンプトを追加。
- portfolio.position_sizing:
  - aggregate cap のスケーリング処理において lot_size 単位での端数処理と残余配分ロジックを実装し、総コスト超過時の按分を安定化。

### Fixed
- .env パーサーの堅牢性向上
  - export キーワード対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの誤認処理を修正。
- 環境変数の読み込み順序の明確化
  - OS 環境変数 > .env.local > .env の順で読み込むよう実装。既存 OS 環境変数は .env で上書きされないよう保護。
- run_monitoring のポーリング間隔設定
  - 環境変数 MONITOR_POLL_INTERVAL の不正値（非数値・0 以下）に対して警告を出し、デフォルト値（60 秒）にフォールバックする挙動を追加（time.sleep に渡す負の値回避）。
- run_execution の停止挙動
  - 停止フラグ検知時のエンジン停止／スレッド join 処理を堅牢化。既に停止フラグが立っている場合は起動をスキップして終了する。
- paper_verification_report
  - データがない・テーブルが存在しない場合に sqlite3.OperationalError を捕捉してレポート生成を継続するように修正。P95 算出ロジックの空データハンドリングを追加。
- process_priority / set_cpu_affinity
  - 権限不足や未サポート OS 上での例外をキャッチして警告ログを出すことで、起動失敗を防止するよう修正。
- portfolio.portfolio_builder
  - calc_score_weights: 全銘柄のスコアが 0.0 の場合は等金額配分にフォールバックして NaN/ZeroDivision を回避。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

リリースに含まれる主なファイル（抜粋）
- src/kabusys/__init__.py (version 0.1.0)
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/utils/logging_setup.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py (一部実装)

注:
- 上記はソースコードの内容から推測して作成した変更履歴です。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。
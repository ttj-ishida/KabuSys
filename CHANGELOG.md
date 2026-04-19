# Changelog

すべての重要な変更をこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠します。
セマンティック バージョニングを使用します。  

※ この CHANGELOG はソースコードから推測して作成したものであり、実際のコミット履歴とは異なる可能性があります。

## [Unreleased]

### Added
- 監視・実行系の起動スクリプトを追加/改善
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検出で安全に終了。
  - run_execution: ExecutionEngine を起動するスクリプトを実装。KABUSYS_ENV=paper_trading 時は専用のペーパートレーディング用 DB（data/paper_trading.db）を使用して本番 DB と分離。

- 環境設定・検証・ウィザード
  - config_setup CLI: .env ファイルの対話的作成/更新ウィザードを追加（シークレット入力、選択肢、デフォルト反映、確認プロンプト）。
  - validate_config CLI: 起動前に .env および config/*.yaml の検証を行うユーティリティを追加。--strict モードで警告をエラー扱いに可能。
  - 環境変数自動読み込み機能: プロジェクトルートの .env/.env.local を自動で読み込む（OS 環境変数の保護機構あり）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

- 設定管理
  - Settings クラスを実装し、各種環境変数（データベースパス、API トークン、KABUSYS_ENV、ログレベル、監視しきい値など）をプロパティ経由で取得・検証する機構を提供。
  - .env パースの堅牢化: export プレフィックス、クォート、インラインコメント、エスケープシーケンスに対応。

- ロギング・プロセス管理ユーティリティ
  - logging_setup: stdout ストリームハンドラと日次ローテートのファイルハンドラ（TimedRotatingFileHandler、30日保持）をルートロガーに一元設定。ログディレクトリ作成失敗時のフォールバック処理を実装。
  - process_priority: Windows / POSIX を抽象化してプロセス優先度(nice / HIGH_PRIORITY_CLASS) を設定するユーティリティを追加。CPU affinity 設定関数も実装（設定失敗時は警告でスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder: シグナル選定（score 降順、signal_rank によるタイブレーク）、等分配・スコア加重の重み計算を追加。スコアが全て 0 の場合のフォールバックを実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - position_sizing: 各種配分方式（risk_based, equal, score）に基づく株数算出、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）考慮などのロジックを実装。

- ペーパートレード検証ツール
  - tools/paper_verification_report: SQLite のペーパートレード DB を解析して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計するレポート生成スクリプトを追加。閾値に基づく PASS/FAIL 判定を出力。CLI オプション --from/--to/--db をサポート。

- リサーチ（骨子）
  - research/factor_research: DuckDB を用いたファクター計算モジュール（Momentum, Value, Volatility, Liquidity）の設計と一部実装。DuckDB 接続を受け取り SQL + Python で処理する想定（prices_daily / raw_financials テーブル参照）。※ 実装途中の箇所あり。

### Changed
- 監視起動時の DB 接続挙動を明示
  - run_monitoring は KABUSYS_ENV に関わらず「本番」sqlite_path を使用して監視テーブルを管理する方針を明確化（監視は実環境の状態を参照するため）。

- logging_setup の挙動調整
  - StreamHandler は stdout に出力するように変更（cron 等で stdout/stderr を一本化する運用を想定）。既存ハンドラは必ずクリアして設定を二重登録しないように実装。

### Fixed
- 起動ループの例外耐性向上
  - run_monitoring のポーリング内で monitor.check_once() が例外を投げてもループを継続し、例外内容をログ出力して次のポーリングまで待機するように修正（監視プロセスの耐障害性向上）。
  - run_execution でバックグラウンドスレッド実行中に停止フラグを検知した際、engine.stop() を呼び安全に停止する処理を追加。

### Security
- シークレットの扱い改善
  - config_setup の表示や確認でシークレット項目をマスク表示（"****"）するようにし、.env の生成時に注意書きを追加。

---

## [0.1.0] - 2026-04-19

初回リリース想定（コードベースから推測）。

### Added
- パッケージ基盤
  - パッケージ初期設定ファイル（__init__.py、version=0.1.0）。
  - モジュール群: config, config_setup, validate_config, utils, portfolio, monitoring/run_monitoring, execution/run_execution, tools/paper_verification_report, research/factor_research（骨子）。

- 実行・監視機能
  - ExecutionEngine 起動スクリプト（run_execution）と SystemMonitor 起動スクリプト（run_monitoring）。
  - BrokerClientFactory 経由でブローカークライアントを分離（paper_trading と live を切り分け）。

- データベース連携
  - SQLite（監視用 / ペーパートレード用）と DuckDB（分析用）の接続をサポートし、起動時に必要なテーブルが存在することを保証する初期化処理（init_monitoring_db を利用）。

- リスク管理デフォルト値
  - RiskManager の構成パラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をデフォルトで設定。initial_portfolio_value を broker.get_available_cash() から取得して初期化する設計。

- 監視・停止制御
  - data/stop_requested.flag による停止フラグ、data/execution.pid（エンジン PID 保存）等のファイルベース制御を導入。
  - KILL_FLAG_CLEAR_ON_START 設定を読み取るプロパティを追加（本番での誤操作防止用）。

### Changed
- .env のデフォルトロード順を定義（OS > .env.local > .env）。
- .env パーサーの堅牢化（引用符・エスケープ・inline コメント処理、export プレフィックス対応）。

### Fixed
- 主要ユーティリティがエラー時に安全にフォールバックするように修正（ログディレクトリ作成失敗時の stdout のみ出力、psutil の権限エラーのハンドリングなど）。

---

## 既知の問題 / 注意点
- research/factor_research はファイル末尾が途中で切れているように見え、実装が未完の箇所があります。実運用前に機能の完成・テストが必要です。
- position_sizing, apply_sector_cap 等で価格が欠損 (0.0) の場合の扱いに TODO が残っており、欠損価格に対するフォールバック（前日終値や取得原価等）の実装が推奨されます。
- process_priority / cpu_affinity はプラットフォームや権限に依存し、設定に失敗する場合は警告を出してスキップします。権限や psutil のバージョンを確認してください。
- .env は機密情報を含むため、絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きを追加済み）。

---

作成者注: 上記 CHANGELOG は提供されたソースツリーを解析して推測に基づき記述したものです。実際のリリースノートやコミット履歴に合わせて適宜修正してください。
# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースの現状（初回リリース相当）から推測して作成しています。

全般的な注記:
- バージョンはパッケージの __version__ に準拠しています（0.1.0）。
- 多くの機能が CLI スクリプト・ライブラリとして提供され、ローカル実行・ペーパートレード環境・本番環境を想定した設計になっています。
- 設定は .env / 環境変数および config/*.yaml によって管理します。自動ロード、対話式ウィザード、検証ツールを備えています。

## [0.1.0] - 2026-04-23

### Added
- 実行エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し MockBrokerClient による分離を行う。
    - 起動時にプロセス優先度を "high" に設定。
    - stop フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の取り扱いを実装。
    - スレッドで ExecutionEngine を起動し、停止フラグ検知で安全に停止するループを実装。
- 監視エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は実行環境に依らず本番 sqlite_path を利用して監視テーブルを一貫して扱う。
    - stop フラグの検知、例外捕捉とログ出力、リソースクローズ処理を実装。
- 設定管理
  - config.py: 環境変数・.env 自動読み込み、.env ファイルパースロジック、設定値アクセス用 Settings クラスを追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml）。
    - .env の読み込み順序: OS 環境 > .env.local > .env。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数取得用の _require と各種設定プロパティ（DB パス、PID パス、閾値、環境判定など）を提供。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH などペーパートレード関連設定をサポート。
- 設定作成ウィザード
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - プロンプト、既存 .env の読み込み、シークレット値のマスク表示、最終確認とファイル書き込みを提供。
- 設定検証ツール
  - validate_config.py: 起動前チェック用 CLI を追加。
    - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在と（PyYAML がある場合の）パース検証、"live" 環境向けのガードチェックを実装。
    - --strict オプションで警告も失敗扱いにする。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定・重み計算（等分配・スコア配分、スコアが全て 0 の場合のフォールバック）を追加。
  - portfolio/position_sizing.py: 発注株数算出ロジック（risk_based / equal / score の配分方式、単元株丸め、aggregate cap のスケーリング）を追加。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームによる投下資金乗数（calc_regime_multiplier）を追加。
  - portfolio/__init__.py で公開 API をまとめてエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日分保持）のファイル出力を設定。
    - ログディレクトリ自動作成処理、作成失敗時のフォールバックを実装。
    - LOG_LEVEL や LOG_DIR を環境変数で上書き可能。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供。
    - set_cpu_affinity(cpu_count) による CPU ピニングをサポート（権限エラー等は安全に無視してログ警告）。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - SQLite のトレード/監視ログから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計して PASS/FAIL 判定を行う。
    - CLI オプション --from / --to / --db をサポート。環境変数 PAPER_TRADING_SQLITE_PATH を利用可。
    - 複数の閾値（稼働率 99%、成立率 90% など）を定義して評価する。
- 研究/ファクター計算（初期）
  - research/factor_research.py: DuckDB 接続を受け取るファクター計算モジュールを追加（モメンタム等の計算方針・定数定義を含む）。
    - prices_daily / raw_financials テーブルのみ参照し、Zスコア正規化などに連携する設計（関数群を分離して実装予定）。
- パッケージ情報
  - __init__.py にてパッケージ名、バージョン（0.1.0）、主なサブパッケージを定義。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

## 既知の注意点 / TODO
- portfolio/risk_adjustment.py:
  - apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過少見積りされうる旨の TODO コメントあり。将来的にフォールバック価格（前日終値等）を導入することが検討されています。
- research/factor_research.py:
  - ファイル末尾で未完の関数（calc_momentum の実装途中）が存在するように見えます。研究モジュールは今後の実装拡張が必要です。
- process_priority および CPU affinity の設定は権限不足やプラットフォーム非対応時に警告でスキップされる設計ですが、本番運用時の権限要件・挙動確認が必要です。
- validate_config の YAML パース検証は PyYAML の有無に依存します。CI で PyYAML を含めることを推奨します。
- .env 自動ロード挙動:
  - デフォルトでプロジェクトルートを検出して .env/.env.local を自動で読み込みますが、テストなどでこれを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

──
参考コマンド:
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証:      python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

(注) 本 CHANGELOG はコードの内容から推測して作成しています。実際の変更履歴／コミット履歴がある場合はそれに基づいて更新してください。
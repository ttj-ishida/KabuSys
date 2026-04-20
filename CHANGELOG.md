# Changelog

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠します。

新しいリリースはセマンティックバージョニングに従います。

## [Unreleased]

（現在のスナップショットから推測される主要機能を v0.1.0 として初回リリースにまとめています。将来の差分はここに記載します。）

---

## [0.1.0] - 2026-04-20

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading モードでは MockBrokerClient を使用し、paper-trading 専用 DB（デフォルト: data/paper_trading.db）へ記録する。本番用の実行 PID ファイル管理、停止フラグ検知による安全停止処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。監視は環境に関わらず本番用 sqlite_path を使用する仕様になっている。
- 設定関連
  - config.py: .env 自動読み込み機能（.env / .env.local）を実装。プロジェクトルートの自動検出（.git または pyproject.toml を基準）、.env の厳密なパース（クォート／エスケープ／コメント処理）を追加。Settings クラスを導入し、各種設定（DB パス、API トークン、監視閾値、環境判定等）をプロパティ経由で取得可能に。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加（鍵設定のマスク、デフォルト値、選択肢サポートなど）。
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。--strict オプションで警告も失敗扱いにできる。YAML の存在／パース確認や本番環境向けガードチェック（LINE 設定や Kill Switch の扱い等）を実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（スコア順）、等金額/スコア加重の重み計算を提供。
  - portfolio/position_sizing.py: position size（株数）計算ロジックを実装。risk_based / equal / score の配分方式、lot（単元）での丸め、aggregate キャップ時のスケーリングと端数処理を含む。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（既存ポジションを考慮）、市場レジームに応じた乗数（bull/neutral/bear）を実装。
  - portfolio/__init__.py: 上記関数群を公開。
- utils
  - utils/logging_setup.py: ルートロガー共通設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックを用意。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。psutil の権限不足や未対応 OS を検出して安全にフォールバックする。start-up スクリプトは起動直後に優先度を high にするよう呼び出す。
- 監視・検証ツール
  - monitoring.monitoring_db への初期化呼び出しを run_monitoring/run_execution の起動時に追加（監視テーブルが存在することを保証）。
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を算出し Pass/Fail を判定する。閾値はソース内定義（稼働率 99%、FILL 90%、SEND 95%、P95 200ms）。
- research
  - research/factor_research.py: DuckDB 上の過去価格・財務テーブルを利用してモメンタム、ボラティリティ、バリュー等のファクターを計算するモジュールの骨子を追加（モメンタム計算などの設計と定数を定義、実装途中）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 重要な移行・運用上の注意
- .env の自動読み込みはデフォルトで有効。自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利です）。
- run_execution は paper_trading モード（KABUSYS_ENV=paper_trading）で paper 用データベースを分離して使用します。本番データと完全に分離するため、紙トレード時は PAPER_TRADING_SQLITE_PATH を確認してください。
- run_monitoring は Monitoring に対して常に settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（正の整数を指定。無効な値は 60 秒にフォールバック）。
- プロセス優先度設定は psutil を用いて行います。権限不足や未対応プラットフォームでは警告を出してスキップします。サービス運用環境では権限（systemd ユニット設定等）を確認してください。
- ログ出力先のディレクトリ作成に失敗してもアプリはコンソール出力のみで継続します。ログファイル出力を利用する場合は LOG_DIR を適切に設定し、実行ユーザーに書き込み権限があることを確認してください。
- validate_config と config_setup を使って事前に設定検証・初期化を行うことを推奨します（特に KABUSYS_ENV=live の場合は追加ガードや通知設定を必須確認）。

### Removed / Deprecated
- （初回リリースのため該当なし）

---

メンテナンス／将来追加予定（参考）
- research/factor_research の完全実装（複数ファクターの計算と正規化パイプライン）。
- 銘柄別単元（lot_size）を stocks マスタから読み込む拡張。
- ExecutionEngine の詳細実装改善（再接続・リトライ方針、より詳細なリスク管理ルールの外部化）。
- ロギングの Structured Logging（JSON）オプション追加や外部ローテーション設定の洗練。

[0.1.0]: 0.1.0
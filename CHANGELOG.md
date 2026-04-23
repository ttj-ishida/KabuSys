CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。主要なカテゴリ: Added / Changed / Fixed / Deprecated / Removed / Security。

Unreleased
----------

### Added
- 設定検証コマンドラインツールを追加: python -m kabusys.validate_config
  - .env と config/*.yaml の存在・基本的な妥当性を起動前にチェック。
  - --strict オプションを追加。警告も失敗（exit 1）扱いにできる。
  - PyYAML 未インストール時は YAML 内容検証をスキップし警告を出力。
  - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）。
- 対話式環境設定ウィザードを追加: python -m kabusys.config_setup
  - .env の初期作成・更新をサポート。シークレットマスクや選択肢サポートを含む。
  - .env をテンプレート形式で書き出す機能を提供。
- 設定管理 (kabusys.config) を実装
  - .env パーサーを実装（export KEY=val 形式対応、クォート文字列のエスケープ処理、インラインコメントの適切な扱い）。
  - 自動 .env ロードを実装（優先度: OS 環境変数 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、環境変数から型変換・バリデーション済みの設定をプロパティとして取得可能（DB パス、ログレベル、env 判定、paper_trading 用 DB 等）。
- 実行スクリプトを追加/整備
  - run_execution.py: ExecutionEngine 起動用エントリポイント（paper_trading 時は専用 DB を使用、PID ファイル・kill.flag の扱いを含む）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動用スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能、監視は常に本番 sqlite_path を使用）。
- 発注系コア実装
  - OrderRecord（状態機械）を実装。許可される状態遷移を定義し、不正遷移時に例外を投げる。
  - OrderManager を実装し、create/send/sync/cancel のフローおよびクラッシュ耐性（2 相的な永続化戦略）を適用。
  - ExecutionEngine 実装: シグナル読み込み → Gate1/2 のリスクチェック → 発注 → push/drain ループ → Gate3（ドローダウン監視）までのフローを提供。
  - 発注に関連する監視イベントの記録（監視 DB へのログ）を組み込み（失敗時は警告を出し発注フローは継続）。
- kabu station 用クライアント (KabuStationClient) を実装
  - httpx を用いた同期 REST クライアント。トークンの遅延取得・401 リトライをサポート。
  - HTTP エラーやタイムアウトを BrokerAPIError / RateLimitError に変換。
  - kabu ステータスコード -> 内部ステータスへのマッピングを実装。
- その他ユーティリティ
  - プロセス優先度設定（set_process_priority）やログセットアップを呼び出して起動時の環境整備を行う（run_* スクリプト内で利用）。
  - 実行中の停止フラグ（data/stop_requested.flag）検出による安全なシャットダウン。

### Changed
- （Unreleased — 主に初期実装の追加・整備に相当）設定読み込み・検証ロジックを厳密化:
  - LOG_LEVEL / KABUSYS_ENV の妥当性チェックを追加し、不正値はエラー/例外にする（validate_config では警告としても報告）。
  - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在確認を行い、存在しない場合に警告出力。

### Fixed
- -（現在の差分から推測される軽微な堅牢化）MONITOR_POLL_INTERVAL の不正値に対してデフォルトにフォールバックするように改善（0 以下や非整数入力対策）。

0.1.0 - 2026-04-23
-----------------

初期リリース。上記の主要機能群を含む最初の公開バージョン。

### Added
- プロジェクトのコア機能一式を追加:
  - 環境設定 / .env ローダー / Settings
  - 対話式設定ウィザード (config_setup)
  - 設定検証 CLI (validate_config)
  - 実行用スクリプト（run_execution, run_monitoring）
  - 発注エンジン（ExecutionEngine）、Order 管理（OrderRecord / OrderManager）、リスク管理連携
  - kabu station REST クライアント（KabuStationClient）
  - 監視・ログ記録の土台（監視 DB 初期化呼び出し等）
- バージョン情報をパッケージに設定: __version__ = "0.1.0"

### Fixed
- 初期実装段階でのクラッシュ安全性・永続化順序（OrderManager の send_order における broker_order_id の先行コミット等）を考慮した設計を反映。

Security
--------
- .env を決して Git にコミットしないようにウィザードの出力ヘッダに注意書きを追加。

Notes / Migration
-----------------
- 本番運用時は必ず validate_config を実行し、KABUSYS_ENV=live での警告項目（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）を確認してください。
- 自動で .env を読み込む仕組みが導入されています。テストや CI 環境で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading モードでは監視や発注に使用する SQLite が本番と分離されます（PAPER_TRADING_SQLITE_PATH を参照）。

問い合わせ・貢献
----------------
バグ報告や機能要望はリポジトリの Issues にお願いします。貢献は歓迎します。
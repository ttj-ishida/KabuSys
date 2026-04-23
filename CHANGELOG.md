# Keep a Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に従います。  

※この CHANGELOG はコードベースの内容から推測して作成した初期リリース記録です。

全般
- リリース日: 2026-04-23
- バージョン: 0.1.0

## [0.1.0] - 2026-04-23

### Added
- プロジェクト初回リリース相当の基本機能を追加。
- 環境設定・管理
  - Settings クラスを実装。環境変数からアプリ設定を取得する統一インターフェイスを提供（kabusys.config）。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。読み込み順は OS 環境変数 > .env.local > .env。自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイルのパースロジックを実装（export プレフィックス、引用符、エスケープ、インラインコメント対応）。
  - Settings に多数のプロパティを追加（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE 関連、DB パス、paper_trading 用設定、PID/KILL フラグ、閾値、env/log_level 等）。PAPER_FILL_MODE の値検証を実装。
  - settings インスタンスをモジュールレベルで提供。

- 設定ウィザード CLI
  - 対話式の .env 生成/更新ツールを追加（kabusys.config_setup）。
  - 質問テンプレート（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を用意。
  - 既存 .env の読み込み・表示、シークレット値のマスク表示、保存前確認を実装。
  - .env の書き込みフォーマットと注意コメントを出力。

- 設定検証 CLI
  - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加（kabusys.validate_config）。
  - 必須・任意の環境変数チェック、KABUSYS_ENV の妥当性チェック（development/paper_trading/live）、LOG_LEVEL の妥当性チェック、DB パスの存在チェック（親ディレクトリの有無を警告）、config/*.yaml の存在確認と（PyYAML がインストールされていれば）パース検証を実装。
  - KABUSYS_ENV=live 時の追加ガード（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の危険な値など）を実装。
  - --strict オプションで警告を失敗扱いにする機能を追加。

- 実行・監視ランナー
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）を追加。プロセス優先度設定、PID ファイル管理、stop フラグ検出、DB 初期化、スレッドによるエンジン実行・停止処理を実装。
  - Monitoring ポーリングランナー（kabusys.run_monitoring）を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。

- 発注系コア
  - OrderRecord: 注文状態モデルと状態遷移ロジックを実装（kabusys.execution.order_record）。状態遷移の許可表と InvalidStateTransitionError を定義。
  - OrderManager: 外向きの注文管理 API を実装。create/send/sync/cancel の流れを実装し、DuplicateOrderError を導入。send_order における二相永続化（OrderSent を先にコミット、broker_order_id を保存してから OrderAccepted に遷移）や OrderSentPendingError の扱いなど、クラッシュ後の再同期（Reconciliation）設計を反映。
  - ExecutionEngine: シグナル読み取り（DuckDB）、Gate 1/2/3 による多段リスクチェック、発注ループ、WebSocket push ドレイン、kill_switch（全 active 注文キャンセル）を実装。paper_trading では専用 SQLite（paper_sqlite_path）を使用する挙動をサポート。position_entries への書き込み、監視 DB への発注イベントログ出力（存在する場合）も実装。
  - Reconciler を起動時に呼び出す仕組みを設置（存在する場合のみ実行）。発注ループは複数例外を想定して堅牢化（例外時ログ・継続）。

- ブローカー API クライアント
  - KabuStationClient を実装（kabusys.execution.kabu_client）。httpx を用いた同期 REST クライアント。トークン取得の遅延初期化、自動再取得（401 時）、リトライロジックを実装。
  - レスポンスの JSON パース失敗、ネットワーク/タイムアウト、401/429/5xx のエラーを BrokerAPIError / RateLimitError 等にマッピング。
  - WebSocket（push）受信用の stream_push を想定した設計（WebSocket の受信を別スレッドで処理し、ExecutionEngine の _push_queue に投入する想定）。

- DB / 監視関連
  - monitoring_db 初期化ユーティリティを使用するフロー（init_monitoring_db を run_monitoring/run_execution で呼び出し）。
  - DuckDB と SQLite を用途に応じて使い分ける設計を反映。

- ユーティリティ
  - ログ設定、プロセス優先度設定ユーティリティとそれを呼び出す起動スクリプトを追加（setup_logging, set_process_priority を呼ぶ）。

### Changed
- （初回リリースのため変更履歴なし）  

### Fixed
- （初回リリースのため修正履歴なし）  

### Security
- 本リリースでは特段のセキュリティ修正は記録されていませんが、API トークン/シークレットは .env に格納する想定であり、config_setup にも「.env を絶対に Git にコミットしない」旨の注意を埋め込み済みです。

### Notes / 備考
- config/*.yaml の内容検証には PyYAML が必要。未インストール時は YAML 内容チェックはスキップされ、警告が出ます。
- Settings の env/log_level 等は厳密に検証され、無効値は ValueError を発生させます。validate_config は値検証のサニティチェック（警告/エラー）を行いますが、Settings のプロパティは実行時に例外を投げるため、起動前に validate_config を実行して設定を確認することを推奨します。
- ExecutionEngine のセッション制御（時刻ベースのシグナル処理/ドレインループ）や kill.flag の扱いは運用リスクにかかわるため、KABUSYS_ENV=live のときは validate_config による注意喚起を必ず確認してください。
- 本 CHANGELOG はコードベースの解析に基づく初期リリース向け推測ドキュメントです。実際のリリースノート作成時は変更点を追加/調整してください。

--- 

今後のリリースでは各コンポーネント（ExecutionEngine、OrderManager、KabuStationClient、monitoring 等）の改良点（例: 非同期対応、リトライ改善、監視項目の追加、API レスポンス処理の拡張）やバグ修正を個別に記載していくことを想定しています。
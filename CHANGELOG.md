CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています（簡易版）。
この CHANGELOG は提供されたコードベースの内容から推測して作成したもので、実際のコミット履歴ではありません。

Unreleased
----------

- （現時点のスナップショット。リリース予定の変更はここに記載します）

0.1.0 — 初回リリース
--------------------

Added
- 基本機能を実装（日本株自動売買システム「KabuSys」初期実装）
  - パッケージ初期バージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 環境設定関連
  - Settings クラスを実装し、環境変数経由で設定を取得可能に（src/kabusys/config.py）。
  - .env 自動読み込み機構を実装（プロジェクトルート検出に基づく。.env / .env.local の読み込み順を尊重。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
  - .env の行パーサを強化（export プレフィックス、クォート文字・エスケープ対応、インラインコメント取り扱いなどをサポート）。
  - PAPER_FILL_MODE、DBパス、ログレベル等の設定プロパティを提供（paper_trading 用 DB 分離含む）。
- 設定ウィザード CLI
  - 対話式ウィザードで .env を作成・更新するツールを追加（src/kabusys/config_setup.py）。
  - デフォルト値、選択肢、シークレット表示（マスク）をサポートし、.env をテンプレート形式で書き出す機能を提供。
- 設定検証 CLI
  - 起動前に .env / config/*.yaml を検証する CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、PyYAML の有無に応じた YAML 検証を実装。--strict モードで警告も失敗扱いに。
- 実行プロセス起動スクリプト
  - 実行エンジン起動スクリプト（run_execution）を追加（src/kabusys/run_execution.py）。
  - 監視プロセス起動スクリプト（run_monitoring）を追加（src/kabusys/run_monitoring.py）。MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応。
- 発注 / 実行基盤
  - ExecutionEngine（シグナルプル型発注エンジン）を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理ウィンドウ（デフォルト 8:50–9:10）、push ドレインループ（9:10–15:30）を実装。
    - kill.flag による起動拒否 / 起動時クリア（KILL_FLAG_CLEAR_ON_START）対応、PID ファイル書き出し、WebSocket push 処理、Gate1/2/3 によるリスクチェックなどを実装。
    - 発注成功時の position_entries 更新（DuckDB）や監視 DB へのログ記録のフックを提供。
  - OrderRecord：状態遷移を厳密に管理する状態機械モデルを実装（src/kabusys/execution/order_record.py）。
    - 許可遷移定義、InvalidStateTransitionError、transition_to による更新（更新時刻自動設定）を実装。
  - OrderManager：外向き API（create/send/sync/cancel）を実装（src/kabusys/execution/order_manager.py）。
    - DuplicateOrderError、2相永続化（OrderSent 前後の DB 更新戦略）によるクラッシュ安全性向上。
    - broker 側の pending／拒否／送信後の状態同期ロジックを実装。
  - Reconciler / RiskManager 等と連携するためのフックを実装（ExecutionEngine 内で使用）。
- Broker クライアント（kabu station）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期的 REST クライアント。トークン取得・自動再取得、HTTP 401 のリトライ、429 のレートリミット判定、タイムアウト・ネットワーク例外の BrokerAPIError 変換を実装。
    - WebSocket push（stream_push）に対応する形で push を受け取り ExecutionEngine の _push_queue に供給する設計をサポート（存在チェックで非対応ブローカーをスキップ）。
- DB / 監視関連
  - monitoring 用 SQLite 初期化ユーティリティと SystemMonitor（run_monitoring で使用）を参照する構成を導入（run_monitoring, run_execution）。
  - duckdb を分析 DB として使用する組み込み。

Changed
- 設計上の注意点（明記）
  - paper_trading 環境では本番の監視 DB を共有せず、paper_trading 用 SQLite を使用するように分離（settings.paper_sqlite_path）。
  - ログ設定・プロセス優先度設定（high）を起動時に実行することで、監視／実行プロセスの優先度を確保。
  - ExecutionEngine のセッション制御は thread + Event ベースで実装し、外部フラグで安全に停止できるようにした。

Fixed / Improved
- .env 読み込みの堅牢化
  - ファイル読み込み失敗時に warnings.warn を発行して処理を継続するように変更（I/O エラーで落ちない）。
  - OS 環境変数を保護する protected 引数を導入し、.env.local で OS 環境を意図せず上書きしないようにした。
- 発注フローのクラッシュ復旧性
  - send_order の実装で OrderSent の永続化を broker 呼び出し前に行い、broker_order_id を先にコミットする二相的更新を採用。これによりリコンシリエーションで状態復元可能。
  - OrderSentPendingError の取り扱いを明確化（broker が注文番号のみ返すケースを DB に残し、呼び出し元へ例外を伝播）。
- 設定検証の充実
  - validate_config にて必須/任意環境変数のチェック、プレースホルダ検出（"_here" / "your_value"）や KABUSYS_ENV=live に対する注意喚起を追加。
  - PyYAML 未インストール時の挙動を警告し、パース検証をスキップするように改良。

Security
- .env を絶対にリポジトリにコミットしない旨を生成される .env ヘッダーに明記（config_setup が生成する .env の冒頭コメント）。

Internal / Developer Notes
- 多くのモジュールで明示的に型注釈を導入（-> 型安全性向上）。
- テスト容易性のため、設定の自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- 設定ウィザードと検証ツールを用意して初期導入の UX を改善。

既知の制限（推測）
- KabuStationClient は現時点で同期実装（httpx.Client）。将来的な非同期化は httpx.AsyncClient への切り替えで対応可能としている。
- 一部の外部依存（PyYAML、kabuステーション環境、DuckDB、sqlite3）が必要。validate_config は PyYAML がない場合に YAML 検証をスキップするが、完全な検証のためには PyYAML を推奨。

クレジット
- この CHANGELOG は提供されたソースコードの解析に基づく推測的な変更履歴です。実際のコミットメッセージや差分ログに基づくものではありません。必要ならば実際の git 履歴から正確な CHANGELOG を生成できます。
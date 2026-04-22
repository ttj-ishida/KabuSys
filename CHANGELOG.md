# Changelog

すべての注目すべき変更点を記載します。本ファイルは「Keep a Changelog」準拠の形式で作成されています。

フォーマット:
- 変更種別: Added, Changed, Fixed, Deprecated, Removed, Security
- 各エントリは影響のある機能やファイル名を挙げて説明しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-22
初回リリース — KabuSys のコア機能群を実装。

### Added
- 環境/設定管理
  - Settings クラスを追加し、環境変数から各種設定を取得するプロパティを実装（src/kabusys/config.py）。
    - J-Quants / kabuステーション / LINE / DB パス / PID / Kill Switch / モニタリング閾値等をプロパティで提供。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を行い、不正値は ValueError を投げる。
  - .env 自動読み込み機構を追加（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - 読み込み順: OS 環境変数 > .env.local > .env。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（src/kabusys/config.py）。
  - .env の柔軟なパース実装（export プレフィックス、クォート内エスケープ、行末コメント処理に対応）（src/kabusys/config.py）。

- 環境設定ウィザード CLI
  - 対話式ウィザードで .env の生成/更新を支援するツールを追加（src/kabusys/config_setup.py）。
    - J-Quants/Kabu/DB/LINE/ログレベル/kill フラグ等の項目を定義。
    - シークレットをマスク表示、既存 .env の読み込みとデフォルトをサポート。
    - 保存フォーマットのテンプレートを用意（.env 生成）（src/kabusys/config_setup.py）。

- 設定検証 CLI
  - 起動前に .env や config/*.yaml の不足や設定ミスを検出する validate_config CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在チェックおよび（PyYAML があれば）パース検証。
    - --strict フラグにより警告を FAIL として扱う機能を提供。
    - プレースホルダ（"_here" や "your_value"）の検出で警告を出す。

- 実行系スクリプト
  - ExecutionEngine 起動スクリプト（run_execution）を追加（src/kabusys/run_execution.py）。
    - プロセス優先度設定、PID/停止フラグ管理、paper_trading と本番 DB の分離、監視 DB 初期化などを行う。
  - Monitoring 用ポーリングスクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検出で安全に終了。

- 発注ロジック（Execution）
  - ExecutionEngine（シグナル読み込み・発注ループ・WebSocket push ドレイン等）を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（8:50-9:10）と push ドレイン（9:10-15:30）を分離。
    - Gate1/2/3 のリスクチェックを統合し、Gate で NG の場合の挙動を明確化（kill_switch 発動等）。
    - WebSocket push を受け取り同期処理を行う仕組み（_push_queue）。
    - PID ファイル管理、kill.flag の既存検出と起動動作（KILL_FLAG_CLEAR_ON_START サポート）。
    - DuckDB からのシグナル読み込み、position_entries の更新を行う。

- 注文状態管理 / 発注フロー
  - OrderRecord（状態遷移ロジックを含む純粋なデータモデル）を実装（src/kabusys/execution/order_record.py）。
    - 明確な状態列挙 OrderState と許可遷移テーブルを定義。InvalidStateTransitionError を提供。
    - transition_to により updated_at を自動更新し、必要なフィールドの更新をサポート。
  - OrderManager（外向き API）を実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id の重複チェック（DuplicateOrderError）、DB 保存、UUID で client_order_id を付与。
    - send_order: 送信前に OrderSent を DB に永続化 → broker API 呼び出し → broker_order_id を先に保存 → OrderAccepted へ遷移（2相永続化戦略）。OrderRejected/OrderSentPending の扱いを実装。
    - sync_order: broker 側のステータスからローカル状態を同期。部分約定の進行を反映。
    - cancel_order: キャンセル不可能状態の判定（終端状態チェック）と broker への cancel 呼び出し。
    - list_active / get / update / save などは OrderRepository と連携（order_repository は別モジュール）。

- ブローカークライアント（kabu station）
  - KabuStationClient を追加（src/kabusys/execution/kabu_client.py）。
    - HTTP クライアントに httpx（同期）を使用。トークン取得の遅延初期化、自動再取得（401 時のリトライ）を実装。
    - レスポンスの JSON パース失敗・ネットワークエラー・タイムアウト等を BrokerAPIError 等に変換。
    - kabu station のステータスコードを内部ステータス（open/partial/filled/cancelled/rejected）にマップする辞書を提供。
    - 429（Rate Limit）と 5xx を明示的にエラー化。
    - （将来的な Async 対応を想定した設計）

- 監視 / DB 初期化
  - monitoring 用 DB 初期化ユーティリティと SystemMonitor（run_monitoring で利用）を統合（参照: src/kabusys/run_monitoring.py）。

### Changed
- データベース運用方針
  - paper_trading モードでは paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番監視 DB と完全分離する設計に変更（src/kabusys/config.py, src/kabusys/run_execution.py）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明記（src/kabusys/run_monitoring.py）。

- 安全性 / クラッシュ耐性の改善
  - send_order における「OrderSent を先に永続化してから broker 呼び出し」を明確に実装し、クラッシュ時に OrderSent レコードが残ること、broker_order_id の永続化が Reconciliation に有利である旨をドキュメント化（src/kabusys/execution/order_manager.py）。
  - OrderSentPendingError を導入し、ブローカーが注文番号は返すが約定しないケースを明示的に扱う。

- .env パースの堅牢化
  - クォートされた値内のバックスラッシュエスケープ対応や行末コメントの扱いなど、より現実的な .env フォーマットをサポート（src/kabusys/config.py）。

### Fixed
- 設定検証の利便性向上
  - validate_config において PyYAML が未インストールの場合は YAML パース検証をスキップしつつ警告を出すようにして、環境による起動阻害を回避（src/kabusys/validate_config.py）。
  - validate_config はプレースホルダ値の検出（"_here", "your_value"）で警告を出すようになり、初期設定ミスを早期発見可能にした。

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数の自動読み込み時、OS 側の既存環境変数を保護するため protected キーセットを導入（src/kabusys/config.py）。これによりシステム環境変数を .env で誤って上書きするリスクを低減。

---

注:
- 上記は現行コードベース（src/kabusys/*.py）から推測可能な変更点・機能説明をまとめたものです。実際のリリース履歴や過去バージョンとの差分はリポジトリのコミット履歴を参照してください。
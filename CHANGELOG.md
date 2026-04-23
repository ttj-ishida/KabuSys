Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。
この CHANGELOG は与えられたコードベースの内容から推測して作成しています（コミット履歴ではなくソースコードの構造・実装に基づき記載）。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-----------

- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-23
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- 設定管理:
  - 環境変数/ .env ファイルを自動読み込みする設定モジュールを追加（kabusys.config）。
  - .env パーサは export プレフィックス、クォート文字列、エスケープ、インラインコメントの扱いに対応。
  - OS 環境変数を保護する override/protected ロジックを搭載（.env/.env.local ロード順の実装）。
  - Settings クラスを提供し、各種設定値（J-Quants トークン、kabu API パスワード、DB パス、PID/KILL フラグ、閾値等）へ型付きアクセスを提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
- 設定ウィザード:
  - 対話式 .env 作成/更新ツール（kabusys.config_setup）を追加。
  - 項目定義（実行環境、J-Quants/Kabu 認証、DB パス、LINE 通知、ログレベル、Kill Switch クリア設定など）と書き出しテンプレートを提供。
- 設定検証 CLI:
  - 起動前に .env と config/*.yaml の設定を検証するツール（kabusys.validate_config）を追加。
  - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パス親ディレクトリ確認、YAML パーサ（PyYAML）有無でのスキップ、実行環境が live の場合の追加ガードチェックを実装。
  - --strict オプションで警告を失敗扱いにできる exit コードを提供。
- 実行系ランチャー:
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）を追加。paper_trading モードでは paper_trading 用 SQLite を使用して本番 DB から分離。
  - Monitoring 用ランチャー（kabusys.run_monitoring）を追加。監視は実行環境にかかわらず本番 sqlite_path を使用。
  - 両ランチャーともプロセス優先度設定や PID/停止フラグ処理を組み込み。
- 実行エンジン:
  - ExecutionEngine（kabusys.execution.execution_engine）を実装。
  - シグナルの読み出し（DuckDB）、Gate1/2/3 によるリスクチェック、発注ループ（8:50–9:10）、WebSocket プッシュドレイン（9:10–15:30）などセッション制御ロジックを実装。
  - push 通知をキューに入れて処理する WebSocket スレッド連携（broker.stream_push を利用）。
  - PID ファイル管理、kill.flag の存在チェックと KILL_FLAG_CLEAR_ON_START による起動時クリア挙動をサポート。
- 発注周り（Execution サブシステム）:
  - OrderRecord（状態遷移ロジック）を実装（状態列挙、許可遷移、InvalidStateTransitionError）。
  - OrderManager（create/send/sync/cancel）を実装。DB（OrderRepository）との連携で二相永続化パターンを採用し、クラッシュ時の整合性を考慮。
    - send_order は OrderSent を先に永続化してから broker を呼び、broker_order_id を先にコミット → OrderAccepted に遷移する等のフローを実装。
    - OrderSentPendingError（注文保留）を扱い、broker_order_id を保存したまま OrderSent の状態で残す。
    - DuplicateOrderError を検出（signal_id の重複／DB 制約）。
  - Reconciliation を想定した同期ロジック（sync_order）を実装。broker 側ステータスを内部状態へマッピングし、部分約定の進行で filled_qty / avg_fill_price を更新。
  - cancel_order は終端状態を考慮し、必要に応じて broker の cancel API を呼ぶ。
- ブローカークライアント:
  - KabuStationClient（kabu station REST API 実装）を追加（httpx ベース、同期）。トークン管理（遅延取得・401 リトライ）、エラーハンドリング（タイムアウト、ネットワークエラー、429 レート制限、5xx）を実装。
  - 推奨接続先とデフォルト base_url を明記（ローカルの kabusapi を想定）。
- リスク管理 / モニタリング連携:
  - ExecutionEngine と OrderManager が RiskManager、Reconciler、MonitoringDB、DuckDB と連携するためのフックを用意。
  - 発注レイテンシを監視 DB に記録する処理（監視 DB が有る場合）を実装。
- 監視（Monitoring）:
  - SystemMonitor を使った監視ループ起動スクリプトを追加（MONITOR_POLL_INTERVAL 環境変数で間隔上書き、デフォルト 60 秒）。停止フラグ検知で安全に終了。
- その他ユーティリティ:
  - ロギング、プロセス優先度設定ユーティリティ参照（setup_logging, set_process_priority）が組み込まれた設計。
  - コード内に多数の安全ガード（例: kill.flag、PID ファイルの管理、例外ログ、リトライ/回復パターン）を導入。

Changed
- （初回リリースのため、過去変更の履歴はなし）

Fixed
- （初回リリースのため、過去バグ修正履歴はなし）

Deprecated
- なし

Removed
- なし

Security
- なし

注記
- この CHANGELOG は与えられたソースコードから機能・実装を読み取り推測して作成しています。実際のリリースノートはコミット履歴やリリース管理者の記録に基づいて作成してください。
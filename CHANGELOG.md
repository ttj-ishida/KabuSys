# Keep a Changelog
すべての重要な変更をこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-23
初期リリース。以下の主要機能と実装を含みます。

### 追加
- 全体
  - パッケージ初期版を追加。バージョンは kabusys.__version__ = "0.1.0"。
- 設定・環境変数管理
  - 環境変数および .env ファイルを読み込む Settings クラスを実装（src/kabusys/config.py）。
    - OS 環境変数 > .env.local > .env の優先順位で自動ロード（自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート）。
    - .env パーサーは export 形式・シングル／ダブルクォート・バックスラッシュエスケープ・行末コメント等を正しく処理。
    - 必須変数取得時に未設定なら ValueError を投げる _require() を提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）。
    - PAPER_FILL_MODE 等、一部設定値の検証（許容値チェック）を行うプロパティを提供。
- 設定ウィザード CLI
  - 対話式ウィザードで .env を作成／更新するツールを追加（src/kabusys/config_setup.py）。
    - 秘匿項目はマスク表示。選択肢・デフォルトのサポート。
    - 既存 .env 読み込み、確認プロンプト、ファイル書き出しロジックを実装。
    - 書き出される .env のテンプレート／コメント付きヘッダを生成。
- 設定検証 CLI
  - 起動前に .env と config/*.yaml の基本的な検証を行う CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、プレースホルダ値検出、KABUSYS_ENV や LOG_LEVEL の値検証、DB パスの親ディレクトリ存在チェック等を実施。
    - PyYAML が利用可能なら config/*.yaml のパース確認も行う。
    - --strict オプションで警告を失敗として扱う。
- 実行スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - paper_trading 環境では paper_trading 用 SQLite を使用し、本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検知（data/stop_requested.flag）をサポート。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して永続化。
- Execution/注文ロジック
  - ExecutionEngine 実装（src/kabusys/execution/execution_engine.py）
    - シグナルの読み込み、Gate1/Gate2（リスクチェック）、発注フロー、push ドレインループ（WebSocket）を含む通し処理。
    - kill_switch、PID ファイル管理、Reconciliation 呼び出しや WebSocket スレッド管理等を実装。
    - 発注時のレイテンシ計測・監視DBへのログ（監視 DB が渡された場合）を考慮。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - OrderRecord と OrderRepository を組み合わせ、create/send/sync/cancel の外向き API を実装。
    - 重複注文検出（DuplicateOrderError）、二相永続化戦略（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新）を実装し、クラッシュ耐性を向上。
    - OrderSentPendingError ハンドリング（注文番号は発行されたが確定しないケース）に対応。
    - sync_order により broker 側ステータス取得とローカル状態同期を実装（部分約定の進行は差分更新で対応）。
    - cancel_order は終端状態の判定および broker 呼び出しの取り扱いを実装。
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態の列挙型 OrderState と許可遷移テーブルを定義。
    - 状態遷移検証（InvalidStateTransitionError）と更新ロジックを実装。updated_at を UTC で自動更新。
- ブローカークライアント
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx を利用した同期 REST クライアントを実装（トークン取得・自動再取得、401 リトライ、429/5xx のハンドリング、JSON パースエラーハンドリング）。
    - レスポンスコードに基づくエラー変換（RateLimitError, BrokerAPIError 等）を実装。
- その他ユーティリティ
  - モニタリング DB 初期化 / SystemMonitor 等（参照のみ、実体は別モジュール）を呼び出すためのインターフェース追加。
  - プロセス優先度設定およびログセットアップの呼び出しポイントを run_* スクリプトに組み込み。

### 変更
- （初期リリースのため該当なし）

### 修正
- （初期リリースのため該当なし）

### セキュリティ
- .env は絶対に Git にコミットしない旨の注記を config_setup の生成ファイルヘッダに明記。

---

注記:
- 本 CHANGELOG はソースコードからの推測に基づく要約です。実際の仕様や外部モジュールの振る舞い（例: monitoring_db の詳細、broker API の完全な挙動など）は該当モジュールや外部依存に依存します。
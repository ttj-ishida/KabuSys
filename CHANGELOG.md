# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-04-22
初回公開リリース。

### 追加 (Added)
- 基本パッケージ情報を追加
  - パッケージバージョン: `__version__ = "0.1.0"`

- 環境設定管理
  - .env 自動ロード機能を導入（プロジェクトルートの .env / .env.local を読み込む）。
    - OS の既存環境変数は保護され、.env.local は上書きとして読み込まれる。
    - 環境変数の自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env ファイルの行パーサーを実装（引用符付き値、エスケープ、コメント処理、export 形式に対応）。
  - Settings クラスを追加し、環境変数から型付き設定値を提供。
    - J-Quants / kabuステーション / LINE / DB（DuckDB, SQLite）/ システム設定 等をプロパティで取得可能。
    - 値検証を行うプロパティ（`env`, `log_level`, `paper_fill_mode` など）を追加。無効値は例外を発生させる。
    - paper_trading 用の専用 SQLite パス（`paper_sqlite_path`）をサポート。
    - kill flag 関連設定（`kill_flag_path`, `kill_flag_clear_on_start` 等）をサポート。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを追加。`.env` の初期作成 / 更新を支援。
  - 多数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を定義し対話的に編集可能。
  - `.env` の読み書きロジックを実装（既存値の読み込み、シークレットのマスク表示、保存確認）。
  - 生成される .env テンプレートは Git にコミットしない旨を明記。

- 設定検証ツール CLI
  - `kabusys.validate_config` を追加。起動前に環境変数や config/*.yaml の不備を検出。
    - 必須環境変数チェック（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）。
    - `KABUSYS_ENV`, `LOG_LEVEL` 等の妥当性チェック。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック（自動作成の注意メッセージ）。
    - config/*.yaml の存在確認と PyYAML が存在すればパース検証（PyYAML 未インストール時はスキップで警告）。
    - `KABUSYS_ENV=live` 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意等）。
    - `--strict` オプションで警告も失敗扱いにするモードを提供。

- 実行用スクリプト
  - `run_execution.py` を追加。ExecutionEngine を起動するエントリポイント。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出、DB 接続の取り扱い（paper_trading 時の専用 DB 使用）を組み込む。
  - `run_monitoring.py` を追加。SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔オーバーライド（デフォルト 60 秒）、停止フラグ検出、DB 初期化を実施。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する点を明示。

- 発注関連コアコンポーネント
  - OrderRecord と状態遷移
    - 注文状態を列挙する OrderState 列挙体と、状態遷移許可表を実装。
    - `OrderRecord` データクラスを追加。状態遷移検証を行う `transition_to()` を実装し、不正遷移で `InvalidStateTransitionError` を発生。
  - OrderManager
    - `create_order`, `send_order`, `sync_order`, `cancel_order` の外向け API を実装。
    - create_order は signal_id に対する重複検査を行い重複時は `DuplicateOrderError` を返す。DB 制約違反（部分ユニーク）を DuplicateOrderError にマッピング。
    - send_order はクラッシュ安全性を考慮した二相永続化戦略を導入（OrderSent 保存 → broker 呼び出し → broker_order_id 保存 → OrderAccepted 更新等）。
    - OrderRejectedError / OrderSentPendingError の扱いを実装（pending は broker_order_id を永続化して OrderSent のまま残す）。
    - sync_order は broker 側の状態を照合して local レコードを同期（部分約定の更新や状態遷移の補正を含む）。
    - cancel_order は終端状態チェックの上で broker cancel を呼び出し、Cancelled に遷移。
  - ExecutionEngine
    - シグナル読み込み（DuckDB）→ Gate1/Gate2 チェック→ 発注フローの実装。
    - レート制限リトライ、Circuit Breaker の検出、API レイテンシ計測と監視 DB への記録（MonitoringDB が指定されている場合）。
    - WebSocket (kabu push) の受信スレッド実装（_websocket_worker）と push ドレイン処理（_drain_push_queue/_handle_push）。
    - Gate3（ポートフォリオメトリクス）チェックで NG の場合 kill_switch を発動。
    - kill_switch により全 active 注文をキャンセルしてループ停止。
    - セッション管理（発注時間帯 / ドレインループ / PID ファイル管理 / kill.flag ロジック）を実装。

- ブローカークライアント実装
  - KabuStationClient を追加（同期 httpx クライアントを使用）。
    - API トークン管理（遅延初期化、401 時の再取得とリトライ）を実装。
    - HTTP エラー / タイムアウト / ネットワーク例外を BrokerAPIError 系に変換。
    - レスポンスの JSON パース失敗を例外変換。
    - kabu ステーションの状態コード → 内部状態マップを導入。
    - レート制限 (429) を RateLimitError として扱う。

- モニタリング DB 初期化ユーティリティを導入（init_monitoring_db 呼び出しを実装、監視テーブルの存在を保証）。

- ユーティリティ
  - ロギングセットアップ / プロセス優先度設定を利用するエントリポイントとの統合（setup_logging, set_process_priority を使用）。

### 変更 (Changed)
- なし（初回リリースのため多数の新規追加が中心）。

### 修正 (Fixed)
- なし（初回リリース）。

### 注意事項 (Notes)
- .env は絶対にリポジトリにコミットしないでください（config_setup の出力にも明記）。
- 本番環境 (KABUSYS_ENV=live) では `KILL_FLAG_CLEAR_ON_START` をデフォルトの `0` のままにすることを推奨します。`1` の場合起動時に kill flag が自動クリアされます（危険）。
- validate_config の YAML 検証は PyYAML に依存します。PyYAML がインストールされていない環境ではパース検証はスキップされ警告となります。
- Execution/Monitoring は DuckDB と SQLite を使用します。適切な DB パスの親ディレクトリが存在するか確認してください（存在しない場合は起動時に自動作成される場合がありますが、注意が必要です）。

--- 

今後のリリースでは以下を予定しています（案）
- テストカバレッジの拡充（ユニット / 統合テスト）
- 非同期対応の HTTP クライアント実装（httpx.AsyncClient への移行）
- 監視/アラートの強化、CLI の改善（非対話モード等）
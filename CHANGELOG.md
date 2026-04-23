CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

リリース履歴
-----------

### 0.1.0 — 2026-04-23

初回公開リリース。主に設定管理、監視・実行エンジン、注文管理のコア機能を実装しています。

Added
- 基本バージョン情報を追加
  - パッケージバージョン: __version__ = "0.1.0"

- 設定読み込み・管理
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントの扱いに対応）。
  - Settings クラスを実装し、環境変数をプロパティとして提供（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_fill_mode など）。
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等で不正値は ValueError を送出）。

- 設定ウィザード CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を提供。
  - シークレット項目はマスク表示、選択肢・デフォルト値・説明をサポート。
  - 生成される .env にヘッダと注意書きを含める（.env を Git にコミットしない旨の注意）。

- 設定検証 CLI
  - validate_config.py: .env および config/*.yaml（存在確認と PyYAML パーサがあればパース検証）を起動前に検出するツールを実装。
  - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パス親ディレクトリ存在チェック、KABUSYS_ENV=live 時の追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START の警告）など。
  - --strict オプションで警告も失敗扱いにできる。

- 実行 / 監視のエントリスクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - paper_trading 環境では paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検知（data/stop_requested.flag）等を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明記。

- 注文状態管理（State Machine）
  - order_record.py: OrderRecord データモデルと状態遷移ロジックを実装。
    - OrderState Enum（created, sent, accepted, partial, filled, closed, cancelled, rejected）と許可遷移テーブルを定義。
    - 不正遷移時は InvalidStateTransitionError を送出。
    - transition_to() により更新時刻自動更新、オプションフィールド（broker_order_id、filled_qty、avg_fill_price、error_message）更新対応。

- 注文の上位 API
  - order_manager.py: OrderManager を実装（create_order / send_order / sync_order / cancel_order）。
    - create_order は signal_id のアクティブ重複を検出して DuplicateOrderError を送出。
    - send_order はクラッシュ耐性を考慮した 2 相永続化アプローチを採用:
      1) OrderCreated → OrderSent を DB に保存（コミット）
      2) broker API 呼び出し
      3a) 成功時: broker_order_id を先に保存（state は Sent のまま）
      3b) OrderAccepted に遷移して保存
      - OrderRejectedError は Rejected に遷移して保存
      - OrderSentPendingError（ブローカが注文番号は返すが約定しない/保留）を呼び出し元に伝播しつつ broker_order_id を保存
    - sync_order は broker 側ステータスを取得して DB と同期し、部分約定の進行はフィールド更新で対応。
    - cancel_order は取消不可能な状態をチェックし、可能なら broker に cancel を投げて Cancelled に遷移。

- ExecutionEngine（発注エンジン）
  - execution_engine.py: シグナル取得→リスクゲート→発注→push ドレインのフローを実装。
    - EngineConfig でターゲット日と時間窓（発注開始/締切/市場終了）を指定。
    - _process_signals(): size_multiplier 適用、Gate1（シグナルレベル）、Gate2（実行レベル・レート制限・サーキットブレーカー）、発注処理（create/send）、発注レイテンシ計測と監視DB への記録。
    - _drain_push_queue / _handle_push: push 通知から sync_order 実行、Gate3（ドローダウン）チェックと kill_switch 発動。
    - kill_switch(): 全 active 注文をキャンセルしループ停止（外部からの stop() はエイリアス）。
    - WebSocket ワーカーをサポート（broker が stream_push を提供する場合のみ起動）。
    - 起動時に kill.flag 検査と KILL_FLAG_CLEAR_ON_START による自動クリアの挙動（PID 書き込み前に検査）。

- ブローカークライアント（kabu station）
  - kabu_client.py: KabuStationClient を実装（httpx 同期クライアント）。
    - トークン取得の遅延初期化と自動再取得（401 時）、認証ヘッダー付きリクエストラッパーを実装。
    - レスポンス JSON パース失敗・タイムアウト・ネットワーク例外は BrokerAPIError に変換。
    - 401（再取得後も）→ BrokerAPIError、429 → RateLimitError、5xx → BrokerAPIError など HTTP ステータスごとの扱い。
    - kabu ステータスコードを内部状態（open/partial/filled/cancelled/rejected）へマッピング。
    - 将来的な非同期対応を容易にする設計（httpx.Client を内部に持つ）。

- その他ユーティリティ
  - 設定検証や起動処理向けに logging 設定やプロセス優先度設定へのフック（setup_logging / set_process_priority）を使用する設計を採用。
  - 監視 DB 初期化関数 init_monitoring_db の呼び出しを各起動処理に追加してテーブル存在を保証。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 実運用上の注意
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup で生成される .env のヘッダにも注意喚起を記載）。
- KABUSYS_ENV=live の場合は本番データベース・実際の注文が行われます。validate_config や config_setup で設定を慎重に確認してください。
- kill.flag（KILL_FLAG_PATH）や KILL_FLAG_CLEAR_ON_START の扱いは本番稼働で重要です。設定に留意してください。
- monitoring は環境にかかわらず本番 sqlite_path を使用するため、連続監視を行う際の DB 参照先に注意してください。

今後の予定（抜粋）
- async 対応の検討（httpx.AsyncClient への移行）と WebSocket 実装の改善。
- Reconciler（注文整合処理）や監視機能の拡充（メトリクス保存・アラート強化）。
- さらなる単体テストと統合テストの追加。

----------</>
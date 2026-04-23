KEEP A CHANGELOG
すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

変更履歴
========

Unreleased
----------

- ドキュメント・リリースノート未確定の変更点はここに記載します。

[0.1.0] - 2026-04-23
-------------------

Added
- 基本パッケージ情報
  - パッケージ初期バージョンを __version__ = "0.1.0" として導入。

- 設定管理
  - 環境変数/ .env を扱う Settings クラスを追加（src/kabusys/config.py）。
  - .env 自動ロード機能を導入（プロジェクトルート探索: .git または pyproject.toml を基準）。
  - 自動ロードの抑止: KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - .env 解析強化:
    - export KEY=val 形式をサポート。
    - クォート（シングル/ダブル）とバックスラッシュエスケープを正しく処理。
    - 行内コメントの扱い（クォートなしの場合は適切に削除）。
  - _require() による必須環境変数チェック（未設定時は ValueError を発生）。

- 設定ウィザード CLI
  - 対話式 .env 生成・更新ツールを追加（src/kabusys/config_setup.py）。
  - 各種設定キー（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を定義し、対話的に入力可能。
  - secret フィールドは表示時にマスク。
  - --env-file オプションで .env ファイルパスを指定可能。
  - 生成される .env にはコメントとセクションを付与し、誤ってコミットしない旨を明記。

- 設定検証 CLI
  - 起動前に .env と config/*.yaml の問題を検出する validate_config CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パス（DUCKDB_PATH / SQLITE_PATH）親ディレクトリの確認、config/*.yaml の存在確認および PyYAML があればパース検証を実行。
  - --strict オプションで警告も失敗扱い（exit code 1）にできる。
  - プレースホルダ値検出（例: 値が "your_value" や末尾が "_here"）で警告を出す。

- 監視プロセス
  - SystemMonitor をポーリングで実行する run_monitoring スクリプトを追加（src/kabusys/run_monitoring.py）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
  - Monitoring は KABUSYS_ENV にかかわらず常に本番用 sqlite_path を使用。
  - 起動時にプロセス優先度設定、監視用 SQLite/ DuckDB の初期化と接続、停止フラグ検知（data/stop_requested.flag）を実装。
  - 例外発生時でもループは継続し、適切にログ出力。

- 実行エンジン起動スクリプト
  - ExecutionEngine を起動する run_execution スクリプトを追加（src/kabusys/run_execution.py）。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
  - 停止フラグ、実行 PID の書き込み、スレッド監視と安全なシャットダウンを実装。

- ExecutionEngine（発注エンジン）
  - Signal Queue からの発注フローを実装（src/kabusys/execution/execution_engine.py）。
  - EngineConfig により発注開始/締切/市場終了時刻を設定可能（デフォルト: 8:50 / 9:10 / 15:30）。
  - シグナル処理時に複数の Gate（Gate1: シグナルレベル、Gate2: エグゼキューションレベル、Gate3: ドローダウン監視）を通し、NG の場合はスキップまたは kill_switch 実行。
  - size_multiplier の適用（BUY のみ、100株単位切り捨て）。
  - レート制限リトライ（Gate2）を最大 3 回まで実施し、サーキットブレーカ起動時はシグナルループを停止。
  - 発注成功時に position_entries を DuckDB に記録（BUY はエントリー、SELL はクローズ）。
  - WebSocket（broker が stream_push を提供する場合）の受信を別スレッドで処理し、push を drain して同期処理を行う。
  - 起動時に Reconciler によるリコンシリエーションを実行（存在する場合）。
  - kill.flag の存在検査と KILL_FLAG_CLEAR_ON_START の挙動（存在する場合にクリアして起動するオプション）を実装。
  - PID ファイルの生成と終了時の削除。

- 注文レコード / 状態機械
  - OrderRecord データモデルと状態遷移ロジックを追加（src/kabusys/execution/order_record.py）。
  - OrderState 列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
  - 許可遷移テーブルと transition_to() による遷移検証。InvalidStateTransitionError を導入。
  - updated_at は遷移時に自動更新。可選のフィールド（broker_order_id, filled_qty, avg_fill_price, error_message）をキーワードで更新可能。

- 注文管理（外向き API）
  - OrderManager を追加（src/kabusys/execution/order_manager.py）。
  - create_order: signal_id の重複防止（DB に部分ユニークインデックスあり）および DuplicateOrderError の導入。
  - send_order: クラッシュ耐性を考慮した二相的永続化フローを実装（OrderSent を先に永続化→ broker 呼び出し→ broker_order_id を先に永続化→その後 OrderAccepted 等へ遷移）。
    - OrderRejectedError を受けた場合は Rejected へ遷移。
    - OrderSentPendingError（注文番号は取得したが約定しないケース）は broker_order_id を保存して OrderSent のまま残す（呼び出し元へ再スロー）。
  - sync_order: broker の状態を照会して DB を更新。部分約定の進行はフィールド更新で反映。OrderSent→Filled/Partial の直接遷移が許可されないため OrderAccepted を経由して整合性を取る。
  - cancel_order: 終端状態ではキャンセル不可とし InvalidStateTransitionError を raise、そうでなければ broker API に cancel を送り Cancelled に遷移。

- ブローカークライアント（kabuステーション）
  - KabuStationClient を追加（src/kabusys/execution/kabu_client.py）。
  - httpx を用いた同期クライアント実装。内部でトークン取得（/token）を行い、401 時はトークン再取得してリトライ。
  - HTTP レスポンスの JSON パース失敗やネットワークタイムアウトを BrokerAPIError に変換。
  - 429 を RateLimitError として扱う。
  - kabu ステーションの注文状態コードを内部ステータス（open/partial/filled/cancelled/rejected）へマッピング。
  - 将来の WebSocket push 統合（websocket パッケージ使用）のための準備と stream_push の存在チェック。

- 監視 DB 初期化・ログ
  - monitoring 用 DB 初期化ユーティリティ（init_monitoring_db）を使用して起動時にテーブル整備を行う。
  - 発注時の監視ログ（log_trade_event）書き込みを ExecutionEngine から行う（監視 DB が渡された場合）。

Changed
- ログ出力・例外ハンドリング
  - 各種処理で詳細なログを追加（INFO/WARNING/ERROR/EXCEPTION）。
  - 各スレッドルーチンやループでの例外を捕捉してループ継続や安全終了を行う設計に。

Fixed
- N/A（初回リリース相当のため修正項目はなし）

Security
- .env の取り扱いに関する注意書きを .env 出力ヘッダに明記（.env を Git にコミットしないことを推奨）。

Notes / その他
- これらの実装はファイル内コメントや docstring に設計意図（クラッシュ耐性、リコンシリエーション戦略、paper_trading の DB 分離など）を詳細に残しています。運用前に validate_config と config_setup を用いて環境を整備してください。
- PyYAML が未インストールの場合、validate_config は YAML 内容検証をスキップして警告を出します（依存は必須ではありませんが config パース検証には推奨）。

将来の予定（参考）
- async 対応のための httpx.AsyncClient 化の余地を残す（kabu_client のコメントに記載）。
- 監視・実行フローの追加テストおよびリファクタリング、外部 API のモック用インターフェース強化。

----- End of CHANGELOG -----
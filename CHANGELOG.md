# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。  

※このファイルは、コードベースから実装内容を推測して作成した初期の変更履歴です。

## [Unreleased]

（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-04-23

初回リリース。本バージョンでは自動売買システム「KabuSys」のコア機能と運用ツール群を実装しています。

### 追加 (Added)
- 設定関連
  - Settings クラスを実装し、環境変数を型付きプロパティで取得する仕組みを提供。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動読み込み抑止フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 読み込みロジックを強化: export プレフィックス対応、シングル/ダブルクォート及びエスケープ処理、インラインコメント処理などを実装。
  - 環境変数読み込みの優先度: OS 環境変数 > .env.local > .env（.env.local は上書き、OS 環境は保護）。
- 設定 UI / CLI
  - 対話式ウィザード `kabusys.config_setup` を実装し、.env の初期生成・更新を支援。
  - `config_setup` はシークレット項目をマスクして表示、選択肢やデフォルト値をサポート。
  - `.env` を安全に書き出す `_write_env` を実装（生成時の注意コメントを含むテンプレートを出力）。
- 設定検証ツール
  - `kabusys.validate_config` CLI を実装し、起動前に環境変数・config/*.yaml 等の整合性を検査。
  - 必須/任意の環境変数チェック、KABUSYS_ENV の妥当性検査、LOG_LEVEL 検査、DB パス存在チェック（親ディレクトリ存在確認）を実施。
  - --strict オプションを追加（警告を FAIL 扱いにして exit(1) を返す）。
  - PyYAML 未インストール時の挙動（YAML パース検証のスキップ）を適切に警告出力。
- 実行スクリプト
  - `run_execution` スクリプトを実装（ExecutionEngine 起動用）。
    - paper_trading 環境時はペーパートレード用 SQLite（分離された DB）を使用。
    - プロセス優先度設定、PID ファイル出力、停止フラグ検出（stop_requested.flag）に対応。
  - `run_monitoring` スクリプトを実装（SystemMonitor のポーリングループ）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
- 発注/実行関連
  - ExecutionEngine を実装:
    - シグナル処理（8:50-9:10）と push ドレイン（9:10-15:30）を含むセッション管理。
    - WebSocket push を別スレッドで受信し、内部キューへ格納。
    - シグナルに対する Gate1（シグナルレベル検査）、Gate2（実行レベル検査・レート制限）、Gate3（ドローダウン監視）を実装。Gate2 のレート制限はリトライ（最大3回）を行い、サーキットブレーカー検出で適切に停止。
    - kill.flag に応じた起動拒否・自動クリア（KILL_FLAG_CLEAR_ON_START）に対応。
    - position_entries への約定予定書き込み（BUY は entry、SELL は sell_date 更新）を実装。
    - 監視 DB（MonitoringDB）への発注イベントログ出力フックを追加。
  - OrderRecord（状態遷移モデル）を実装:
    - 明示的な状態定義（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許容される遷移集合を定義し、不正遷移時は InvalidStateTransitionError を発生。
    - 状態遷移時に更新フィールド（broker_order_id, filled_qty, avg_fill_price, error_message）と updated_at の自動更新を実装。
  - OrderManager を実装:
    - create_order: signal_id に対する重複 active 注文の検出（DuplicateOrderError）。
    - send_order: 2 相永続化設計（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を保存 → OrderAccepted へ遷移）により、クラッシュ耐性を確保。
    - OrderSentPendingError の扱い（broker_order_id を永続化した上で OrderSent のまま残す）をサポート。
    - sync_order: broker 側のステータスを取得して状態を同期。部分約定の進展に応じたフィールド更新や OrderSent→Filled/PartialFill を OrderAccepted 経由で補正するロジックを実装。
    - cancel_order: キャンセル不可能な状態の判定（Closed/Cancelled/Rejected/Filled）と、broker 側キャンセル呼び出し→Cancelled への遷移を実装。
  - ブローカークライアント関連
    - KabuStationClient を実装（httpx 同期クライアントを使用）。
      - トークン取得の遅延初期化、401 応答時の自動トークン再取得と 1 回の再試行処理。
      - レスポンス JSON パース失敗は BrokerAPIError に変換。
      - 429 を RateLimitError として扱う。
      - ネットワークエラー / タイムアウトを適切に変換して伝播。
    - KabuStationClient は将来的な async 対応を見据えた実装になっている（httpx.AsyncClient へ変更可能）。
- 監視・DB 初期化
  - monitoring_db の初期化処理（init_monitoring_db）呼び出しフローを実装（冪等な初期化）。
  - DuckDB と SQLite の接続とクローズ処理を適切に管理。
- その他ユーティリティ
  - 簡易プロセス優先度設定、ロギングセットアップの呼び出しポイントを追加（setup_logging, set_process_priority を利用）。
  - パッケージメタ情報: __version__ = "0.1.0"。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- 実行フロー設計上のクラッシュ復旧を考慮し、発注の永続化順序やリコンシリエーションを設計（Issue #32 を参照するコメントあり）。
- .env 解析の堅牢性向上（クォート内エスケープやインラインコメントの扱いを改善）。

### 廃止 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数のシークレット項目は対話ウィザードでマスク表示。
- .env を絶対に Git にコミットしない旨を明示するテンプレートコメントを出力。

---

既知の注意点 / 運用上のヒント
- validate_config にて KABUSYS_ENV=live 設定時は複数の注意喚起（LINE 通知設定や KILL_FLAG_CLEAR_ON_START 等）を行います。本番環境での設定確認に利用してください。
- run_execution/run_monitoring は PID ファイル・停止フラグ（data/stop_requested.flag / data/execution.pid 等）を利用します。運用時のファイルパス権限・ディレクトリ作成に注意してください。
- PAPER_FILL_MODE 等一部設定のバリデーションは Settings プロパティ内で行われ、無効値は ValueError を送出します。起動前に validate_config を実行することを推奨します。

もし CHANGELOG に追加したい差分やリリース日付の修正、あるいは過去バージョンを遡って記載したい場合は、コードやリリース履歴（コミットメッセージ）を共有してください。
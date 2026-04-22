# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]
（次回リリースに向けた変更はここに記載してください）

## [0.1.0] - 2026-04-22
初回リリース。KabuSys の基本的な実行・設定・監視・発注基盤を実装しました。

### 追加 (Added)
- パッケージバージョンを追加
  - kabusys.__version__ = "0.1.0"

- 環境変数／設定管理
  - Settings クラスを実装し、環境変数から各種設定値を提供（J-Quants トークン・kabu API パスワード・DB パス等）。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の読み込みロジックは .env と .env.local の優先度、既存の OS 環境変数を保護する挙動に対応。
  - .env 行パーサーを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、コメント処理に対応）。

- 設定ウィザード CLI
  - python -m kabusys.config_setup による対話式ウィザードを実装。
  - 初期 .env ファイルの生成・更新を支援（項目定義、シークレットマスク、選択肢、デフォルト値、保存確認など）。
  - .env 書き込みフォーマットを定義（Git へのコミット禁止の注意書き等）。

- 設定検証 CLI
  - python -m kabusys.validate_config による起動前設定検証ツールを実装。
  - 必須／任意環境変数の存在チェック、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
  - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在確認（存在しない場合は警告）。
  - config/*.yaml の存在チェックおよび PyYAML がインストールされている場合は YAML パース検証。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険値検出）。
  - --strict オプションで警告を FAIL（exit code 1）として扱うモード。

- 実行スクリプト
  - Execution エンジン起動スクリプト（python -m kabusys.run_execution）を追加。
    - paper_trading 環境では専用の paper_sqlite_path を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ（data/stop_requested.flag）への対応。
    - メインループは別スレッドで ExecutionEngine.run_session を起動し、停止フラグで安全に終了。
  - Monitoring ポーリングスクリプト（python -m kabusys.run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する設計。
    - 監視中の例外はログ出力して次ポーリングへ継続。

- ExecutionEngine（発注エンジン）
  - Signal Queue ベースの発注フローを実装（シグナル処理時間帯・push ドレインループ・セッション管理）。
  - kill.flag 検査、KILL_FLAG_CLEAR_ON_START による起動時自動クリアのサポート。
  - PID ファイル作成・削除、WebSocket (push) スレッドの統合、push ペイロードの処理キューを実装。
  - 発注フロー:
    - シグナル読み取り（DuckDB）、size_multiplier 適用、数量の切り捨て（100株単位）処理。
    - Gate 1（シグナルレベル）／Gate 2（実行レベル、レート制限）を経て実際の発注実行。
    - 発注結果に基づき position_entries を DuckDB に書き込み（買いは entry、売りは sell_date 更新）。
    - 発注時の遅延計測を監視 DB にログ（監視 DB が提供される場合）。
    - WebSocket push を受けて sync_order を呼び、Gate 3（ドローダウン監視）評価を実施。

- Order 層（OrderRecord / OrderManager / OrderRepository 連携）
  - OrderRecord: 純粋な状態マシンモデルを実装（OrderState 列挙、許可遷移テーブル、transition_to メソッド）。
  - InvalidStateTransitionError を導入し、不正遷移を検出。
  - OrderManager:
    - create_order(): signal_id 単位での重複検出、UUID による client_order_id 発番、DB の部分ユニーク制約からの DuplicateOrderError 変換。
    - send_order(): クラッシュ安全を考慮した 2 相永続化フローを実装（OrderSent 状態の永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移等）。
      - OrderRejected / OrderSentPending の明示的ハンドリング（OrderSentPendingError は呼び出し元へ再送出）。
    - sync_order(): broker 側の状態取得とローカル状態の同期（部分約定の更新や OrderSent→Filled の経路補正等）。
    - cancel_order(): 終端状態ではキャンセル不可とする検査、broker cancel 呼び出し、Cancelled への遷移。
  - 発注フローは Reconciliation を前提にクラッシュ後の状態回復を考慮。

- Broker クライアント（KabuStationClient）
  - kabu station REST API の同期クライアントを実装（httpx を使用）。
  - トークン取得処理（遅延初期化、タイムアウト・ネットワーク例外の変換）、401 発生時のトークン再取得とリトライをサポート。
  - レスポンス JSON パース時のエラーハンドリング、429（rate limit）検出（RateLimitError の返却）。
  - websocket ストリーム（push）を受けるための stream_push インターフェイス統合（ExecutionEngine 側で利用）。

- 監視周り
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を呼び出すフローを追加し、監視テーブルの存在を保証（冪等）。

- プロセス制御 / ロギング / 優先度
  - set_process_priority を用いたプロセス優先度の設定（high 推奨）を起動直後に実行。
  - setup_logging を用いたコンポーネント毎のログ初期化。

### 変更 (Changed)
- （初回リリースのため履歴なし）

### 修正 (Fixed)
- （初回リリースのため履歴なし）

### 削除 (Removed)
- （初回リリースのため履歴なし）

### 既知の制約・注意点 (Known issues / Notes)
- config/*.yaml の内容検証は PyYAML がインストールされていない場合スキップされ、警告が出ます。
- ExecutionEngine の時間判定はローカル時計を使用しており、タイムゾーンやシステムクロックに依存します。
- PAPER_FILL_MODE の不正値は Settings.paper_fill_mode で ValueError を送出します。起動前に validate_config で検査することを推奨します。
- kill.flag の扱いは慎重に：本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します（validate_config が警告を出します）。

---

このリリースはシステムの初期コア機能（設定管理、検証、発注エンジン、監視、broker クライアント、状態管理）を提供します。今後のリリースでは監視拡張、詳細なメトリクス、エラーハンドリング強化、単体テスト・結合テストの追加などを予定しています。
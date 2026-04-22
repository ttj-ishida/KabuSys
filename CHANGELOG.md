# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

最新のリリース: 0.1.0

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-22
初回公開リリース。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- 全体
  - パッケージバージョンを追加: kabusys.__version__ = "0.1.0"。
  - コマンドラインで利用可能なユーティリティスクリプトを追加:
    - python -m kabusys.validate_config（設定検証）
    - python -m kabusys.config_setup（環境設定ウィザード）
    - python -m kabusys.run_execution（ExecutionEngine 起動）
    - python -m kabusys.run_monitoring（SystemMonitor ポーリング）

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から特定）。
  - .env / .env.local の読み込み順序と上書きルール（OS 環境変数を保護する protected set）。
  - .env 行パーサーを実装（export プレフィックス、シングル/ダブルクォート内エスケープ、インラインコメント処理に対応）。
  - 必須変数取得ヘルパー _require を提供（未設定時に ValueError を送出）。
  - Settings クラスを追加し、環境変数から各種設定値を取得するプロパティを定義:
    - J-Quants / kabuAPI / LINE / DB パス / paper trading 設定 / 監視しきい値 / PID / kill flag 等
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の値検証（不正値で例外を送出）。

- 環境設定ウィザード（src/kabusys/config_setup.py）
  - 対話式ウィザードで .env を作成・更新する run_wizard を実装。
  - 入力項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。
  - シークレット項目のマスク表示、選択肢サポート、既存 .env の読み込み・再利用。
  - .env のテンプレート書き出し機能（_write_env）。

- 設定検証 CLI（src/kabusys/validate_config.py）
  - .env と config/*.yaml の起動前検証を行う validate() と main() を提供。
  - 必須環境変数チェック、プレースホルダ値警告、KABUSYS_ENV / LOG_LEVEL の許容値検査。
  - DB パス存在チェック（親ディレクトリの存在確認と警告）。
  - config/*.yaml の存在確認と PyYAML によるパース検証（PyYAML 未インストール時は警告）。
  - KABUSYS_ENV=live 時の追加チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険値警告）。
  - --strict フラグで警告を FAIL（exit(1)）扱いにする機能。

- 実行エンジン・監視系
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - Signal Queue を元にした発注エンジンを実装（セッション管理、8:50–9:10 のシグナル処理、9:10–15:30 の push ドレイン）。
    - Gate 1/2/3 によるリスクチェックの組み込み（RiskManager と連携）。
    - kill_switch による全 active 注文のキャンセル、kill.flag の扱い、KILL_FLAG_CLEAR_ON_START による自動クリア動作。
    - PID ファイル書き込み、WebSocket push の別スレッド処理、_push_queue を使った同期処理。
    - position_entries への約定記録（buy / sell の扱い分岐、バックテストと整合する fill_date の算出）。
    - 発注レイテンシ / 監視DB ログ記録（監視 DB オブジェクトが渡される場合）。
  - run_execution.py（src/kabusys/run_execution.py）
    - プロセス優先度セット（High）、設定読み込み、DB 接続（paper_trading 環境は専用 SQLite を使用）し、ExecutionEngine を起動。
    - stop_requested.flag 検知により安全に停止。
  - run_monitoring.py（src/kabusys/run_monitoring.py）
    - SystemMonitor ポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - stop_requested.flag 検知、例外処理、DB（SQLite / DuckDB）初期化。

- 注文管理 / ブローカー関連（src/kabusys/execution/*）
  - OrderRecord（src/kabusys/execution/order_record.py）
    - OrderState 列挙と状態遷移ロジック (transition_to) を実装。許可されない遷移で InvalidStateTransitionError を送出。
    - created_at / updated_at の自動更新、オプションフィールド（broker_order_id, filled_qty, avg_fill_price, error_message）更新。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - create_order / send_order / sync_order / cancel_order の外向き API を提供。
    - create_order は signal_id の重複チェック（DB と部分ユニーク制約いずれも DuplicateOrderError に変換）。
    - send_order はクラッシュ安全性を考えた2相永続化のワークフローを実装（OrderSent を先に保存し、broker_order_id を保存→OrderAccepted に遷移）。
    - OrderRejectedError / OrderSentPendingError のハンドリング。OrderSentPendingError は broker_order_id を保存したまま例外を再送出。
    - sync_order は broker の状態照合とフィールド更新（部分約定の進行時は状態を保持しつつ filled_qty/avg_fill_price を更新）。
    - cancel_order はキャンセル不可能な状態の検査と broker API 呼出しの後に Cancelled に遷移。
  - Broker クライアント（src/kabusys/execution/kabu_client.py 他）
    - KabuStationClient を実装（httpx 同期クライアント、トークン取得・自動再取得、401 リトライ）。
    - レスポンス JSON パース失敗 / ネットワークエラー / タイムアウト / 429 レート制限 / 5xx を BrokerAPIError / RateLimitError に変換。
    - WebSocket push ハンドリング（stream_push）との連携を想定。

- 監視 DB 初期化ユーティリティ（src/kabusys/monitoring/monitoring_db.py を参照する呼出しを追加）
  - run_monitoring, run_execution で init_monitoring_db を呼び出し、監視テーブルを確保する設計（冪等）。

- ロギング & プロセス優先度
  - setup_logging と set_process_priority ユーティリティを利用して、起動時にログ設定とプロセス優先度（High）を設定。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （初回リリースのため該当なし）

### 注意事項 / 備考
- config/*.yaml のパース検証は PyYAML に依存します。PyYAML がインストールされていない場合は検証がスキップされ、警告が表示されます。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup のテンプレートにも注記あり）。
- ExecutionEngine の kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番での使用は危険で、validate_config では警告を出します。
- 設計上、OrderSent 状態でクラッシュした場合は Reconciliation（reconciler）が復旧を試みるため、send_order は OrderSent を先にコミットする実装になっています（2相永続化の設計）。

---

（この CHANGELOG はコードベースの内容から推測して記載しています。細かな実装意図や将来の変更により実際の変更履歴は差異が生じる可能性があります。）
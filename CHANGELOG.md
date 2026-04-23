# Changelog

すべての変更は Keep a Changelog の形式に従います。  
非互換性のある変更は明確に記載します。

## [0.1.0] - 2026-04-23

### 追加
- 初期リリース: KabuSys の基本機能を実装。
- 環境・設定管理
  - Settings クラスを追加し、環境変数から各種設定を取得可能に（J-Quants トークン、kabu API パスワード、DB パス等）。
  - .env 自動読み込み機能を追加（読み込み優先度: OS 環境変数 > .env.local > .env）。OS 環境変数を保護する仕組みを備え、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーを実装（export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
- 対話型設定ウィザード
  - python -m kabusys.config_setup で起動する .env 作成／更新ウィザードを実装。テンプレート（項目定義、デフォルト、選択肢、シークレット扱い等）を備える。
  - .env を書き出す _write_env を実装（コメント付きテンプレート）。
- 設定検証 CLI
  - python -m kabusys.validate_config 実行で必須環境変数・設定ファイル・パス等を起動前に検証。
  - --strict オプションで警告を FAIL（exit 1）扱いにできる。
  - PyYAML の有無に応じて config/*.yaml のパース検証を行う（未インストール時は警告でスキップ）。
  - 本番用追加チェック（KABUSYS_ENV=live 時の LINE 設定、KILL_FLAG_CLEAR_ON_START の危険検出等）。
- 実行スクリプト
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
    - シグナル処理（指定時間帯）と WebSocket push ドレインループのセッション実行。
    - PID ファイル管理、kill.flag による停止制御、KILL_FLAG_CLEAR_ON_START による起動時自動クリア処理。
    - paper_trading モードでは専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
  - Monitoring 起動スクリプト: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用。
- 注文管理・実行周り
  - OrderRecord（状態遷移ロジック）を実装。OrderState 列挙と許可遷移を定義し、不正遷移時に InvalidStateTransitionError を発生。
  - OrderManager を実装（create / send / sync / cancel）。DB と OrderRecord を組み合わせて状態管理を行う。
    - create_order: signal_id の重複チェック（部分ユニーク制約とアプリレベルチェック）、UUID ベースの client_order_id を採番。
    - send_order: クラッシュ安全性を考慮した2相的な永続化フローを実装（OrderSent への遷移を先にコミット、broker_order_id を先に保存、その後 OrderAccepted に遷移等）。
    - OrderSentPendingError の取り扱い（broker_order_id を永続化して OrderSent のまま残す — Reconciliation の対象）。
    - sync_order: broker 側からの状態取得に基づく同期ロジック（部分約定の進行はフィールド直接更新、OrderSent→Filled 等の特殊ケースは OrderAccepted を経由して遷移）。
    - cancel_order: 終端状態ではキャンセル不可として InvalidStateTransitionError を発生、そうでなければ broker API を呼び Cancelled に遷移。
  - DuplicateOrderError を定義して同一 signal_id の active 注文重複を検出。
- ExecutionEngine（発注エンジン）
  - シグナル読み込み（DuckDB）、Gate チェック（Gate1: シグナルレベル、Gate2: エグゼキューションレート制限＋サーキットブレーカー、Gate3: ポートフォリオドローダウン監視）。
  - size_multiplier 適用（BUY のみ、100 株単位切捨）、発注タイプ自動判定（price==0 -> market）。
  - リトライ（Gate2 は最大 3 回、サーキットブレーカー発生時はシグナルループを停止）。
  - WebSocket push の受信を別スレッドで行い、受信 payload を _push_queue に投入して同期処理。
  - 発注後に position_entries を更新（BUY はエントリ登録、SELL はクローズ日を設定。ただし pending の SELL は未記録）。
  - 発注レイテンシを監視 DB にログ可能（MonitoringDB を注入）。
  - kill_switch により全 active 注文をキャンセルする仕組みを公開（stop のエイリアス）。
- ブローカークライアント（kabu）
  - KabuStationClient を実装（httpx を同期利用）。
  - トークン管理（遅延初期化、401 時に再取得して1回リトライ）、レスポンス JSON パースのエラーハンドリング、HTTP 状態コードに応じた例外（401, 429, 5xx など）。
  - WebSocket push 用 stream_push（存在する場合に ExecutionEngine から利用）を想定。
- モニタリング周り
  - monitoring_db の初期化関数呼び出しを組み込み（init_monitoring_db を各スクリプトで呼ぶ）。
  - 監視ループ（SystemMonitor）用の run_monitoring スクリプトを用意。
- ユーティリティ
  - process_priority 設定ユーティリティを利用して、起動時にプロセス優先度を High に設定（run_execution / run_monitoring）。
  - ロギングセットアップユーティリティ（setup_logging）を使用する構成。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の注意点
- config/*.yaml のパース検証は PyYAML がインストールされている場合のみ行われる。未インストール時は警告を出して検証をスキップする。
- KabuStationClient は同期 httpx.Client を使用しており、将来的に非同期対応する場合は httpx.AsyncClient へ置換することを想定している。
- 一部ファイルの HTTP エラー処理等は拡張ポイントとして残している（ログ・例外の詳細は導入環境に応じて調整推奨）。

---

注: 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして利用する場合は、追加の説明や既知の問題、マイグレーション手順などをプロジェクトの実態に合わせて追記してください。
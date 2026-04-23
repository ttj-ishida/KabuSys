# Changelog

すべての注目に値する変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

履歴は概ねコードベースから推測して作成しています。実装の詳細は各モジュールのソースを参照してください。

## [Unreleased]
- 今後のリリース向けの変更・検討事項をここに記載します。

## [0.1.0] - 2026-04-23
初回リリース（推定）。主要な機能と実装を追加しました。

### 追加（Added）
- CLI / ユーティリティ
  - `kabusys.config_setup`：対話式ウィザードで .env を初期作成 / 更新するコマンドラインツールを追加。
    - 各種設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン等）を対話形式で編集可能。
    - .env の読み書きロジック（既存値読み込み、秘密値マスク表示、保存の確認）を実装。
  - `kabusys.validate_config`：起動前に .env と config/*.yaml の設定不備を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の値チェック、DB パスや親ディレクトリの存在確認、本番環境（live）向けの追加ガードなど。
    - `--strict` フラグで警告を FAIL として扱うモードをサポート。
- 設定 / 環境変数管理
  - `kabusys.config.Settings`：環境変数からアプリケーション設定を取得する Settings クラスを追加。
    - 自動 .env ロード（プロジェクトルートの検出 .git / pyproject.toml に基づく）と上書きルール（OS環境変数保護、.env → .env.local）を実装。
    - 必須値取得用 `_require()`、PAPER_FILL_MODE の厳密なバリデーション、パス類を Path に変換するプロパティを提供。
  - .env パーサーは引用符付き値、バックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
- 実行スクリプト
  - `run_execution.py`：ExecutionEngine を起動するスクリプトを追加。
    - paper_trading 環境では専用の SQLite（paper_trading.db）を使用して本番 DB と分離。
    - プロセス優先度設定・PID ファイル書き込み・停止フラグ検知を実装。
  - `run_monitoring.py`：SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境にかかわらず本番の sqlite_path を使用して監視データを収集。
    - ポーリング間隔を `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
- Execution / 注文処理基盤
  - `ExecutionEngine`：Signal Queue Pull 型の発注エンジンを実装。
    - 日中のシグナル処理（8:50-9:10）および push ドレインループ（9:10-15:30）を実行。
    - WebSocket (kabu push) を受け取るワーカースレッドを持ち、受信 payload をキュー処理して注文同期や Gate 3 評価を行う。
    - kill_switch により全 active 注文をキャンセルしループを停止する機能を実装。
  - `OrderRecord`（状態遷移ロジック）：
    - 注文状態（created, sent, accepted, partial, filled, closed, cancelled, rejected）の列挙と許可遷移を定義。
    - 不正遷移時に `InvalidStateTransitionError` を送出し、状態遷移時にタイムスタンプやオプションフィールドを更新。
  - `OrderManager`：
    - signal_id 単位の重複防止（DuplicateOrderError）を実装。
    - send_order の二相的パーシステント処理（OrderSent を永続化 → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移）でクラッシュ時の回復性を向上。
    - OrderRejected / OrderSentPending（OrderSentPendingError）などのケースを適切に扱う。
    - sync_order により broker 側の状態を取りに行き、部分約定や full fill の反映を行うロジックを実装。
    - cancel_order はキャンセル不可状態をチェックし、broker API 呼び出し後に Cancelled に遷移。
  - `ExecutionEngine` 側では以下を実装：
    - Gate 1: シグナルレベル検査（RiskManager を用いた signal チェック）
    - Gate 2: エグゼキューションレベル（実行前のレート制限等、リトライロジック、サーキットブレーカー検出）
    - Gate 3: ドローダウン監視（ポートフォリオ評価で閾値超過なら kill_switch）
    - 発注レイテンシや監視情報を monitoring DB に記録するフック
    - position_entries（DuckDB）への約定予定日の記録（次営業日に基づく）
- ブローカ / API クライアント
  - `KabuStationClient`：kabu ステーションの REST API クライアントを追加。
    - httpx を用いた同期クライアント、トークン取得（遅延初期化・再取得）と 401 リトライ、429（レート制限）や 5xx エラーの扱いを実装。
    - WebSocket push の stream_push を利用する設計（存在しない場合はスキップ）。
- データベース / 監視
  - DuckDB（分析用）と SQLite（監視 / 注文履歴）を併用する設計を採用。
  - Monitoring DB 初期化関数 `init_monitoring_db` の利用によりテーブル存在保証（冪等）を行う。
  - 監視ループ / Execution で DB の接続とクローズを適切に行う。
- 運用周り
  - PID ファイル管理（書き込み・削除）、stop_requested.flag / kill.flag による外部停止フラグ検知を実装。
  - `KILL_FLAG_CLEAR_ON_START` による起動時 kill.flag 自動クリアオプション。
  - `set_process_priority` / `setup_logging` と連携してプロセス優先度・ログ出力を整備。

### 変更（Changed）
- 初版のため特になし（初期実装）。

### 修正（Fixed）
- 初版のため特になし。

### 削除（Removed）
- 初版のため特になし。

### セキュリティ（Security）
- .env ファイルは絶対に Git にコミットしない旨を生成済み .env ヘッダに明記。
- API トークンやパスワードなどの秘密情報はウィザードでマスク表示・秘密指定可能。

### マイグレーション / 注意事項（Migration / Notes）
- .env の自動ロードはデフォルトで有効。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 本番環境（KABUSYS_ENV=live）では validate_config の警告や本番ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認）に注意してください。
- PAPER_TRADING を使う場合、実行は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を用いて本番 DB と分離されます。
- `PAPER_FILL_MODE` や `LOG_LEVEL` などの環境変数は許容値が限定されています。不正な値は起動時に例外を発生させます。
- config/*.yaml の検証は PyYAML がインストールされている場合にのみ行われます。未インストール時は警告を出してスキップします。

---

必要があれば、個別ファイルや機能ごとにより詳しい変更点（実装の抜粋や設計意図）を付記できます。どのレベルの詳細を追加希望か教えてください。
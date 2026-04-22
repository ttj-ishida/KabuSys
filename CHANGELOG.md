CHANGELOG
=========

すべての notable な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-22
--------------------

Added
- 初期リリース: 日本株自動売買システム "KabuSys" のコア機能を追加。
- 環境設定・起動補助
  - 対話式ウィザードで .env を作成・更新する CLI を追加（python -m kabusys.config_setup）。
    - 設定項目の定義とシークレットマスキング、選択肢・デフォルト提示、保存確認機能を実装。
    - .env ファイル書き込みはプロジェクトルートの .env をデフォルトとする（--env-file で変更可）。
  - .env の自動読み込み実装（プロジェクトルートの .env と .env.local を読み込み、.env.local は上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等を考慮して robust に実装。
  - OS 環境変数を保護するための上書き制御（protected key セット）。
- 設定管理
  - Settings クラスを追加（kabusys.config）。環境変数経由で各種設定を取得するプロパティを提供。
  - 必須項目取得時に未設定なら ValueError を投げる _require() を実装。
  - 環境・ログレベル・paper trading 関連の妥当性チェック（有効値の検証）を実装。
  - paper_trading 用の別 SQLite パス（PAPER_TRADING_SQLITE_PATH / paper_sqlite_path）と PAPER_FILL_MODE の検証を追加。
  - 各種閾値（CPU/MEM/DISK/MEMORY）や kill flag 関連設定プロパティを提供。
- 設定検証 CLI
  - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パーシング（PyYAML があれば）などを実行。
    - --strict フラグで警告も失敗扱いにするオプションを実装。
- 実行・監視プロセス用ランチャー
  - 実行エンジン起動スクリプトを追加（python -m kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - PID ファイル管理、停止フラグ検知、プロセス優先度設定、DB 初期化処理を実装。
  - 監視用ポーリングループ起動スクリプトを追加（python -m kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き、監視は常に本番 sqlite_path を使用する挙動を明示。
- 発注ロジック
  - OrderRecord（状態遷移を厳格に検証するビジネスロジックモデル）を追加。
    - 明示的な状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と許容遷移定義を実装。
    - 不正遷移時は InvalidStateTransitionError を送出。
  - OrderManager を追加（create/send/sync/cancel の外向き API）。
    - 同一 signal_id の重複防止（DuplicateOrderError）。
    - send_order はクラッシュ安全性を考慮した 2 相永続化戦略を採用（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）。
    - OrderRejectedError / OrderSentPendingError の扱いを明確化。pending は broker_order_id を保持して再照合対象とする。
    - sync_order による broker 状態同期（部分約定の更新ロジック含む）。
    - cancel_order は状態チェックを行い、キャンセル不可状態では例外を発生させる。
- ExecutionEngine（Signal Queue 型発注エンジン）
  - シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）のセッションロジックを実装。
  - Gate ベースのリスク管理フローを実装:
    - Gate1: シグナル単位の検査（check_signal）
    - Gate2: 実行単位の検査（レートリミット・サーキットブレーカー） — リトライ/CB 発動時の挙動制御
    - Gate3: ドローダウン監視（push 受信時に portfolio valuation を評価し、NG なら kill_switch 発動）
  - kill_switch による全ループ停止と全 active 注文のキャンセル処理を実装（外部停止 API として stop() を提供）。
  - WebSocket push ハンドラを別スレッドで実行し、受信 payload を queue 経由で処理。
  - 発注成功時の position_entries 登録（DuckDB を用いたエントリ管理）や監視 DB へのイベント記録を実装（監視 DB 書き込み失敗でも発注フロー継続）。
- Broker / kabu station クライアント
  - KabuStationClient を追加（httpx の同期クライアント、トークン管理、401 リトライ、429 → RateLimitError マッピング、JSON パースエラー変換等）。
  - stream_push インターフェースを想定し WebSocket push 受信に対応（実装されない broker ではスキップ）。
- 監視関連
  - 監視 DB の初期化ユーティリティと SystemMonitor 起動ロジックを追加。
  - run_monitoring は stop フラグ検出と例外ハンドリングを行い安全に終了する。
- その他ユーティリティ
  - robust な .env パース・ロード、ログ設定セットアップ、プロセス優先度設定ユーティリティを追加。

Changed
- なし（初回リリースのため履歴は追加のみ）。

Fixed
- なし（初回リリースのため履歴は追加のみ）。

Notes / Implementation details
- 一部実装はクラッシュ安全性（永続化の順序付け、Reconciliation を想定した broker_order_id の保存等）を優先して設計されています（Issue #32 に関連する設計言及あり）。
- YAML の検証は PyYAML がインストールされている場合のみ実行され、未インストール時は警告を出してスキップします。
- .env ファイルはセキュリティの観点から Git にコミットしない旨のコメントを挿入して書き出します。
- ローカル開発（development）、ペーパートレード（paper_trading）、本番（live）を明確に区別する設計になっており、live モードでは追加の安全確認（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起等）を行います。

ライセンス、貢献、バグ報告
- バグ報告や機能要望はリポジトリの Issue にてお願いします。
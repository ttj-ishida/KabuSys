# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現行バージョン: 0.1.0

## [Unreleased]

（特になし）

## [0.1.0] - 2026-04-22

初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- CLI / ユーティリティ
  - `kabusys.config_setup`:
    - .env ファイルを対話式に作成・更新するウィザードを実装。
    - 必須/任意項目、選択肢、シークレットマスク表示などをサポート。
    - 出力テンプレートにより .env を安全に生成（.env を Git 管理しない旨のヘッダを挿入）。
  - `kabusys.validate_config`:
    - 起動前に .env と config/*.yaml（存在確認・パース）を検証する CLI。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 必須環境変数の未設定チェック、プレースホルダ判定、環境値 / ログレベルの妥当性チェック、DB パスの親ディレクトリ存在チェック、本番環境向け警告（LINE 通知や Kill Flag 設定）などを実施。
- 環境/設定管理
  - `kabusys.config`:
    - プロジェクトルート自動探索（.git / pyproject.toml を基準）に基づく .env 自動読み込み機能を実装（OS 環境変数を保護、`.env.local` は上書き）。
    - .env のパースは export 形式、クォート文字列、エスケープ、コメント処理（ルールに基づく）に対応。
    - `Settings` クラスでアプリ設定を集中管理（型変換、既定値、不正値時の ValueError を含む）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能（テスト向け）。
- 実行 / 監視ランナー
  - `run_execution.py`:
    - ExecutionEngine を起動するエントリポイントを追加。
    - Paper Trading 時は専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検出による安全な停止を実装。
    - PID ファイル管理、プロセス優先度設定、ログ初期化を組み込む。
  - `run_monitoring.py`:
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
- 発注ロジック・実行基盤
  - `execution/order_record.py`:
    - 注文状態（OrderState）列挙と状態遷移検証を持つ純粋なドメインモデル `OrderRecord` を実装。許可されない遷移では `InvalidStateTransitionError` を投げる。
    - 状態遷移時にタイムスタンプを UTC で更新。必要な追加メタ情報（broker_order_id、filled_qty、avg_fill_price、error_message）をキーワード引数で安全に更新可能。
  - `execution/order_manager.py`:
    - `OrderManager` による外向き API を実装（create/send/sync/cancel）。
    - create_order は signal_id の重複チェック（DB とメモリ）を行い、重複時は `DuplicateOrderError` を投げる。
    - send_order は「OrderCreated → OrderSent を先に永続化」する 2 相的な耐クラッシュ設計を採用（broker 呼び出し前に状態を永続化し、broker_order_id を先にコミットすることでリコンシリエーションに耐える）。
    - broker 呼び出しで拒否された場合や pending（注文番号は発行されたが約定しない）ケースを適切に扱い、各種例外（OrderRejectedError, OrderSentPendingError）に対応。
    - sync_order は broker 側ステータスを内的 OrderState にマッピングし、部分約定の進行は差分更新で対応。OrderSent→Filled/Partial の直接遷移不可能性を考慮して OrderAccepted を経由する補正ロジックを実装。
    - cancel_order は終端状態の注文はキャンセル不可として `InvalidStateTransitionError` を投げ、broker_order_id があれば API に対して cancel を実行する。
  - `execution/execution_engine.py`:
    - Signal Queue Pull 型の発注エンジンを実装（セッションタイムウィンドウ: 発注 8:50-9:10、push ドレイン 9:10-15:30）。
    - Gate 1（シグナル単位）/ Gate 2（エグゼキューション単位、レート制限、サーキットブレーカー）/ Gate 3（ポートフォリオドローダウン監視）という多段リスク検査を実装。Gate 2 はリトライ（最大 3 回）を行い、Circuit Breaker の場合はシグナルループ自体を停止。
    - size_multiplier の適用（BUY のみ、100 株刻み切り捨て）や、発注成功・保留の監視イベント記録、position_entries の DuckDB への書き込み（発注の副作用で最低保有日数管理）を実装。書き込み失敗時は警告を出してフローは継続する。
    - WebSocket push の受信と _push_queue への格納、push に対する sync_order と Gate 3 評価を行う push ドレイン処理を実装。broker に stream_push を持たない場合はスキップしてログ出力。
    - kill.flag の検査と KILL_FLAG_CLEAR_ON_START の挙動（1 で自動クリア）を組み込み。kill_switch により全 active 注文をキャンセルしてループを停止する。
    - PID ファイル管理（起動時作成、終了時削除）を実装。
- ブローカー（kabuステーション）クライアント
  - `execution/kabu_client.py`:
    - kabu station REST API クライアント（同期 httpx 実装）を追加。内部でトークン取得（/token）を管理し、401 時はトークン再取得して再試行するロジックを実装。
    - レスポンス JSON パース失敗やタイムアウト、ネットワークエラーを BrokerAPIError にラップして扱う。429 は RateLimitError を返す。
    - WebSocket push は websocket を使い、push payload の処理により ExecutionEngine と連携可能。
- 監視/DB 初期化
  - 監視系の DB 初期化関数（init_monitoring_db）を利用して起動時に必要テーブルを作成できるように統合。
- 共通ユーティリティ
  - プロセス優先度設定（high）やログセットアップを起動ルーチンに組み込み（`utils.process_priority`, `utils.logging_setup` を利用）。

### Changed
- （初回リリースのため履歴上はなし）

### Fixed
- （初回リリースのため履歴上はなし）

### Known issues / 注意点
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ有効。未インストール時は警告を出してスキップする。
- .env の自動ロードはプロジェクトルートが特定できない場合はスキップされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で明示的に無効化可能）。
- ExecutionEngine / OrderManager は外部 Broker API や DB に依存するため、本番運用前に validate_config と十分なステージングテストを推奨します。

-----

この CHANGELOG はソースツリーの現在の実装から推測して作成しています。実際のリリースノートとして利用する際は、必要に応じて日付や文言の調整、細部の補足を行ってください。
CHANGELOG
=========

すべての変更は Keep a Changelog の書式に準拠しています。日付はリリース日または推定実装日を示しています（コードの内容から推測して作成）。

Unreleased
----------

- なし

[0.1.0] - 2026-04-21
--------------------

Added
- 基本パッケージ情報
  - パッケージバージョンを __version__="0.1.0" として公開。
- 環境設定/読み込み
  - .env と .env.local からの自動環境変数読み込み機能を実装（os 環境変数を優先、.env.local は上書き可能）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env ファイルのパース機能を独自実装。export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - Settings クラスを実装して、環境変数経由で各種設定（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、KABUSYS_ENV、LOG_LEVEL、各種閾値など）をプロパティとして提供。
  - 標準的な有効値チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）で不正な値は ValueError を送出。
- 環境設定ウィザード
  - python -m kabusys.config_setup による対話式ウィザードを追加。.env の初期作成・更新を支援し、シークレット項目はマスク表示、選択肢・デフォルト対応。
  - .env を保存するテンプレート（コメント付き）を出力する _write_env 実装。
- 設定検証 CLI
  - python -m kabusys.validate_config を追加。必須環境変数の有無、プレースホルダ値検出、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境（live）向けの追加ガードチェック（LINE 設定、KILL_FLAG_CLEAR_ON_START）等を行う。
  - --strict オプションで警告も失敗扱いにして exit(1) を返すモードを実装。
- 実行用スクリプト
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）を追加。paper_trading 環境では paper_trading 用 SQLite を使用して本番 DB と分離。
  - Monitoring 用起動スクリプト（python -m kabusys.run_monitoring）を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は environments にかかわらず本番 sqlite_path を使用。
  - プロセス優先度をセットするフック（set_process_priority を呼び出し）を起動時に実行。
- 発注実装（Execution）
  - OrderRecord: 注文状態の列挙 OrderState と状態遷移ロジックを純粋なデータモデルとして実装。許可された遷移を定義し、不正遷移時に InvalidStateTransitionError を発生させる。
  - OrderRepository（SQLite）と組み合わせる OrderManager を実装。create/send/sync/cancel の外向き API を提供。
    - create_order は signal_id に対する重複 active 注文を検出して DuplicateOrderError を送出。
    - send_order はクラッシュ耐性を考慮した 2 相永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を先に永続化 → OrderAccepted に遷移）を実装。OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order は broker 側の状態取得に基づいて部分約定や状態遷移を同期。Filled / Partial の際の qty/price 更新や OrderSent→Filled などのケースで中間状態 OrderAccepted を経由する補正ロジックを実装。
    - cancel_order は終端状態の判定（キャンセル不可状態の列挙）を行い、必要に応じて broker の cancel_order を呼ぶ。
  - ExecutionEngine:
    - セッション制御（シグナル処理時間帯、push ドレイン、セッション終了）を実装。
    - kill.flag の扱い（起動時の存在チェック、KILL_FLAG_CLEAR_ON_START による自動クリア動作）や PID ファイル書き出しを実装。
    - シグナル処理は Gate1（シグナルレベル）、Gate2（実行レベル・レート制限、リトライ/サーキットブレーカー）、発注タイミング計測（latency）および監視 DB へのログ出力を行う。
    - WebSocket push を受け取り _push_queue に投入、ドレイン時に sync_order と Gate3（ドローダウン監視）を実行し、必要なら kill_switch を発動する。
    - kill_switch は全 active 注文をキャンセルしループを停止する。
  - Broker クライアント
    - KabuStationClient を実装（httpx 同期版）。トークンを遅延取得し、401 発生時に自動再取得して 1 回リトライする実装。429 は RateLimitError、5xx は BrokerAPIError として扱う。
    - send_order/cancel_order/get_order_status を実装。send_order は成行時に Price=0 を強制するなどのサーバー拒否回避ロジックを含む。
    - kabu station のステータスコードマップ（1..7 → open/partial/filled/cancelled/rejected）を提供。
- 監視（Monitoring）
  - monitoring 用 DB 初期化ユーティリティを呼び出す init_monitoring_db の利用を run_monitoring/run_execution 起動時に実装（監視テーブルの存在を保証する冪等処理）。

Changed
- 設定/実行の分離設計
  - paper_trading 環境では監視と実行の DB を分離（paper_trading 用 SQLite を使用）し、本番 DB とデータの干渉が起きないように設計。
- .env 読み込みの優先順位明確化
  - OS 環境変数 > .env.local > .env の順で読み込む動作を公式化。

Fixed
- クラッシュ回復性の向上
  - send_order の実装で broker_order_id を先に永続化することで、ステップ間でのクラッシュ時にも Reconciliation で復旧できるようにした（Issue 想定の対策についての注釈あり）。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - 0 以下や非整数値が設定された場合はデフォルト（60 秒）にフォールバックする仕様を追加。

Deprecated
- なし

Removed
- なし

Security
- セキュリティ注意
  - .env ファイルには機密情報を含めるため、生成される .env に関して「絶対に Git にコミットしないこと」を明示。
  - config_setup の入力ではシークレット項目をマスク表示。

Notes / 実装上の注意
- PyYAML がインストールされていない環境では validate_config は YAML の内容検証をスキップし、警告を出すのみ。PyYAML を入れることで config/*.yaml のパース検証が有効になる。
- ExecutionEngine のタイミング判定はローカル時間（datetime.now().time()）を使用しており、ミリ秒切り捨てで比較される。
- OrderRecord は DB を直接操作しない純粋なビジネスロジックとして実装されており、永続化・問い合わせは OrderRepository 側で行う想定。
- get_order_status の実装（kabu station の API 特性に合わせ、全件取得→ID フィルタ）は一部 API の制約（id パラメータを無視するケース）を回避するための設計。

今後の改善候補（コードから推測）
- KabuStationClient の WebSocket push 処理と REST 部分のテストカバレッジ強化。
- config/*.yaml のスキーマ検証（存在する場合は JSON Schema 等で厳密検証）。
- ExecutionEngine のエラーハンドリングと Graceful shutdown に関する詳細テスト・補強。
- Rate limit やリトライ戦略のパラメタ化（環境変数経由で調整可能にする等）。

以上。コードの実装内容に基づき機能追加・変更点を要約しました。必要であれば各モジュール別により細かい差分説明や、チケット/イシューの対応関係の推測も作成します。
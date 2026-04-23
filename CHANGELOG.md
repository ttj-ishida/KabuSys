# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-23

初回公開リリース。主要な機能追加と設計上の要点を以下にまとめます。

### 追加 (Added)
- 全体
  - パッケージ初期版を提供（__version__ = 0.1.0）。
  - DuckDB / SQLite を利用したストレージ、監視・発注周りの基盤コンポーネントを実装。

- 設定関連
  - Settings クラスを実装。環境変数をラップしてプロパティ経由でアクセス可能に。
  - .env 自動ロード機能を追加（プロジェクトルートの .env / .env.local を読み込み）。OS の既存環境変数は保護され上書きされない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
  - 環境変数読み込み用の堅牢なパーサを実装（export プレフィックス、シングル／ダブルクォート内のエスケープ、行内コメントの取り扱いに対応）。

- CLI / ユーティリティ
  - config_setup: .env を対話式に生成・更新するウィザードを追加。秘密値はマスク表示、既存 .env の読み込みと Enter での再利用が可能。
  - validate_config: 起動前に .env と config/*.yaml の問題を検出する検証 CLI を追加。--strict フラグで警告も失敗扱いにできる。
  - 設定ウィザードはデフォルト・選択肢・説明付きで主要設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 通知等）を扱う。

- 実行・監視用スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。paper_trading モードでは専用の SQLite（paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
  - 両スクリプトでプロセス優先度設定（set_process_priority）、ログ設定のセットアップを行う。

- 発注系コア
  - ExecutionEngine: シグナルループ（発注窓口）と WebSocket push ドレインループを実装。kill.flag による安全停止、PID ファイル管理、Reconciliation 実行フローを実装。
  - EngineConfig によりセッション日時（発注開始/締切/終了）を設定可能。
  - OrderRecord: 注文状態を表す状態機械（OrderState）と遷移ロジックを実装。不正遷移は InvalidStateTransitionError を raise。
  - OrderManager: OrderRecord と OrderRepository を組み合わせた外向き API を提供（create_order / send_order / sync_order / cancel_order）。DuplicateOrder の検出、トランザクション的な発注フロー設計を実装。
    - send_order は「OrderSent を永続化 → broker 呼出し → broker_order_id を永続化 → OrderAccepted に遷移」の 2 相永続化を採用し、クラッシュ耐性と Reconciliation を意識した設計。
    - OrderSentPendingError（注文は送信されたが約定しない／保留ケース）を特別扱いし、broker_order_id を保持して再同期対象とする。
  - Reconciler（参照）を使った起動時リコンシリエーションの呼び出しに対応。

- ブローカークライアント
  - KabuStationClient を実装（httpx 同期クライアント）。トークン取得の遅延初期化、401 に対するトークン再取得と 1 回のリトライ処理、429 を RateLimitError にマッピング、JSON パース失敗を BrokerAPIError に変換するなど堅牢化を行った。
  - WebSocket の push を受け取り _push_queue に渡す stream_push サポート（client 側が提供する場合に使用）。

- 監視 DB
  - monitoring 用 SQLite テーブル初期化関数（init_monitoring_db）へのフックを設置。監視ループと実行ループで監視 DB の初期化・接続を行う。

### 変更 (Changed)
- 設定と挙動
  - KABUSYS_ENV の既定値は "development"。Settings と validate_config の双方で有効値チェックを実施（development / paper_trading / live）。
  - LOG_LEVEL に対して設定/検証を追加（INFO デフォルト、許容値: DEBUG/INFO/WARNING/ERROR/CRITICAL）。validate_config は不正値を警告、Settings は不正値で例外を送出するよう差異を持たせた。
  - 監視（run_monitoring）は KABUSYS_ENV に関わらず「本番 sqlite_path（設定値）」を使用する方針を明示。

- 発注ロジック
  - ExecutionEngine 側で size_multiplier の扱いを明確化（BUY のみ適用、100 株単位に丸め、0 以下はスキップ）。
  - シグナル実行前の Gate チェックを三段階（Gate1: シグナル検査、Gate2: エグゼキューション検査（レート制限）、Gate3: ドローダウン監視）で実施。Gate2 はリトライ（最大 3 回）、Circuit Breaker 発生時はシグナルループを停止する挙動。
  - push ハンドリング時は broker.get_positions() によりポートフォリオ評価を行い Gate3 を実行、必要なら kill_switch を発動。

- ファイル / パス処理
  - .env 書き出しテンプレートにセクション分け（J-Quants, kabu, LINE, DB, Kill Switch 等）を追加。
  - 設定検証（validate_config）で DUCKDB_PATH / SQLITE_PATH の親ディレクトリが存在しない場合に警告（起動時に自動作成される可能性を注記）。

### 修正 (Fixed)
- 安全性／堅牢性
  - send_order のフローを 2 相永続化にして、途中クラッシュ時でも broker_order_id を DB に残しリコンシリエーション可能に（Issue 想定: #32 に対処する設計）。
  - OrderRepository 側の UNIQUE 制約違反（signal_id の部分ユニークインデックス）を検出して DuplicateOrderError に変換する処理を OrderManager.create_order で実装（DB エラーの意味を分かりやすく）。
  - ExecutionEngine.run_session の起動時に kill.flag が存在する場合の挙動を明確化。KILL_FLAG_CLEAR_ON_START=1 のときは自動クリアするオプションをサポート。
  - get_poll_interval（監視）で不正な値（0 以下や整数以外）を検出してデフォルトへフォールバックする実装により time.sleep に渡しての ValueError を防止。

- エラー処理
  - KabuStationClient の HTTP/JSON エラー（タイムアウト、ネットワーク、非 JSON レスポンス、ステータスコード別処理）を詳細にマッピングし、上位での扱いを容易に。
  - validate_config で PyYAML が未インストールの場合に YAML 内容検証をスキップして警告を出すようにし、環境に依存せず実行できるように改善。

### 削除 (Removed)
- 該当なし（初回リリースにつき削除はなし）。

### セキュリティ (Security)
- 環境変数の取り扱いにおいて、secret フィールド（.env ウィザード）をマスク表示し、.env の Git コミット禁止を明示するテンプレートを追加。
- KabuStationClient において認証トークンを内部で管理し、401 発生時の即時再取得を行うことで認証失敗の持続を防止。

---

注意:
- 本 CHANGELOG は提供されたコードからの仕様・挙動を基に推測して作成したものであり、実際のコミット履歴を元にしたものではありません。実際の変更履歴（コミット単位）は git log 等で別途管理してください。
# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。  

注: この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。

## [Unreleased]

（未リリースの変更があればここに記載）

---

## [0.1.0] - 2026-04-23

初回公開リリース。自動売買システム KabuSys のコア機能と運用用ユーティリティを実装。

### Added
- 全体
  - パッケージの初期バージョンを定義（__version__ = "0.1.0"）。
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を基準に探索）。
  - 環境変数自動ロード機能を追加（プロジェクトルート存在時に .env, .env.local を読み込み、OS 環境変数は保護）。
  - .env ファイルの堅牢なパーサーを実装（export プレフィックス、引用符付き値、エスケープ、インラインコメント処理に対応）。

- 設定管理
  - Settings クラスを実装：環境変数を経由した設定取得 API を提供（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン等）。
  - 環境値のバリデーションを実装（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等は許容値チェックを行い不正値時は ValueError を送出）。
  - 環境変数自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。

- CLI / ユーティリティ
  - 環境設定ウィザード（kabusys.config_setup）を追加：
    - 対話式に .env を初期作成 / 更新するウィザード。
    - シークレット値はマスク表示、選択肢/デフォルトのサポート、既存 .env 読み込み。
    - 保存前の確認と .env の整形済み出力。
  - 設定検証ツール（kabusys.validate_config）を追加：
    - 必須 / 任意の環境変数チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の検証。
    - DB パス（DUCKDB / SQLITE）の親ディレクトリ存在確認。
    - config/*.yaml の存在確認と（PyYAML がインストールされていれば）パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の危険設定検出）。
    - --strict オプションで警告を失敗扱いにできる。
  
- 実行スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加：
    - ExecutionEngine の初期化、PID/停止フラグ管理、DB 接続（paper_trading 時は専用 SQLite を使用）、スレッド起動・終了ロジックを備える。
    - プロセス優先度設定、stop フラグ検知による起動抑止。
  - 監視スクリプト（kabusys.run_monitoring）を追加：
    - SystemMonitor のポーリングループを開始。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用。

- 発注 / 実行系
  - ExecutionEngine を実装：
    - シグナル読み込み（DuckDB）、シグナル窓（8:50–9:10）の処理、WebSocket push ドレインループ（9:10–15:30）を含むセッション実行フロー。
    - Gate1（シグナルレベル）、Gate2（実行レベル・レート制限）、Gate3（ポートフォリオ・ドローダウン）を用いたリスクチェックと kill_switch 発動ロジック。
    - position_entries の更新（発注成功時に約定予定日を記録）や監視 DB へのトレードイベントログ登録をサポート。
    - WebSocket push の受信を別スレッドで処理し、push に基づく同期と Gate3 の評価を行う。
    - kill.flag の検査と KILL_FLAG_CLEAR_ON_START のオプション対応（起動時の自動クリア）。

  - OrderRecord（状態機械のモデル）を実装：
    - 注文状態（created, sent, accepted, partial, filled, closed, cancelled, rejected）を enum として定義。
    - 許可遷移表を定義し、不正遷移時は InvalidStateTransitionError を raise。
    - transition_to による安全な状態遷移とメタ情報（broker_order_id, filled_qty, avg_fill_price, error_message, updated_at）更新を実装。

  - OrderManager を実装：
    - create_order: signal_id 単位での重複検出（部分ユニークインデックス / DB の整合性を考慮）と DuplicateOrderError の導入。
    - send_order: クラッシュに耐える 2 相永続化フローを採用（OrderSent を DB に保存 → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移）。
      - OrderRejectedError を受け取ると Rejected に遷移。
      - OrderSentPendingError（注文番号は渡るが約定しない状態）は broker_order_id を保存した上で OrderSent のまま再送出（Reconciliation 対象）。
    - sync_order: broker 側の状態照会から DB 状態を同期。部分約定の進行（filled_qty/avg_fill_price）の更新や OrderSent→Filled のケースで一時的に OrderAccepted を挟む復旧処理を実装。
    - cancel_order: キャンセル不可状態の判定（Filled を含む）と、可能な場合は broker へキャンセル要求して Cancelled に遷移。

  - Broker クライアント
    - KabuStationClient（kabu station REST API クライアント）を実装：
      - httpx を用いた同期クライアント。トークン取得（/token）を内部で管理し、401 時に自動リトライでトークンを再取得。
      - レスポンス JSON パースの失敗やタイムアウト/ネットワークエラーを BrokerAPIError に変換。
      - 429 を受けた場合は RateLimitError を送出。
      - kabu station のステータスコード→内部ステータス（open / partial / filled / cancelled / rejected）マッピングを実装。
      - 将来的な async 対応を見据えた設計。

- 監視・DB
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を呼び出して監視用テーブルを保障する実装（冪等）。
  - duckdb と sqlite の併用を前提にした設計（分析用に DuckDB、監視/注文履歴に SQLite）。

- 安全性・運用
  - PID ファイル管理、stop_requested.flag / kill.flag による外部制御、kill_switch による全 active 注文キャンセル処理を実装。
  - プロセス優先度設定ユーティリティを呼び出すことで実行時の優先度を調整するフローを導入。
  - config_setup による .env 生成時の注意書き（.env を絶対に Git にコミットしない等）を出力。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Known limitations
- config/*.yaml の内容検証は PyYAML がインストールされている場合にのみ行われる。未インストール時はパース検証をスキップして警告を出力する。
- .env の自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。配布後に予期せず環境変数が上書きされることを避けるため、OS 環境変数は protected として自動上書きを防止している。
- KILL_FLAG_CLEAR_ON_START=1 は本番環境では危険（kill.flag を無視して起動する）ため、validate_config や config_setup で注意喚起を行う。
- ExecutionEngine / OrderManager のリコンシリエーションや broker API に依存する挙動（ネットワーク障害・部分約定等）は実運用での検証が必要。
- WebSocket push 機能は broker 側の stream_push API を想定しており、未対応ブローカーではスレッド起動がスキップされる旨をログ出力する。

---

（以降リリースは日付と変更内容を追加してください）
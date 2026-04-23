# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリース（0.1.0）に含まれる機能をコードベースから推測してまとめています。

<!-- 参考: https://keepachangelog.com/ja/1.0.0/ -->

## [Unreleased]

## [0.1.0] - 2026-04-23

### 追加 (Added)
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」のコア部分を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 設定・環境管理
  - 環境変数 / .env の自動読み込み機能を実装（OS環境変数 > .env.local > .env の優先順）。
  - .env ファイルのパース機能を独自実装。以下の仕様に対応:
    - 空行・コメント行（#）を無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォート、バックラッシュエスケープを考慮した値の読み取り
    - クォートなしの場合、インラインコメント扱いの判定（'#' の直前が空白/タブの場合のみ）
  - 環境変数の自動読み込みを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを実装し、アプリケーション設定（トークン・パスワード・DBパス・環境・ログレベル等）をプロパティ経由で提供。
  - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）を実装。
  - 環境値（KABUSYS_ENV / LOG_LEVEL 等）の検証を実装（不正な値は ValueError を発生）。

- 環境設定ウィザード CLI
  - 対話式ウィザード `kabusys.config_setup` を実装し、.env の初期作成・更新を支援。
  - .env の既存値読み込み、シークレット入力（表示マスク）、選択肢/デフォルト表示、保存確認を提供。
  - `.env` 書き込みフォーマットを定義（コメント付、Gitコミット禁止の注意書き含む）。
  - CLI 引数で .env ファイルパスを指定可能（`--env-file`）。

- 設定検証ツール CLI
  - `kabusys.validate_config` を実装。起動前に .env と config/*.yaml の基本的な不備を検出。
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、live 環境時の警告（LINE通知設定、KILL_FLAG_CLEAR_ON_START の危険設定など）。
  - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（存在しない場合は警告）。
  - config/*.yaml の存在確認と PyYAML がインストールされている場合の YAML パース検証（PyYAML 未インストール時はスキップ）。
  - `--strict` オプションで警告を失敗扱い（exit(1)）にできる。

- 実行スクリプト
  - `run_execution`:
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
    - プロセス優先度の設定、PID ファイル管理、停止フラグ（data/stop_requested.flag）検出を実装。
    - DuckDB と SQLite の接続を行い、監視DB初期化を呼び出す。
  - `run_monitoring`:
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検出、例外発生時のロギング、コネクションクローズ処理を実装。

- 注文実行系（Execution）
  - ExecutionEngine:
    - シグナル処理（デイリーの発注ウィンドウ: signal_send_start / signal_send_end）と push ドレインループ（市場クローズまで）を実装。
    - run_session でリコンシリエーションの実行、kill.flag の検査/クリア、PID ファイル書き出しを実施。
    - WebSocket スレッド（broker が stream_push を提供している場合）による push イベント受信・処理をサポート。
    - シグナル処理時に 3 段階のリスクゲートを適用（Gate1: シグナルレベル、Gate2: 実行レート制御、Gate3: ドローダウン監視）。
    - position_entries の更新（発注成功時に DuckDB へ書き込み、BUY/Sell の取り扱い差分を反映）。
    - 監視DB（MonitoringDB）への発注イベント記録（latency 等）を行うフックを提供。

  - OrderRecord
    - 注文状態遷移を表現する OrderState Enum と状態遷移ルール（_ALLOWED_TRANSITIONS）を実装。
    - OrderRecord データクラスを提供（状態遷移検証、updated_at 自動更新、オプションフィールド更新）。
    - 不正遷移時に InvalidStateTransitionError を発生。

  - OrderManager
    - Signal を受け取り OrderRecord を生成、DB（OrderRepository）へ保存する create_order を実装。重複 (same signal_id の active 注文) は DuplicateOrderError を発生。
    - send_order: 2相永続化戦略を採用（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を保存 → OrderAccepted へ遷移）し、クラッシュ耐性を考慮した設計。
      - OrderRejectedError / OrderSentPendingError の扱いを実装（pending は broker_order_id を保存して OrderSent のまま残す）。
    - sync_order: broker 側の注文状態に同期。ステータスマッピングと部分約定の更新をサポート。OrderSent→Filled/Partial を中継で OrderAccepted を経由させる等の調整を実装。
    - cancel_order: 終端状態のキャンセル不可判定、broker API 実行、Cancelled への遷移を実装。

  - Broker API / クライアント
    - KabuStationClient（kabu station REST API の同期クライアント）を実装。
      - httpx を利用し、認証トークン取得ロジック（遅延初期化、401 時の再取得と1回リトライ）を実装。
      - レスポンス JSON パースの例外変換、ネットワーク/タイムアウト/サーバーエラー/レート制限（429）に対する例外ハンドリングを実装。
      - kabu station の注文状態コード→内部ステータスマッピングを定義。
      - 将来的な async 対応を見据えた設計注記（httpx.AsyncClient へ差し替え可能）。

- リスク管理・リコンシリエーション
  - RiskManager / Reconciler と統合するためのフックを ExecutionEngine / OrderManager 等に追加（RiskConfig のサンプル値も含む）。
  - Reconciler 呼び出し時のログ出力（同期結果のサマリー）を実装。

- 監視
  - MonitoringDB 初期化（init_monitoring_db）呼び出し箇所を実装（監視テーブルの冪等な準備）。
  - SystemMonitor のポーリングループ実行スクリプトを提供。

- ユーティリティ
  - ロギングセットアップ（setup_logging）やプロセス優先度設定ユーティリティ（set_process_priority）を利用するコードパスを追加。

### 変更 (Changed)
- 設定/挙動に関する既定値を明記:
  - DUCKDB_PATH / SQLITE_PATH / KABU_API_BASE_URL / LOG_LEVEL 等のデフォルト値を明確化。
  - Monitoring は常に本番の sqlite_path を参照する仕様に変更（設計上の決定）。

### 修正 (Fixed)
- .env 読み込みでのファイル入出力エラー時に警告を出して処理を継続する耐障害処理を追加（_load_env_file）。

### 注意点 (Notes)
- config/*.yaml の内容検証には PyYAML が必要。未インストールの場合は検証をスキップして警告を出す。
- ExecutionEngine / run_execution は外部コンポーネント（BrokerClientFactory, RiskManager, Reconciler, OrderRepository 等）に依存しており、これらの実装により実行時挙動が変化する。
- kill.flag / stop_requested.flag / PID ファイルなどファイルベースのインタラクションに依存するため、実稼働環境ではファイルパーミッションや存在チェックに注意。

### セキュリティ (Security)
- .env ファイルにはシークレットが含まれるため、.env をリポジトリにコミットしない旨を .env ヘッダに明示。

---

この CHANGELOG はコードから推測して作成しています。実際の変更履歴やリリースノートは開発履歴（コミットログ、チケット等）を基に確定してください。
# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

現在の日付: 2026-04-23

## [Unreleased]

- ドキュメントや小修正を追加予定。

---

## [0.1.0] - 2026-04-23

初回公開リリース。以下の主要機能・設計を実装しています。

### 追加 (Added)
- 全体
  - 日本株自動売買システム "KabuSys" の初期実装を追加。
  - パッケージバージョンを `0.1.0` に設定。

- 設定・環境関連
  - Settings クラス（kabusys.config）を実装し、環境変数から各種設定を取得。
  - .env 自動読み込み機能を実装：
    - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を読み込む。
    - OS 環境変数を保護する override/protected の読み込み順序をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - .env のパースロジックを強化：
    - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理に対応。
  - 環境設定ウィザード CLI（kabusys.config_setup）を追加：
    - 対話式で .env を生成/更新するウィザード。
    - 初期値、選択肢、シークレット項目のマスク表示、保存確認を実装。
    - .env ファイルの読み書きフォーマットを定義。

- 設定検証
  - validate_config CLI（kabusys.validate_config）を追加：
    - 必須環境変数の有無チェック、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パース検証、live 環境向け追加ガードを実装。
    - --strict オプションで警告を FAIL として扱う。

- 実行・監視プロセス
  - 実行スクリプト:
    - run_execution: ExecutionEngine の起動スクリプトを追加。paper_trading の場合は専用 SQLite（paper_trading.db）を使用して本番 DB と完全分離。
    - run_monitoring: SystemMonitor の定期ポーリングループを実装。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用。
  - プロセス優先度設定・ログ初期化を行うユーティリティ呼び出しを組み込み（setup_logging, set_process_priority）。

- 発注エンジン / 実装
  - ExecutionEngine（kabusys.execution.execution_engine）を実装：
    - シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30） のセッションループ。
    - Gate1/2/3 によるリスクチェックフロー（シグナル検査、実行レート制限、ポートフォリオドローダウン）を実装。
    - position_entries への約定記録、発注遅延計測と監視 DB へのロギング連携を実装。
    - WebSocket push の受信 -> _push_queue による非同期処理を実装。
    - kill.flag / PID ファイルの取り扱い（起動時チェック、KILL_FLAG_CLEAR_ON_START の挙動）を実装。

  - OrderRecord（kabusys.execution.order_record）:
    - 注文状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と状態遷移ルールを定義。
    - 不正遷移時に InvalidStateTransitionError を送出するロジックを実装。

  - OrderManager（kabusys.execution.order_manager）:
    - signal_id 単位の重複防止（DuplicateOrderError）。
    - create_order / send_order / sync_order / cancel_order のフロー実装。
    - send_order においてクラッシュ耐性を考慮した永続化順序（OrderSent の先行コミット、broker_order_id の先コミット、OrderAccepted の遷移）を採用。
    - OrderSentPendingError の取り扱い、OrderRejectedError キャッチによる Rejected 遷移処理。
    - sync_order による broker 側ステータスの同期（部分約定の進行はフィールド更新で対応）。
    - cancel_order は終端状態の検査後に broker へキャンセル要求。

  - Reconciler / RiskManager / OrderRepository 周辺の組合せで実運用ワークフローを実現（各コンポーネントの接続点を実装）。

- ブローカークライアント
  - KabuStationClient（kabusys.execution.kabu_client）を実装：
    - httpx を用いた同期 REST クライアント。
    - トークン取得の遅延初期化と 401 発生時の自動再取得・リトライ実装。
    - レスポンス JSON パースの例外変換、タイムアウト/ネットワーク例外の BrokerAPIError 変換、429 に対する RateLimitError を実装。
    - kabu station の状態コード -> 内部ステータスへのマッピングを実装。
    - 将来的な WebSocket（stream_push）に対応するための設計（stream_push を持つクライアントを想定）。

- 監視 DB / DuckDB
  - duckdb と sqlite3 を利用した DB 接続処理を各起動スクリプトに実装。
  - monitoring_db の初期化処理（init_monitoring_db）を起動時に呼び出し、監視テーブルの整合性を確保。

### 変更 (Changed)
- Settings/設定系の挙動を明確化：
  - KABUSYS_ENV と LOG_LEVEL の検証を Settings 側で行い、不正値は ValueError を送出するように実装。
  - PAPER_FILL_MODE に対する許容値チェックを追加（instant/partial/never/reject）。

- ExecutionEngine の設計：
  - セッション起動時に Reconciliation を実行（reconciler が提供されている場合のみ）し、同期結果をログ出力する。

### 修正 (Fixed)
- 発注フローのクラッシュ時の不整合を減らすため、send_order の永続化および例外処理フローを設計（OrderSentPendingError の扱いなど）。

### 注意点 / 互換性のある破壊的変更 (BREAKING)
- Settings のプロパティが不正値である場合に ValueError を投げる挙動は、以前に黙ってフォールバックしていたコードとの互換性問題を引き起こす可能性があります。環境変数設定は .env ウィザードや validate_config で事前チェックすることを推奨します。

### セキュリティ (Security)
- .env ファイルは Git にコミットしない旨を .env テンプレートのヘッダに明示。

---

今後の予定（例）
- async 対応の検討（httpx.AsyncClient による非同期化）。
- 単体テストの追加（OrderRecord / OrderManager / ExecutionEngine 等）。
- run_* スクリプトの systemd ユニット例の提供。
- より詳細な監視（監視イベントのダッシュボード化）と障害通知強化（LINE 通知のテンプレ化）。

---

脚注:
- 本 CHANGELOG は提供されたソースコードからの推測に基づき作成しています。実装意図や今後の変更計画はリポジトリの公式ドキュメントを参照してください。
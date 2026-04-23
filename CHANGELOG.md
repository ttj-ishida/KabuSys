# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

## [0.1.0] - 2026-04-23

初回公開リリース

### 追加 (Added)
- 全体
  - Python パッケージ「KabuSys」初期実装を追加。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 設定管理
  - Settings クラス（kabusys.config）を追加。環境変数からアプリケーション設定を取得する統一 API を提供（例: jquants_refresh_token, kabu_api_password, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。優先順位: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理などに対応。

- 設定ウィザード CLI
  - kabusys.config_setup モジュールに対話式ウィザードを追加。.env の新規作成／更新を支援する run_wizard を提供。
  - 設定項目の定義 (KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等) と、シークレット値のマスク表示、選択肢・デフォルト提示を実装。
  - .env ファイルへの書き出しロジックを追加（書式コメント付き）。ユーザー確認フローを実装。

- 設定検証 CLI
  - kabusys.validate_config を追加。.env と config/*.yaml の起動前検証を行う CLI を提供。
  - 検証内容:
    - 必須環境変数の存在チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - プレースホルダ値（末尾が "_here" や "your_value"）の警告。
    - KABUSYS_ENV 値検証（development/paper_trading/live）。live の場合は注意喚起の警告。
    - LOG_LEVEL 妥当性チェック。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（存在しなければ警告）。
    - config/*.yaml の存在チェックと、PyYAML がある場合は YAML のパース検査（PyYAML 未インストール時はパース検査をスキップして警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意）。
  - --strict オプションを提供（警告も FAIL として exit(1)）。

- 実行スクリプト
  - run_execution: ExecutionEngine を起動するユーティリティスクリプトを追加。
    - paper_trading 環境時は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - プロセス優先度設定、PID/stop flag 管理、DB（SQLite / DuckDB）接続・クローズ処理を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバック。
    - 監視 DB 接続は環境にかかわらず本番 sqlite_path を使用。

- 発注エンジン / 実行ロジック
  - ExecutionEngine を追加（kabusys.execution.execution_engine）。
    - シグナル処理（指定時間帯）と WebSocket push ドレインループを持つセッション実行フローを実装。
    - kill.flag の検査・KILL_FLAG_CLEAR_ON_START による起動時挙動、PID ファイル書き込み／削除の管理を実装。
    - シグナル読み出しは DuckDB から行い、size_multiplier の適用、発注前 Gate（Gate1: シグナルレベル、Gate2: 実行レート制限、Gate3: ドローダウン監視）を実装。
    - WebSocket push を処理するスレッドを用意し、プッシュ通知から同期（sync_order）や Gate3 評価を実行。
    - 発注時のレイテンシ計測・監視 DB への記録処理（monitoring_db が渡された場合）。

- 注文管理
  - OrderRecord（kabusys.execution.order_record）: 注文状態列挙（OrderState）と状態遷移検証ロジックを実装。InvalidStateTransitionError を定義。
  - OrderManager（kabusys.execution.order_manager）:
    - create_order: signal_id の重複チェック（DB 側の UNIQUE 制約を含む）を実装し、DuplicateOrderError を定義。
    - send_order: クラッシュ耐性を考慮した 2 相永続化戦略を実装（OrderSent を DB に永続化 → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移）。OrderRejectedError / OrderSentPendingError のハンドリングを実装。
    - sync_order: broker 側の注文状態照合（status マッピング）とレコード更新。部分約定の進行は直接フィールド更新して反映。
    - cancel_order: 終端状態のチェックと broker cancel 呼び出し、Cancelled への遷移を実装。

- ブローカークライアント（kabu station）
  - KabuStationClient（kabusys.execution.kabu_client）を実装。
    - httpx を用いた同期 REST クライアント。
    - トークン取得（遅延初期化）と 401 時の自動リトライ（トークン再取得）を実装。
    - レスポンス JSON パース失敗時に BrokerAPIError を変換、429 を RateLimitError にマップ。
    - kabu station のステータスコードを内部ステータスにマッピング（open/partial/filled/cancelled/rejected）。
    - WebSocket push (stream_push) の受け取りに対応するための設計（stream_push を持たない broker の場合はスキップ）。

- 監視関連
  - monitoring_db 初期化フロー（init_monitoring_db）や SystemMonitor（別モジュール参照）を run_monitoring/run_execution から呼び出す形で統合。監視 DB の初期化は冪等に行う。

- ユーティリティ
  - 簡易的な process priority 設定、logging setup などを利用（外部モジュールとして参照・利用）。

### 変更 (Changed)
- 初期リリースのため変更履歴はなし。

### 修正 (Fixed)
- 初期リリースのため修正履歴はなし。

### 既知の制限 / 注意点
- YAML 検証は PyYAML がインストールされている場合のみ行われます。PyYAML 未導入環境では validate_config は YAML の中身検証をスキップして警告を出します。
- KabuStationClient は同期 httpx.Client 実装であり、将来的に async 対応する場合は httpx.AsyncClient へ差し替えが容易な設計になっていますが、現状は同期 API です。
- ExecutionEngine の時間帯・ループ動作はローカル時刻に依存します。テスト時は内部メソッドを直接呼び出して検証する想定です。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布環境でプロジェクトルートが検出できない場合は自動読み込みがスキップされます（この場合は明示的な環境変数設定が必要）。

### 互換性に関する注記
- 初回リリースのため後方互換性の議論は未適用。将来的に環境変数キー名・設定の変更を行う場合は Breaking Change として明示します。

---

今後の予定:
- Broker API のエラーハンドリング強化、テストカバレッジの拡充、async 対応検討、監視・アラート周りの追加改良を予定しています。
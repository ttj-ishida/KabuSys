CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
このファイルはコードベースの内容から推測して作成したリリースノートです。

Unreleased
----------
- （なし）

0.1.0 - 2026-04-22
------------------
### Added
- プロジェクト初回リリース。
- 環境設定・読み込み
  - .env / .env.local を自動で読み込む仕組み（OS 環境変数を保護）。プロジェクトルートは .git または pyproject.toml を基準に探索（src/kabusys/config.py）。
  - .env の行パーサ実装（export 形式・クォート・インラインコメント・エスケープ対応）。不正行は無視。
  - Settings クラスを提供し、環境変数から型付きの設定を取得可能（トークン・パスワード・DB パス・PID/kill flag・閾値等）（src/kabusys/config.py）。
  - 環境変数の必須チェック関数（_require）により未設定時は ValueError を発生。
- 設定ウィザード CLI
  - 対話式ウィザードで .env を作成／更新するツール（src/kabusys/config_setup.py）。
  - デフォルト値、選択肢（choices）、シークレット入力、既存 .env の読み取り、保存プレビューをサポート。
- 設定検証 CLI
  - .env と config/*.yaml を起動前に検証する CLI（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ確認、YAML パース（PyYAML が存在する場合）、本番環境時の追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START）を実施。
  - --strict オプションで警告も失敗扱いとして exit(1)。
- 実行スクリプト
  - 実行エンジン起動用スクリプト（src/kabusys/run_execution.py）
    - paper_trading モードでは paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - プロセス優先度を高く設定する仕組み呼び出し。
    - 停止フラグ検出による安全停止。
  - 監視用ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
- 注文・実行基盤
  - ExecutionEngine（Signal Queue Pull 型発注エンジン）を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（8:50–9:10）と push ドレイン（9:10–15:30）を含むセッションフロー。
    - PID ファイル管理、kill.flag の起動時取り扱い（KILL_FLAG_CLEAR_ON_START の挙動）を実装。
    - WebSocket push を受けて処理するワーカー実装（stream_push を持つ broker のみ）。
    - Gate1（シグナルレベル）、Gate2（エグゼキューション制御／レート制限・サーキットブレーカー）、Gate3（ドローダウン監視による kill switch）を組み合わせたリスク制御フロー。
    - 発注後の position_entries 書き込み（DuckDB を使用、次営業日で fill_date を計算）。
    - 監視DB（MonitoringDB）への発注イベントログ書き込みフック（存在する場合）。
  - OrderRecord（状態遷移モデル）
    - ステートマシン（OrderCreated / OrderSent / OrderAccepted / PartialFill / Filled / Closed / Cancelled / Rejected）と許容遷移を定義（src/kabusys/execution/order_record.py）。
    - transition_to による遷移検証・更新（updated_at 自動更新、オプションフィールド更新）。
  - OrderManager（OrderRecord と OrderRepository を組み合わせた外向き API）
    - create_order: signal_id に対する重複注文防止（DB の部分ユニーク制約違反を DuplicateOrderError に変換）。（src/kabusys/execution/order_manager.py）
    - send_order: クラッシュ安全な 2 相永続化フロー（OrderSent 永続化 → broker 呼び出し → broker_order_id 先コミット → OrderAccepted へ遷移）を実装。OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order: broker 側のステータス取得による同期ロジック（部分約定の更新や OrderSent → Filled/PartialFill の補正経路を含む）。
    - cancel_order: キャンセル可能判定（終端状態は不可）と broker 呼び出し。
- broker クライアント（kabu station）
  - KabuStationClient を実装（httpx 同期クライアント）（src/kabusys/execution/kabu_client.py）。
    - トークン管理（遅延取得、401 時に再取得してリトライ）、JSON パースエラーやネットワーク例外の変換。
    - HTTP ステータスに基づく RateLimitError / BrokerAPIError の発生。
    - push（WebSocket）受信 via websocket ライブラリ のための stream_push 想定（WebSocket 用フックを提供）。
    - kabu station の状態コード→内部ステータス変換マップを定義。
- データベース初期化・監視
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を使用する呼び出し箇所を run_execution / run_monitoring で実行（監視テーブルの存在保証）。
  - DuckDB（分析用）と SQLite（監視・注文履歴用）のハイブリッド利用を想定。
- リスク管理・再照合
  - RiskManager / Reconciler を統合する設計（ExecutionEngine が Reconciler をオプションで実行）。
  - Reconciliation により broker 側と DB の乖離を修正するフローを想定（実行時のログ出力がある仕様）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- .env は Git にコミットしない旨を .env ヘッダに明記（config_setup にて生成）。

注記（運用上の重要ポイント）
- validate_config を実行して環境変数や YAML の整合性を事前に確認してください（python -m kabusys.validate_config）。--strict モードで警告を失敗扱いにできます。
- paper_trading モードでは DB を分離するため、本番データを汚染するリスクが低減されます。ただし設定ミスで live モードが有効になっていると実際に発注が行われます。KABUSYS_ENV=live の場合は特に注意してください。
- kill.flag（KILL_FLAG_PATH）および KILL_FLAG_CLEAR_ON_START の設定により起動時・実行時の安全挙動が変わります。プロダクションでは自動クリア（1）を推奨しません。
- PyYAML 未インストール時は YAML 内容検証がスキップされます（validate_config が警告）。

今後の改善案（コードから推測）
- 非同期 httpx.AsyncClient ベースの非同期対応（KabuStationClient の将来的な移行ポイントとして明示）。
- より詳細な監視メトリクス（スループット・エラー率）と外部アラート統合の強化。
- config/*.yaml のスキーマ検証導入（JSON Schema 等）と CI での自動チェック。

---  
（この CHANGELOG は配布済みのコード内容から推測して作成しています。実際のコミット履歴が存在する場合はそれに合わせて更新してください。）
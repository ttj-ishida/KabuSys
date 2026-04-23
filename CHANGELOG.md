# Changelog

すべての注目すべき変更をこのファイルに記載します。  
このプロジェクトは Keep a Changelog に準拠しています。  

このファイルには、バージョン履歴とその要約（追加、変更、修正、内部的変更など）を日本語で記載しています。

## [Unreleased]

（現在の開発中の変更点はここに記載してください）

---

## [0.1.0] - 2026-04-23

初回リリース。KabuSys のコア設定管理、起動スクリプト、発注エンジン、監視ループ、発注関連ロジックを実装しました。

### Added
- 設定管理
  - kabusys.config: Settings クラスを導入。環境変数経由で設定を提供。
    - 必須値取得用の _require()、KABUSYS_ENV / LOG_LEVEL 等の検証を備えたプロパティを提供。
  - .env 自動ロード
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み。
    - OS 環境変数を保護する override / protected の仕組みを導入。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - .env パーサ
    - export 形式、クォートされた値、バックスラッシュによるエスケープ、インラインコメント処理を考慮した堅牢なパーサを実装。

- 設定ウィザード & 検証
  - kabusys.config_setup: 対話式ウィザードで .env を生成／更新する CLI を追加。
    - シークレット項目のマスク表示、選択肢やデフォルト値の提示、保存確認を実装。
    - 書き出しテンプレート（コメント付き）を生成。
  - kabusys.validate_config: 起動前に設定不備を検出する検証 CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と YAML パース検証（PyYAML が無ければ警告）を実施。
    - --strict オプションで警告も FAIL 扱いにできる。

- 実行／監視起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイント。
    - paper_trading 環境では paper_trading 用の SQLite DB を使用して本番 DB と分離。
    - PID/stop フラグ管理、プロセス優先度設定、ログ設定の初期化を行う。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。

- 発注関連コア
  - execution/order_record.py: OrderRecord（状態マシン）を純粋なビジネスロジックとして実装。
    - OrderState 列挙、許可される遷移マップ、InvalidStateTransitionError、transition_to によりタイムスタンプ等を管理。
  - execution/order_manager.py: DB（OrderRepository） と OrderRecord を結合した外向き API を実装。
    - create_order（signal 単位の重複検出、UUID 発番）、send_order（クラッシュ耐性を考慮した永続化順序）、sync_order（broker と同期）、cancel_order を提供。
    - DuplicateOrderError を導入。SQLite の部分ユニーク制約違反を DuplicateOrderError に変換する処理あり。
    - OrderSentPendingError の取り扱い（broker_order_id を保存して OrderSent のまま残す）を実装。
  - execution/execution_engine.py: Signal Queue Pull 型の発注エンジンを実装。
    - シグナル処理窓口（デフォルト 8:50–9:10）、WebSocket push ドレイン（9:10–15:30）をサポート。
    - Gate1/2/3 によるリスクチェックフローを導入（シグナルレベル検査、エグゼキューションレベル検査（レート制限とサーキットブレーカー）、ドローダウン検査）。
    - kill_switch の実装：全 active 注文のキャンセルとループ停止。
    - Reconciliation 用の reconciler を呼び出す仕組みを実装（起動時）。
    - position_entries の DuckDB 書き込み（約定日 = 翌営業日）と失敗時のフォールバック。
    - 発注レイテンシの監視 DB へのロギング機能（MonitoringDB を注入可）。
    - WebSocket push の stream_push が存在しない broker の場合はスキップして動作。

- broker / kabu クライアント
  - execution/kabu_client.py: KabuStationClient を実装。
    - httpx を用いた同期 REST クライアント。トークン取得、401 時の再取得＋リトライ、HTTP エラーの BrokerAPIError / RateLimitError への変換を実装。
    - WebSocket 受信用の stream_push（存在する場合）に接続する設計を想定。

- データベース・監視
  - duckdb と sqlite3 を組み合わせたデータアクセス。
  - 監視初期化 init_monitoring_db が実行開始時に呼ばれるようにした（冪等性確保）。
  - Monitoring 用のログ（イベント）を書き込むフローを追加。

- その他ユーティリティ
  - プロセス優先度設定（set_process_priority）と共通ログ設定（setup_logging）を呼び出す起動シーケンスを導入。
  - 停止フラグファイル（data/stop_requested.flag）による外部停止制御。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 設定ウィザードと表示でシークレット値はマスク表示（画面上）。
- .env を誤って Git にコミットしないよう書き込みテンプレートに注意喚起コメントを挿入。

### Internal
- コードはモジュール分割を行い、発注ロジック（純粋ロジック）と永続化（OrderRepository）を分離。これにより単体テストやリコンシリエーションの実装が容易になっています。
- クラッシュ時の整合性を考慮した永続化手順（OrderSent の永続化 → broker 呼び出し → broker_order_id の先行コミット → OrderAccepted）を設計・実装しています（Issue #32 に関連する再設計を想定した実装）。
- 動作に依存する外部パッケージ（例: PyYAML, httpx, websocket, duckdb）について、存在しない場合は適切に警告や例外処理を行う設計。

---

作業内容の詳細や改善案、既知の制限事項はドキュメントやコード内の docstring / コメントを参照してください。必要であれば各変更点をさらに分解したリリースノート（例: 小さなチケットやコミットごとの詳細）を作成できます。
CHANGELOG
=========
（このプロジェクトは Keep a Changelog の形式に準拠しています。安定版リリースごとにエントリを追加してください。）

Unreleased
----------
- （なし）

[0.1.0] - 2026-04-22
--------------------
Added
- 基本パッケージ初期実装を追加。
  - 自動設定読み込み/管理:
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。OS 環境変数を保護する保護機構を備え、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって自動ロードを無効化可能。
    - 高度な .env パーサを実装（export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントのルールに対応）。
  - Settings クラスを実装し、環境変数から型安全に設定を提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定 等）。
  - 設定ウィザード CLI（python -m kabusys.config_setup）を追加:
    - 対話式に .env を作成・更新するウィザード、シークレット値のマスク表示、既存 .env の読み込み・再利用、テンプレート出力機能。
  - 設定検証 CLI（python -m kabusys.validate_config）を追加:
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリチェック、config/*.yaml の存在と YAML パース検証（PyYAML インストールの有無に応じてスキップ可能）。
    - --strict オプションで警告も FAIL 扱いにできる。
  - 実行系スクリプトを追加:
    - 実行エンジン起動スクリプト（python -m kabusys.run_execution）。
    - 監視ループ起動スクリプト（python -m kabusys.run_monitoring）。MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応。
  - ExecutionEngine（Signal Queue ベースの発注エンジン）を実装:
    - シグナル処理ウィンドウ（8:50–9:10）と WebSocket push ドレインループ（9:10–15:30）をサポート。
    - kill.flag の検出、PID ファイル書き込み、プロセス優先度設定、セッション終了処理を実装。
    - push イベントをキューに取り込み、同期（sync_order）および Gate 3（ドローダウン監視）を実行。
    - position_entries の DuckDB への書き込み（次営業日計算と併用）。
  - Order 関連コンポーネント:
    - OrderRecord: 明確な状態遷移を表現する状態機械（OrderCreated→OrderSent→OrderAccepted→Partial/ Filled→Closed など）、遷移検証とメタデータ更新を実装。
    - OrderManager: DB（OrderRepository）と OrderRecord を結合した外向き API を実装。create/send/sync/cancel の処理フロー（2相永続化を含む）とエラー種別（DuplicateOrderError, OrderSentPendingError 等）を実装。
    - 送信の堅牢性: OrderSent の前永続化 → broker へ送信 → broker_order_id の先コミット → OrderAccepted へ遷移、というクラッシュ耐性のあるフローを採用。
    - sync_order による broker 側状態照合と部分約定の進捗更新。
    - cancel_order はキャンセル不可能状態を適切に拒否。
  - ブローカークライアント実装（KabuStationClient）:
    - httpx による同期 REST クライアント、トークンの遅延取得・自動再取得、401 の際のリトライ、429 レート制限、サーバーエラーの扱いを実装。
    - WebSocket push（stream_push）インターフェイスを想定し、存在する実装であれば ExecutionEngine が利用可能。
  - 監視用 DB 初期化・監視イベント記録の仕組みを追加（monitoring_db 経由で発注イベント等を記録）。
  - Paper trading サポート:
    - KABUSYS_ENV=paper_trading 時は専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - PAPER_FILL_MODE によるモックブローカの振る舞い設定（instant/partial/never/reject）。
  - リスク管理フロー（RiskManager）との統合:
    - Gate 1（シグナルレベル）/ Gate 2（エグゼキューションレベル、レート制限・サーキットブレーカー）/ Gate 3（ポートフォリオメトリクス）を呼び分け、Gate 3 NG 時には kill_switch を発動。
  - その他ユーティリティ:
    - process_priority の設定、logging_setup の呼び出し、stop フラグ / kill_switch の仕組み。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 機密情報の扱い:
  - config_setup の表示ではシークレット項目をマスクして表示。
  - .env はコミットしないことを README テンプレートに明記（.env を生成するヘッダを出力）。
- 実行前設定検証で本番環境（KABUSYS_ENV=live）に関する注意喚起を強化（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START=1 の危険性を警告）。

Notes / Remarks
- YAML の内容検証は PyYAML に依存するため、未インストール時はファイル存在チェックのみ行い、パース検証をスキップします（validate_config の挙動）。
- 設計上、OrderSent 状態が残るケース（送信直後のクラッシュなど）は Reconciliation により回復可能なよう 2 相永続化と broker_order_id の先コミットを行っています。
- ExecutionEngine はテスト容易性のために内部メソッド（_process_signals, _drain_push_queue 等）を直接呼べる設計になっています。

--------------------------------------------------------------------------------
メンテナンス: 次回リリースで想定される改善案（例）
- 非同期（async）版 KabuStationClient（httpx.AsyncClient）対応
- Unit tests / integration tests の追加と CI ワークフロー整備
- 設定ファイル（config/*.yaml）に対するスキーマ検証（JSON Schema 等）の導入
- より詳細な監視メトリクスの追加（Prometheus 等へのエクスポート）
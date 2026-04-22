CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
詳細な履歴はコードベース（src/ 以下）から推測して作成しています。

Unreleased
----------

- （無し）

0.1.0 - 2026-04-22
------------------

Added
- 初回リリース。
- 環境変数・設定読み込み機能を追加（kabusys.config）。
  - .env / .env.local の自動読み込み（OS 環境変数を保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションをサポート。
  - .env のパースは以下に対応：`export KEY=val`、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなど。無効行はスキップ。
  - 必須環境変数取得用の _require() と Settings クラスによるプロパティベースの設定アクセスを提供。
  - 各種設定プロパティ：API トークン、kabu API 設定、LINE トークン、DB パス、paper_trading 用の分離 DB、PID/KILL フラグ、しきい値など。
  - PAPER_FILL_MODE 等の値検証ロジックを実装。

- 設定ウィザード CLI（python -m kabusys.config_setup）を追加。
  - 対話式で .env を作成・更新可能。
  - シークレットは画面表示時にマスク。
  - デフォルト値・選択肢表示・既存 .env の読み込み・確認プロンプトを実装。
  - 書き出し時に .env のテンプレートヘッダを付加。

- 設定検証 CLI（python -m kabusys.validate_config）を追加。
  - 必須/任意環境変数の有無チェック。
  - KABUSYS_ENV、LOG_LEVEL 等の値検証（有効値チェックと live 環境への注意喚起）。
  - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（存在しない場合は警告）。
  - config/*.yaml の存在確認と（PyYAML があれば）パース検証。PyYAML 未導入時は YAML 検証をスキップする旨を警告。
  - --strict オプションで警告を FAIL として exit(1)。
  - 出力に INFO/WARNING/ERROR を区別して表示。

- 実行用スクリプトを追加。
  - run_execution: ExecutionEngine 起動スクリプト（本番 / ペーパートレード DB を分離）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔上書き可）。
  - どちらもプロセス優先度を high に設定するユーティリティを呼び出す処理を追加。
  - stop_requested.flag / PID 管理および起動時の kill.flag 検査を実装。

- Execution サブシステムのコア実装を追加。
  - ExecutionEngine（シグナル処理 + push ドレインループ）。
    - signal_send_start/End、market_close を利用したセッション制御。
    - kill_switch 起動時の全 active 注文キャンセル処理。
    - WebSocket（push）受信を別スレッドで処理し、同期対象注文の照合と Gate 3（ドローダウン）チェックを実行。
    - 発注の latency を監視 DB にログ化するフックを追加。
    - PID ファイルの書き出し／削除を実装。
  - OrderRecord：状態遷移を表す状態機械を実装（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）。
    - 許容遷移テーブルと transition_to() による検証。InvalidStateTransitionError を定義。
  - OrderManager：外向き API（create_order, send_order, sync_order, cancel_order）。
    - DuplicateOrderError による重複シグナル検知。
    - send_order における "2 相永続化" パターン：
      1) OrderSent へ遷移してコミット（broker 呼び出し前）
      2) broker からの order_id を DB に保存（state は Sent のまま）
      3) 状態を OrderAccepted に遷移してコミット
    - OrderRejectedError / OrderSentPendingError のハンドリング（pending の場合は broker_order_id を保存して OrderSent のまま残す）。
    - sync_order による broker 側状態照合と部分約定情報（filled_qty / avg_fill_price）の更新。OrderSent → Filled/PartialFill へは OrderAccepted を経由して遷移させる安全化処理。
    - cancel_order は終端状態チェックを行い、必要なら broker API 呼び出しで取消しを実施。

- ブローカークライアント実装（KabuStationClient）。
  - httpx 同期クライアントを利用した REST 実装。
  - トークン取得の遅延初期化（_get_token）と 401 時のトークン再取得・リトライ処理を実装。
  - HTTP ステータスに応じた例外処理（401/429/5xx 等）。
  - kabu station の状態コードを内部ステータス（open/partial/filled/cancelled/rejected）にマッピング。

- 監視関連
  - monitoring_db の初期化処理（init_monitoring_db）呼び出しを run_* スクリプトや起動フローに組み込み。
  - ExecutionEngine から監視 DB へ発注イベント（Sent 等）をロギングする処理を追加（障害時は警告を出して発注フローは継続）。

- リスク管理・リコンシリエーション
  - RiskManager と Reconciler の呼び出し点を ExecutionEngine に統合（Gate 1/2/3 のチェック、Reconciliation の実行）。

Changed
- パッケージの初期バージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 実行系と監視系で DB パスの扱いを整理（paper_trading 時の専用 SQLite、monitoring は常に本番 sqlite_path を使用する旨を明示）。

Fixed
- 発注フローのクラッシュ安全性を向上（OrderSent 前後や broker_order_id 永続化の戦略により、リコンシリエーションで整合性を回復可能に設計）。

Security
- .env の生成時にシークレット値を画面表示でマスク。
- 設定検証ツールで本番環境（KABUSYS_ENV=live）の注意喚起や LINE 通知設定の未設定警告を追加。

Notes / Known limitations
- YAML の内容検証は PyYAML に依存。未インストールの場合はファイル存在チェックのみ実行し、パースはスキップする。
- KabuStationClient は同期 httpx.Client ベース。将来的な非同期対応は httpx.AsyncClient への置き換えを想定。
- 一部のエラー（例: BrokerAPIError の詳細な型分解など）は上位で再スローまたはログ処理される設計のため、必要に応じてハンドリングを追加すること。

Acknowledgements
- この CHANGELOG はソースコード（src/ 以下）からの推測に基づいて作成しています。実際のリリースノート作成時はコミットログ・プルリクエスト等の履歴を参照してください。
CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  

0.1.0 - 2026-04-23
------------------

Added
- 初回リリースを公開しました。
- 環境・設定管理
  - Settings クラスを導入し、環境変数からアプリケーション設定を取得する API を提供 (src/kabusys/config.py)。
    - J-Quants / kabuステーション / LINE / DB /監視/システム関連のプロパティを実装。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
    - PAPER_FILL_MODE の妥当性チェックを実装（"instant" / "partial" / "never" / "reject" を許容）。
    - paper_trading 用の別 SQLite パス（PAPER_TRADING_SQLITE_PATH）サポート。
  - .env 自動読み込み機構を追加（プロジェクトルートの .git または pyproject.toml を探索し、.env -> .env.local の順で読み込み）。OS 環境変数は保護され、.env.local は上書きモードで読み込まれます (src/kabusys/config.py)。
  - .env パースは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント処理に対応。

- 対話式設定ウィザード
  - .env の初期作成・更新を行う CLI を追加 (src/kabusys/config_setup.py)。
    - 実行環境や必須トークンの入力補助、既存 .env の読み込み・マスク表示、ファイル出力（テンプレートヘッダ付き）を実装。
    - デフォルト値・選択肢・秘匿項目をサポート。

- 設定検証 CLI
  - .env および config/*.yaml の起動前チェックを行う validate_config CLI を追加 (src/kabusys/validate_config.py)。
    - 必須環境変数の存在チェックと placeholder 値検出。
    - KABUSYS_ENV / LOG_LEVEL / DB パスの検査、必要に応じて警告。
    - config/*.yaml の存在確認と PyYAML があればパース検証（PyYAML 未インストール時はスキップ）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict オプションで警告を FAIL（exit code 1）扱いにできる。

- 実行・監視エントリポイント
  - ExecutionEngine 起動スクリプトを追加 (src/kabusys/run_execution.py)。
    - Paper trading 時は専用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出、バックグラウンドスレッド制御を実装。
  - SystemMonitor 用ポーリングループ起動スクリプトを追加 (src/kabusys/run_monitoring.py)。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する旨を明記。

- ExecutionEngine / 発注フロー
  - ExecutionEngine を実装 (src/kabusys/execution/execution_engine.py)。
    - シグナル処理（8:50–9:10）と WebSocket push ドレインループ（9:10–15:30）を実装。
    - Gate 1 (signal-level)、Gate 2 (execution-level / rate-limit / circuit breaker)、Gate 3 (ドローダウン監視) のリスクチェックを統合。
    - size_multiplier の適用や発注ごとの position_entries 更新処理（DuckDB を利用）を実装。
    - WebSocket push を受けて同期処理を行うワーカーを実装（broker が stream_push を提供する場合）。
    - kill_switch による全 active 注文キャンセルとループ停止の仕組みを実装。PID ファイル/kill.flag の扱いを実装。

- 注文状態機構
  - OrderRecord（純粋な状態機械データモデル）を追加 (src/kabusys/execution/order_record.py)。
    - 明示的な OrderState 列挙型と許可遷移テーブルを定義。
    - 不正遷移時に InvalidStateTransitionError を送出。
  - OrderManager を実装し、OrderRecord と OrderRepository を組み合わせて外向き API を提供 (src/kabusys/execution/order_manager.py)。
    - create_order: signal_id の重複検出（DB の部分ユニークインデックスも考慮）と DuplicateOrderError。
    - send_order: 2 相永続化パターンを採用 (OrderSent を先に永続化→broker 呼び出し→broker_order_id 保存→OrderAccepted 更新)。OrderRejectedError / OrderSentPendingError の扱いを実装し、クラッシュ時の再同期を想定。
    - sync_order: broker の get_order_status との照合ロジック（同一状態でも部分約定の進行を反映）。
    - cancel_order: 終端状態のキャンセル不可チェックと broker cancel 呼び出し。
    - キャンセル不可能な内部状態セット（Filled を含む）を定義。

- ブローカークライアント（kabu）
  - KabuStationClient を実装 (src/kabusys/execution/kabu_client.py)。
    - httpx の同期クライアントを使用した REST 実装。
    - トークン取得の遅延初期化と 401 時のトークン再取得・リトライ処理を実装。
    - HTTP ステータスに基づくエラー分類（401 / 429 / 5xx 等）を実装。
    - 注文状態コード → 内部ステータスへのマッピングを定義。
    - 将来の async 化を踏まえた設計コメントを含む（httpx.AsyncClient での置換で対応可能）。

- 監視関連
  - monitoring_db 初期化 / 使用のためのユーティリティを利用して、Engine と Monitoring スクリプトから監視 DB を初期化する実装を追加（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。
  - 発注イベントの監視 DB へのログ書き込みポイントを ExecutionEngine に追加（監視 DB が与えられている場合）。

Changed
- パッケージメタ
  - __version__ を 0.1.0 に設定 (src/kabusys/__init__.py)。

Fixed
- （初版リリースのため該当なし）

Deprecated
- （初版リリースのため該当なし）

Removed
- （初版リリースのため該当なし）

Security
- （初版リリースのため該当なし）

注記・補足
- 設定ファイル（config/*.yaml）の生成スクリプトは README に記載の通り python scripts/generate_config.py で補助される想定です（validate_config のメッセージ参照）。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup にも同旨のヘッダコメントを追加）。
- 一部の処理は外部ライブラリ（httpx, websocket, PyYAML, duckdb 等）に依存します。実行環境に応じてインストールしてください。
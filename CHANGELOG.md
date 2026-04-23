CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに従って記載しています。

フォーマット:
- 変更はセクション (Added, Changed, Fixed, …) に分類しています。
- バージョンはパッケージの __version__ に合わせて記載しています。

[Unreleased]
-----------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-23
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージバージョン: 0.1.0
- 設定管理
  - src/kabusys/config.py
    - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 対応。
    - _parse_env_line により .env のコメント、クォート、export 形式に対応して堅牢にパース。
    - Settings クラスを導入し、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等のプロパティ経由で設定を取得。
    - PAPER_FILL_MODE の入力検証（有効値: instant, partial, never, reject）や各種ファイルパス（DUCKDB_PATH, SQLITE_PATH 等）および監視閾値を提供。
- 設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の作成/更新を支援。
    - CLI からキー毎に説明・デフォルト・選択肢・シークレット入力をサポート。
    - .env の読み書きロジック（既存値読み込み、テンプレート出力）を実装。
    - 実行例: python -m kabusys.config_setup
- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env と config/*.yaml の起動前検証ツールを実装。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の値検証、DB パスの親ディレクトリ存在確認、YAML パーサ（PyYAML）の有無判定、config ファイルのパース検証を行う。
    - --strict モードで警告を FAIL として扱う。
    - 実行例: python -m kabusys.validate_config
- 実行スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプト。プロセス優先度設定、DB 接続（paper_trading と本番の DB 分離）、PID/停止フラグ管理を実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応、停止フラグ検知、監視用 DB 初期化。
- Execution エンジン核
  - src/kabusys/execution/execution_engine.py
    - Signal Queue Pull 型発注エンジンを実装。
    - シグナル処理ウィンドウ（デフォルト 8:50-9:10）と push ドレインループ（9:10-15:30）を実装。
    - kill.flag による Kill Switch、PID ファイル管理、起動時のリコンシリエーション呼び出し、WebSocket push の受信→処理（_push_queue）、Gate1/2/3 によるリスクチェックフローを含む。
    - 発注成功時に position_entries へ記録して最低保有日数や再エントリー制限と整合性を保つ仕組みを実装。
    - 発注処理中の例外ハンドリング（OrderSentPendingError 処理、API 成功/失敗の記録）や監視DBへの通知を行う。
- 注文状態管理
  - src/kabusys/execution/order_record.py
    - OrderState 列挙と許可された状態遷移（_ALLOWED_TRANSITIONS）を定義。
    - OrderRecord データモデル（DB 操作を行わない純粋ロジック）と安全な状態遷移 transition_to を実装。InvalidStateTransitionError を導入。
  - src/kabusys/execution/order_manager.py
    - OrderRecord と OrderRepository を組み合わせた上位 API を実装。
    - create_order: signal_id ベースの重複検出（DuplicateOrderError）と UUID ベース client_order_id を割当てて永続化。DB UNIQUE 制約違反から DuplicateOrderError へ変換する処理あり。
    - send_order: クラッシュ安全性を考慮した 2 段階永続化（OrderSent を先にコミット → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted へ遷移）および OrderRejectedError / OrderSentPendingError の扱い。
    - sync_order: broker 側状態取得によりローカル状態を同期、部分約定の進捗更新を許可。
    - cancel_order: 終端状態のキャンセル不可判定と broker API 呼び出し後の Cancelled への遷移。
- ブローカークライアント（kabuステーション向け）
  - src/kabusys/execution/kabu_client.py
    - KabuStationClient 実装（同期 httpx クライアント使用）。
    - トークン取得・遅延取得・トークン再取得（401 リトライ）を内部で管理。
    - レスポンス JSON パース失敗・タイムアウト・ネットワークエラー・429（RateLimitError）・5xx エラーなどを BrokerAPIError 系で扱う基盤を実装。
    - WebSocket push 受信用の stream_push（存在する場合）を使った設計を想定（push 用ハンドラを ExecutionEngine に渡す構成に適合）。
- 監視関連
  - src/kabusys/monitoring/*（モジュール参照があるが今回は主要コードスナップショットでは細部を省略）
    - 監視 DB 初期化や SystemMonitor の利用を考慮した起動フローを追加。
- ユーティリティ
  - ロギング設定、プロセス優先度設定などのユーティリティ関数呼び出し箇所を実装（起動時に優先度を上げる等の振る舞い）。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Notes / その他
- .env に関する注意: config_setup によって生成される .env は Git にコミットしないようヘッダに明記。
- YAML 検証は PyYAML のインストール有無に依存。未インストール時は警告して検証をスキップする仕様。
- モジュールは可能な限り DB アクセスと純粋ロジックを分離（OrderRecord は DB 非依存）してテストしやすく設計。
- paper_trading 環境では本番とは別の SQLite（paper_trading 用）を使用して DB を完全分離する挙動。

今後の TODO（例）
- broker API の詳細実装（エラーコード/レスポンス構造に応じたマッピング）と追加ユニットテスト。
- monitoring / SystemMonitor の詳細機能とダッシュボード連携。
- 非同期実行（httpx.AsyncClient 等）や高精度な rate limiting 実装の追加検討。

-----------------------------------------------------------------------------
文責: KabuSys 開発チーム（コードベースから自動生成された変更履歴）
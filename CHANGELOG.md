# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

全体バージョン: 0.1.0 — 初回公開（初期実装）

## [0.1.0] - 2026-04-23

### 追加
- 初期アーキテクチャの実装を追加。
  - パッケージ情報:
    - kabusys パッケージのバージョンを 0.1.0 と設定。
- 環境変数 / 設定管理:
  - src/kabusys/config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env / .env.local の読み込み順序（OS環境 > .env.local > .env）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - .env の行パースロジックを実装（export プレフィックス、引用符、エスケープ、コメント処理に対応）。
    - Settings クラスを実装（各種環境変数の取得ラッパーとバリデーション）。
    - Paper Trading 用の分離された SQLite パス（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE の値チェックを実装。
- 対話式設定ウィザード CLI:
  - src/kabusys/config_setup.py
    - .env を対話的に作成/更新するウィザードを実装（項目定義、既存値取り込み、シークレットのマスク表示、保存）。
    - デフォルト値や選択肢、説明を用意し、保存時に .env ファイルをフォーマットして書き込み。
    - .env の既存読み込み / 出力ロジックを実装。
- 起動前設定検証 CLI:
  - src/kabusys/validate_config.py
    - 必須環境変数の存在チェック、プレースホルダ値検出、KABUSYS_ENV / LOG_LEVEL の妥当性検証。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック（自動作成の可能性を警告）。
    - config/*.yaml の存在確認と、PyYAML があればパース検証（PyYAML 未インストール時はスキップして警告表示）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険設定を警告）。
    - --strict オプションで警告を失敗扱いにする実行モードを提供。
- 実行用エントリスクリプト:
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプトを実装。プロセス優先度設定、DB 接続（paper_trading は専用 DB を使用）、停止フラグ/ PID 管理を実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装（MONITOR_POLL_INTERVAL によるポーリング間隔上書き、監視 DB は常に本番 sqlite_path を使用）。
- Execution / 発注周りのコア実装:
  - src/kabusys/execution/execution_engine.py
    - Signal Queue ベースの発注エンジンを実装（シグナル処理ウィンドウ、push ドレインループ、WebSocket push の受信処理を含む）。
    - Gate1/2/3 のリスクゲートを統合（シグナル検査、実行レート制限、ドローダウン監視）。
    - kill_switch の実装（全 active 注文のキャンセルと停止イベント設定）。
    - PID ファイル書き込み、kill.flag の扱い（KILL_FLAG_CLEAR_ON_START による挙動）を実装。
    - 発注後の position_entries への記録ロジック（買いと売りで挙動を分離、pending 考慮）。
  - src/kabusys/execution/order_manager.py
    - OrderRecord（状態遷移モデル）と OrderRepository を組み合わせた外向け API を実装。
    - create_order（重複 signal_id の検出）、send_order（2相永続化のフロー記述）、sync_order（broker 照合）、cancel_order（キャンセル可否チェック）を実装。
    - OrderSentPendingError の扱い、OrderRejectedError の扱いを区別して処理。
    - DuplicateOrderError を導入。
  - src/kabusys/execution/order_record.py
    - 注文状態の列挙（OrderState）と状態遷移検証ロジックを実装。InvalidStateTransitionError を定義。
    - データクラス OrderRecord を実装（更新時に updated_at を自動更新、オプションフィールドの更新をサポート）。
  - src/kabusys/execution/kabu_client.py
    - kabuステーション向け同期 REST クライアント実装（httpx を使用）。
    - トークン取得・再取得ロジック、認証付きリクエストの自動リトライ（401 対応）、HTTP ステータスに基づくエラー変換（429 を RateLimitError 等へ）。
    - WebSocket push（websocket 等）や stream_push を利用した push 処理の想定（ExecutionEngine の websocket ワーカと連携可能）。
- ブローカー抽象・API 型:
  - 発注/ステータス照会/キャンセル/ポジションなどを表す BrokerAPIProtocol（詳細はモジュール内で定義）。
  - OrderRequest / OrderResponse / OrderStatus / Position / RateLimitError 等の型を利用する設計。
- 監視関連:
  - src/kabusys/monitoring/*（起動スクリプトから利用）
    - monitoring DB 初期化用の init_monitoring_db の呼び出しと、監視イベント記録（発注イベントのログ）を ExecutionEngine / OrderManager と連携。
- 実行環境周りのユーティリティ:
  - プロセス優先度設定ユーティリティ（set_process_priority）およびログセットアップ（setup_logging）を利用するようにスクリプトを構成。

### 変更
- （初期リリースのため該当なし）

### 修正
- （初期リリースのため該当なし）

### 注意点 / 既知の仕様
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後に .env を自動読み込みしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config/*.yaml の中身検証は PyYAML がインストールされている場合のみ行われます。未インストール時は存在確認のみ行い警告を出します。
- ExecutionEngine は WebSocket の push を受け取る broker の stream_push メソッドの有無を動的に判定し、未実装の場合は WebSocket スレッドをスキップします。
- send_order の永続化フローはクラッシュ耐性を考慮して設計されていますが、外部の Broker 実装のエラー種別に依存します（OrderSentPendingError / OrderRejectedError 等の利用を想定）。
- PAPER_TRADING 模式では本番の監視 DB を分離して使用するよう実装されています（paper_trading 用 SQLite を使用）。

### セキュリティ
- .env を絶対に Git にコミットしない旨を config_setup の生成ヘッダに明記。

（この CHANGELOG はコードベースからの推測に基づく初期リリースの要約です。実際の改修履歴やコミットメッセージが存在する場合は適宜差し替えてください。）
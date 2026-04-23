CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに従っています。  

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-23
-------------------

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。

### 追加 (Added)
- パッケージ全体の初期モジュールと CLI スクリプトを追加
  - src/kabusys/__init__.py
    - パッケージ名とバージョン（0.1.0）を定義。
- 環境設定・読み込み機能
  - src/kabusys/config.py
    - .env ファイル（.env / .env.local）および OS 環境変数からの設定自動読み込み。
    - .env のパースロジック（コメント、export プレフィックス、クォート／エスケープ処理）を実装。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
    - Settings クラスにアプリケーション設定プロパティを提供（トークン・API パスワード・DB パス・各種閾値・環境判定など）。
    - 設定値検証（有効な KABUSYS_ENV / LOG_LEVEL や PAPER_FILL_MODE の検証）を行い、無効なら ValueError を送出。
- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を作成／更新する機能を実装。
    - ウィザード定義（各設定項目、ラベル、説明、選択肢、デフォルト、シークレットマスクなど）。
    - .env 読み書きのロジックとテンプレート生成（.env を絶対にコミットしない旨のコメントを含む）。
- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env および config/*.yaml の事前検証ツールを実装。
    - 必須／任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL/DB パスの検査、YAML パース（PyYAML がある場合のみ）等を実行。
    - --strict フラグで警告も失敗扱いにするオプションを提供。
    - ローカル開発でありがちなプレースホルダ値（*_here / your_value）を検出して警告。
- 実行・監視用起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するためのエントリポイントを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - プロセス優先度設定・PID ファイル管理・停止フラグ検知（data/stop_requested.flag）を含む起動フロー。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
- Execution コンポーネント（発注エンジン、Order 管理）
  - src/kabusys/execution/execution_engine.py
    - Signal Queue Pull 型の発注エンジンを実装（シグナル処理 → push ドレインのセッション制御）。
    - シグナル処理 (8:50-9:10) と push ドレイン (9:10-15:30) のタイムウィンドウ管理。
    - Gate 検査（Gate1: シグナル、Gate2: 実行レベル、Gate3: ドローダウン）と kill_switch 発動ロジック。
    - WebSocket push を別スレッドで受け取り _push_queue に投入する仕組みを実装。
    - PID ファイルおよび kill.flag の扱い（KILL_FLAG_CLEAR_ON_START により起動時の自動クリア可）。
  - src/kabusys/execution/order_record.py
    - OrderState 列挙と許可された状態遷移を定義する OrderRecord（純粋ドメインモデル）を追加。
    - 不正遷移時に InvalidStateTransitionError を送出する遷移検証ロジックを実装。updated_at 自動更新。
  - src/kabusys/execution/order_manager.py
    - OrderRecord と OrderRepository を組み合わせた外向 API を実装。
    - create_order: signal_id 毎の重複検出（DuplicateOrderError）、client_order_id の uuid4 生成、DB 永続化。
    - send_order: 2相永続化戦略（OrderSent を先に永続化 → ブローカー呼び出し → broker_order_id を保存 → OrderAccepted へ遷移）でクラッシュ安全性を考慮。
    - OrderRejectedError / OrderSentPendingError 等のハンドリングを実装。
    - sync_order: broker 側状態照会から状態同期（部分約定の更新最適化含む）。
    - cancel_order: 終端状態チェックと broker cancel 呼び出し。
- ブローカー API 客体（kabu station クライアント）
  - src/kabusys/execution/kabu_client.py
    - kabu station REST API クライアントを実装（同期 httpx ベース）。
    - トークン取得・自動再取得、401 リトライ、429 の RateLimitError 判定、タイムアウト/ネットワークエラーの変換を実装。
    - WebSocket (push) の受信は websocket（ライブラリ）に依存する想定（stream_push を broker 実装に要求）。
- 監視 DB 初期化ユーティリティや SystemMonitor 連携（起動時に init_monitoring_db を呼ぶフローを採用）
- その他ユーティリティの利用
  - プロセス優先度設定（set_process_priority）、ロギングセットアップ（setup_logging）を起動時に呼び出す。

### 変更 (Changed)
- 該当なし（初回リリースのためなし）

### 修正 (Fixed)
- 該当なし（初回リリースのためなし）

### 削除 (Removed)
- 該当なし

### 非推奨 (Deprecated)
- 該当なし

### セキュリティ (Security)
- .env の内容が機密情報を含むため、config_setup に .env を Git にコミットしない旨の注意を明記。
- Settings._require() は必須環境変数未設定時に ValueError を上げ、起動時の誤設定を早期検出する。

Notes / 備考
- YAML の検証は PyYAML（yamlパッケージ）に依存。未インストール時は validate_config が YAML 内容検証をスキップして警告を出します。
- 実運用では KABUSYS_ENV=live 時の設定（LINE 通知や KILL_FLAG_CLEAR_ON_START の値など）に注意してください。validate_config と run_* スクリプトで保護・警告を行います。
- ExecutionEngine の動作は多数の外部コンポーネント（BrokerClient, Reconciler, RiskManager, OrderRepository, DuckDB/SQLite）に依存します。各コンポーネントのモック化により単体テストが可能な設計になっています。

もしリリースノートに追記したい具体的な変更点（たとえばバグ修正や設計上の注意点、外部互換性に関する詳細）があれば教えてください。
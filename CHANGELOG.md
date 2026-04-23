# Changelog

すべての重要な変更点を Keep a Changelog の形式で記載します。コードベースから推測して作成しています。

フォーマット:
- [Unreleased] は今後の変更用に残しますが、以下は初期リリース v0.1.0 に相当する機能追加・実装を示します。

## [Unreleased]
- なし

## [0.1.0] - 初期リリース
リリース日: 未指定

### 追加 (Added)
- パッケージ基盤
  - パッケージ情報にバージョンを追加: `kabusys.__version__ = "0.1.0"`。

- 環境設定・管理
  - 環境変数読み込みと管理機能を実装（src/kabusys/config.py）。
    - プロジェクトルート検出: `.git` または `pyproject.toml` を辿って自動判定する `_find_project_root()` 実装。
    - .env ファイルのパース機能を実装（引用符・エスケープ・コメント・export 形式に対応）。
    - .env 自動読み込み機構を追加（読み込み優先順位: OS 環境変数 > .env.local > .env）。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で抑止可能。
    - .env 読込時の上書き制御（override / protected）に対応。
    - 設定取得ヘルパー `Settings` クラスを実装。J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、ログレベル、各種閾値、kill flag の設定等をプロパティで安全に取得できる。
    - 必須環境変数未設定時には例外を投げる `_require()` を提供。

- .env 設定ウィザード CLI
  - 対話式ウィザードで .env を作成・更新するスクリプトを追加（src/kabusys/config_setup.py）。
    - 設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。
    - 既存 .env 読み込み／既存値の再利用、シークレットマスク表示、選択肢チェック、保存確認をサポート。
    - .env を整形して書き出す `_write_env()` を実装。

- 設定検証 CLI
  - 起動前に .env と config/*.yaml の不備をチェックする CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック（development/paper_trading/live）、LOG_LEVEL チェック、DB パスの存在確認（親ディレクトリの存在警告）。
    - config/*.yaml の有無確認と（PyYAML がインストールされていれば）パース検証。
    - 本番環境向け追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の危険値チェック）。
    - 出力フォーマット: INFO/WARNING/ERROR、`--strict` オプションにより警告も失敗（exit 1）として扱う。

- 実行スクリプト
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - paper_trading 環境向けに専用 SQLite（paper_trading.db）を分離して使用。
    - DuckDB / SQLite の接続確立、PID ファイル管理、停止フラグ検出、スレッドでのエンジン実行をサポート。
    - プロセス優先度設定ユーティリティ呼び出し（High）およびログ初期化を行う。
  - Monitoring ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を調整可能（デフォルト 60 秒、無効値時はデフォルトフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。

- 注文・実行エンジンまわり
  - 純粋ビジネスロジックの OrderRecord（状態遷移モデル）を追加（src/kabusys/execution/order_record.py）。
    - OrderState Enum、許可遷移テーブル `_ALLOWED_TRANSITIONS`、`transition_to()` による遷移検証。無効遷移時は `InvalidStateTransitionError` を送出。
  - OrderManager（発注ワークフローの外向け API）を実装（src/kabusys/execution/order_manager.py）。
    - 注文作成（client_order_id は uuid4）、重複検出（同一 signal_id の active 注文が存在する場合 `DuplicateOrderError`）。
    - send_order のクラッシュ安全設計: OrderSent を先に DB に永続化 → ブローカー呼び出し → broker_order_id を保存 → OrderAccepted に遷移するという 2 相永続化を採用。OrderRejected / OrderSentPending のハンドリングを実装。
    - sync_order による外部ブローカー状態同期（部分約定の更新や状態遷移の補正）。
    - cancel_order によるキャンセルロジック（キャンセル不可能な状態の判定、broker 呼び出し、状態遷移）。
  - ExecutionEngine（Signal Queue Pull 型発注エンジン）を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）を実装。
    - Gate 1（シグナルレベル）、Gate 2（エグゼキューションレベル、レート制限・サーキットブレーカー）、Gate 3（ポートフォリオ監視、ドローダウン判定）を導入し、失敗時に kill switch を起動する設計。
    - size_multiplier の適用（買い注文のみ、100株単位で丸め）や発注レイテンシ計測、監視 DB へのトレードイベントログ出力をサポート。
    - WebSocket (push) を受けて broker_order_id を起点に注文同期（sync_order）を行うワーカーを実装。stream_push が未実装の broker はスキップ。
    - kill_switch() により全 active 注文をキャンセルし、ループ停止する仕組み。
    - PID ファイル管理、起動時のリコンシリエーション呼び出しフックをサポート。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期 REST クライアント。トークン取得（遅延初期化）、401 時のトークン再取得とリトライ、429（RateLimit）や >=500 のサーバエラーの扱いを実装。
    - JSON パースエラーやネットワーク例外を BrokerAPIError に変換して扱う設計。
    - WebSocket push 用に websocket クライアント（stream_push 想定）との統合を想定。

- 監視・DB 初期化
  - 監視 DB の初期化呼び出しを run_monitoring/run_execution に追加し、監視テーブルが存在することを保証（init_monitoring_db を使用）。

### 変更 (Changed)
- 設定読み込みの振る舞い（実装上の設計）
  - .env のパースはより寛容に（シングル／ダブルクォート、エスケープ、inline コメント取り扱いなど）実装。
  - .env 自動ロードは OS 環境変数を保護するため既存の OS 環境変数キーを protected として扱う。

- DB パスのデフォルト
  - DuckDB のデフォルトパス: `data/kabusys.duckdb`、監視用 SQLite: `data/monitoring.db`、paper trading 用 SQLite: `data/paper_trading.db`。

- 本番環境（KABUSYS_ENV=live）に対する安全ガード
  - validate_config と Settings の両方で KABUSYS_ENV 値の検証を行い、不正値はエラー（Settings では例外を投げる）として扱う。
  - live 時に LINE 設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告。

### 修正 (Fixed)
- 起動・停止制御
  - 起動時に既存の kill.flag を検出し、`KILL_FLAG_CLEAR_ON_START` が 1 の場合はクリアして起動、そうでなければ起動を拒否する挙動を ExecutionEngine に実装（残留フラグによる誤起動防止）。
- モニタリングのポーリング間隔の安全化
  - `MONITOR_POLL_INTERVAL` が 0 以下や数値以外の場合は警告を出してデフォルトにフォールバックするよう run_monitoring に実装。

### ドキュメント / ユーティリティ（明示的な変更）
- コマンドライン用の説明ヘルプ・usage を各 CLI に追加（argparse を使用）。
- validate_config, config_setup の出力メッセージは日本語で説明を出すように実装されている。

### 既知の設計注記（注意点）
- YAML パーサ（PyYAML）が未インストールの場合、config/*.yaml の内容検証はスキップされる（警告のみ）。
- send_order の二相永続化設計により、クラッシュ時に OrderSent 状態のまま残ることがあり、Reconciliation（reconciler）で修復する前提。
- KabuStationClient は同期 httpx.Client を使用しているため、将来的に非同期対応が必要な場合は httpx.AsyncClient へ差し替えが想定される。

---

この CHANGELOG はソースコードからの推測に基づいて作成しています。実際の変更履歴やリリース日などはプロジェクトの運用方針に従って適宜更新してください。
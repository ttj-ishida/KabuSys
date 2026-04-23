# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-23
初回公開リリース。

### Added
- 基本アプリケーション情報
  - パッケージ版情報を定義: `kabusys.__version__ = "0.1.0"`。

- 環境設定と自動ロード
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを追加。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env のパースは引用符、エスケープ、コメント（#）等を考慮した独自実装を提供（`kabusys.config`）。

- Settings/設定管理 API
  - 環境変数に基づく型付き設定アクセスを提供する `Settings` クラスを追加（`settings = Settings()`）。
  - 必須設定取得用の `_require()` 実装で未設定時は例外を投げる。
  - Paper Trading 用 DB パスや fill モード、しきい値（CPU/MEM/DISK）など多くの設定プロパティを提供。
  - `KABUSYS_ENV` / `LOG_LEVEL` の検証（許容値チェック）を実装。

- .env 設定ウィザード
  - 対話式 CLI `kabusys.config_setup` を追加して `.env` の初期作成・更新を支援。
  - J-Quants / kabu API / DB パス / LINE 通知 等の主要項目を質問形式で設定可能。
  - シークレット項目は表示をマスクして取り扱い、既存値の再利用やデフォルト適用に対応。
  - `.env` の書き込み・テンプレート化を行う `_write_env()` を提供。
  - 生成された `.env` は Git にコミットしない旨の注意を出力。

- 設定検証 CLI
  - `kabusys.validate_config` による起動前チェックを追加。
  - 必須環境変数（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）の存在確認、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認を実施。
  - `config/*.yaml` の存在確認および（PyYAML がある場合）パース検証を行う（PyYAML 未インストール時は警告でスキップ）。
  - `--strict` オプションで警告をエラー扱い（exit(1)）にするモードを提供。

- 実行スクリプト
  - `run_execution`：ExecutionEngine を起動するエントリポイントを追加。
    - プロセス優先度設定（High）およびログセットアップを行う。
    - paper_trading モード時は paper 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し本番 DB と分離。
    - PID ファイルの書き出し、停止フラグ（stop_requested.flag）検知による停止、kill.flag の扱い（`KILL_FLAG_CLEAR_ON_START`）を実装。
  - `run_monitoring`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト60秒、1未満の値はデフォルトにフォールバック）。

- Execution エンジン
  - `ExecutionEngine` を追加（Signal Queue Pull 型）。
    - シグナル処理ウィンドウ（デフォルト 8:50 - 9:10）、push ドレイン（9:10 - 15:30）などセッション管理を実装。
    - WebSocket push を別スレッドで受け取りキューへ投入、ドレイン時に同期処理を行う仕組みを持つ。
    - PID ファイル、kill switch（全 active 注文をキャンセルしてループ停止）を実装。
    - シグナル処理時に Gate1（シグナルレベル） / Gate2（実行レベル） / Gate3（ポートフォリオ指標：ドローダウン等）を順に評価する設計。
    - 発注後は position_entries へ約定予定日を書き込み（買いは記録、売りはクローズ処理）し、監視 DB へトレードイベントをログ可能。

- 注文管理・状態機械
  - `OrderRecord`（状態遷移モデル）を追加。DB には触れない純粋なビジネスロジック。
    - 許容状態遷移テーブル `_ALLOWED_TRANSITIONS` を定義し、不正遷移で `InvalidStateTransitionError` を投げる。
    - `transition_to()` により状態遷移と関連フィールド（broker_order_id, filled_qty, avg_fill_price, error_message）を安全に更新。
  - `OrderManager` を追加（外向き API）。
    - `create_order`：signal_id 重複チェック（DB レベルの部分ユニーク制約の扱いを含む）、client_order_id に UUID を採番して永続化。
    - `send_order`：堅牢な二相的永続化フローを実装（OrderCreated → OrderSent を DB に先に保存、broker 呼び出し、broker_order_id を先に保存、続けて OrderAccepted へ遷移）。OrderSent のまま残るクラッシュケースや OrderSentPending を考慮した設計。
    - `sync_order`：broker 側状態を取得してローカル状態に同期。部分約定の進展はフィールド更新で反映。
    - `cancel_order`：キャンセル不可能な終端状態は拒否し、broker_order_id があれば API を呼んでキャンセルし、Cancelled に遷移。
    - DuplicateOrderError を定義し、同一 signal_id の active 注文重複を明示的に扱う。

- ブローカークライアント（kabu station）
  - `KabuStationClient` を実装（同期 httpx ベース）。
    - トークン取得を内部で遅延初期化・自動再取得（401 時に再試行）。
    - リクエスト共通処理は `_request()` に集約し、タイムアウト・ネットワークエラー・401（再取得）・429（RateLimitError）・5xx（サーバーエラー）等を BrokerAPIError/RateLimitError に変換。
    - REST API ベース URL の設定とタイムアウト設定をサポート。
    - kabu station の注文状態コードを内部状態文字列へマッピング。

- 監視（Monitoring）
  - 監視用 DB 初期化関数 `init_monitoring_db` と SystemMonitor のポーリングループ起動を提供。
  - 監視プロセスは常に本番用 sqlite_path を使用（環境にかかわらず）。

- ユーティリティ
  - ログ設定セットアップ（`setup_logging`）およびプロセス優先度設定ユーティリティ（`set_process_priority`）を使用してプロセス起動時に適用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env は絶対に Git にコミットしない旨を .env テンプレート（config_setup の生成内容）に明記。

### Notes / 重要な運用上のポイント
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。設定されていないと Settings プロパティの呼び出しで例外を投げます。
- 推奨/任意環境変数
  - KABUSYS_ENV: development / paper_trading / live のいずれか
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番環境で未設定だとアラートが届きません）
- 本番起動（KABUSYS_ENV=live）時の注意
  - validate_config の検証で live は警告を出します。LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値（1 は危険）を再確認してください。
- 自動読み込みを抑止するには
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env 自動読み込みを無効化できます（テスト用途など）。
- Monitor 関連
  - MONITOR_POLL_INTERVAL の値が不正な場合は警告を出しデフォルト 60 秒を使用します。
- .env ウィザード
  - 生成した .env の検証は `python -m kabusys.validate_config` を推奨。

---

今後のリリースでは以下の点を予定しています（予定事項）:
- KabuStationClient の WebSocket/ストリーミング関連の強化・エラーハンドリング改善
- Reconciler の詳細な実装と CLI/運用ドキュメント充実
- 単体テスト周りの整備と CI ワークフロー導入

---
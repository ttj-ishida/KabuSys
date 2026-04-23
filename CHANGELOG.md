Keep a Changelog
=================

すべての注目すべき変更点を記録します。これは人間が読める形式であり、リリースノートやデプロイ手順の基礎となります。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------

（なし）

0.1.0 - 2026-04-23
-----------------

初回リリース — KabuSys のコア機能と運用用ユーティリティを実装しました。

Added
- パッケージ初期化
  - パッケージバージョンを __version__ = "0.1.0" として設定。

- 設定管理 (src/kabusys/config.py)
  - 環境変数・.env 管理用 Settings クラスを実装。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env のパースロジックを強化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
  - 必須環境変数取得時に未設定なら ValueError を送出する _require() を提供。
  - 各種プロパティを実装（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE 関連、DUCKDB/SQLite パス、paper trading 用設定、PID/KILL フラグ、各種閾値、環境/ログレベル検証など）。
  - PAPER_FILL_MODE の値検証（"instant" | "partial" | "never" | "reject"）。

- 設定ウィザード CLI (src/kabusys/config_setup.py)
  - 対話式ウィザードで .env の初期作成・更新を支援。
  - 多数の設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。
  - 既存 .env 読み込み・現在値の再利用、シークレットマスク、保存確認、.env テンプレート書き出し機能を実装。
  - 使用例: python -m kabusys.config_setup

- 設定検証 CLI (src/kabusys/validate_config.py)
  - .env と config/*.yaml の起動前チェック用 CLI を実装。
  - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実施。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
  - --strict フラグで警告も FAIL（exit(1)）扱い。
  - 使用例: python -m kabusys.validate_config

- 実行用スクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine の起動ロジックを組み合わせた CLI スクリプトを提供。
    - paper_trading 環境では paper_trading 用 SQLite DB を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出（data/stop_requested.flag）等を実装。
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。

- 実行ロジック (src/kabusys/execution/*)
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - Signal Queue ベースの発注エンジン。
    - EngineConfig による target_date／タイムウィンドウ設定（発注開始/締切/セッション終了時刻）。
    - シグナル処理フロー（size_multiplier の適用、Gate1/Gate2 のリスクチェック、重複注文防止、発注および発注後処理、position_entries 更新、監視 DB へのトレードイベント記録）。
    - push ドレインループ（WebSocket push からの同期）、Gate3（ドローダウン監視）と kill_switch 発動。
    - kill_switch により全 active 注文をキャンセルするロジック、PID ファイルの出力と削除。
    - WebSocket 用の worker（broker が stream_push を持つ場合に起動）。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - OrderRecord（状態遷移モデル）と OrderRepository（SQLite）を組み合わせる外向け API を実装。
    - create_order：signal_id 単位の重複検出（DuplicateOrderError）、uuid4 を client_order_id に採番。
    - send_order：2相永続化を意識した安全な発注（OrderCreated→OrderSent を永続化してから broker 呼び出し、broker_order_id は先に保存、OrderAccepted へ遷移、OrderRejected/OrderSentPending の扱い）。
    - sync_order：broker 側ステータス照合と状態同期（部分約定時の更新含む）。
    - cancel_order：キャンセル不可状態の検査、broker への cancel 呼び出しと状態遷移。
  - OrderRecord（src/kabusys/execution/order_record.py）
    - OrderState enum と許容遷移表を実装。
    - transition_to メソッドで遷移検証とメタデータ更新（broker_order_id / filled_qty / avg_fill_price / error_message）。
    - InvalidStateTransitionError を定義。
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - kabu-station REST API クライアント実装（httpx 同期クライアントを利用）。
    - トークン取得（遅延初期化）、401 時の自動再取得とリトライ、429（RateLimitError）や 5xx のエラー分類、JSON パースエラーの BrokerAPIError 変換。
    - 注文状態コード→内部ステータスマッピングを定義。

- 監視および DB 初期化
  - monitoring_db 初期化ユーティリティを run_monitoring/run_execution スクリプトから呼び出して監視用テーブルの存在を保証。

- ユーティリティ
  - process_priority 設定ユーティリティの呼び出し（優先度を高く設定）。
  - logging_setup を用いたログ出力設定（app_name による識別）。

Changed
- 初回リリースのため、変更履歴はありません（初期実装）。

Fixed
- 初回リリースのため、修正履歴はありません。

Security
- .env は絶対に Git にコミットしない旨を .env テンプレートに明記。
- Settings で OS 環境変数を保護するため protected セットを導入（.env ロード時に OS 環境変数を上書きしない）。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須です。validate_config や Settings._require() は未設定時に警告/例外を出します。
- KABUSYS_ENV: 有効値は development / paper_trading / live。live は本番モードで追加のガードや警告が入ります。
- PAPER_TRADING: paper_trading 環境では paper_sqlite_path（data/paper_trading.db がデフォルト）を使用して本番監視 DB と分離します。
- config/*.yaml: PyYAML がインストールされていない場合はパース検証をスキップします（validate_config が警告を出します）。
- MONITOR_POLL_INTERVAL: 監視スクリプトのポーリング間隔を上書き可能（正の整数、デフォルト 60 秒）。不正な値はデフォルトにフォールバックします。
- KILL_FLAG_CLEAR_ON_START: 本番環境での誤設定は危険（起動時に kill.flag を自動クリアする）ため validate_config で警告します。

Dependencies (実行時想定)
- httpx, websocket, duckdb, sqlite3, PyYAML（任意; 未インストール時は YAML 検証がスキップされる）
- logging, threading, time 等の標準ライブラリ

Breaking Changes
- なし（初回リリース）。

Acknowledgements / TODO
- 一部のモジュール（BrokerAPIProtocol 等）は外部実装に依存するため、実運用時は broker 実装（kabu station client）や環境ごとの設定を整えてください。
- リコンシリエーションやエラーハンドリングについては将来的に追加改善予定（現状でもクラッシュ後の回復を考慮した設計を取り入れています）。

---- 

以上がコードベースから推測して作成した CHANGELOG.md（日本語、Keep a Changelog 準拠）です。追加の変更履歴（コミットログや Issue と紐づけたい詳細情報）があれば追記して正式なリリースノートを作成できます。
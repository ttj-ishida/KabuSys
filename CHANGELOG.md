Keep a Changelog に準拠した CHANGELOG.md（日本語）
すべての注目すべき変更をこのファイルに記載します。  
通常、バージョン番号、日付、カテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）を使います。

未リリース
=========

v0.1.0 - 2026-04-23
-------------------

Added
- 全体
  - 初回リリース。KabuSys 日本株自動売買システムの基礎機能を実装。
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 設定管理 / ツール
  - 環境変数自動ロード
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み（OS 環境変数が優先）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは引用符、エスケープ、コメント（#）に対応。
    - 実装: src/kabusys/config.py。
  - Settings クラス
    - 環境変数をプロパティ経由で取得する Settings（例: settings.jquants_refresh_token、settings.duckdb_path 等）。
    - 値検証を行うプロパティ（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）は不正値で例外を送出。
    - production/paper_trading 用 DB パス分離（paper_sqlite_path）。
    - kill flag / PID ファイル / リソース閾値（CPU/Memory/Disk）などの設定取得を提供。
    - 実装: src/kabusys/config.py。

  - 環境設定ウィザード CLI
    - 対話式で .env を生成・更新するツールを提供。
    - シークレット項目はマスク、選択肢・デフォルト表示、既存 .env の読み込みに対応。
    - .env 保存前に内容確認を行う。
    - 実装: src/kabusys/config_setup.py。
    - 使い方: python -m kabusys.config_setup

  - 設定検証 CLI
    - .env と config/*.yaml の事前検証を行う CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。プレースホルダ値を警告。
    - KABUSYS_ENV / LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在チェック。
    - config/*.yaml の存在確認・YAML パースチェック（PyYAML 未インストールの場合はスキップして警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict を付けると警告も失敗扱いして exit(1)。
    - 実装: src/kabusys/validate_config.py。
    - 使い方: python -m kabusys.validate_config [--strict]

- 実行スクリプト / デーモン
  - Execution エンジン起動スクリプト
    - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - paper_trading 環境では専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - PID ファイル書き出し、stop flag 検出による安全停止対応。
    - 実装: src/kabusys/run_execution.py。

  - Monitoring ポーリングスクリプト
    - run_monitoring: SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）。0 以下の値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
    - 実装: src/kabusys/run_monitoring.py。

- 発注・状態管理（Execution）
  - OrderRecord（状態マシン）
    - 注文状態を列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可遷移テーブルを定義し、不正遷移時に InvalidStateTransitionError を送出。
    - 状態遷移時に broker_order_id / filled_qty / avg_fill_price / error_message の更新を許可。
    - 実装: src/kabusys/execution/order_record.py。

  - OrderManager（外向き API）
    - signal_id ごとの重複注文検出（DuplicateOrderError）。
    - create_order: DB への保存と重複チェック（UUID を client_order_id に採番）。
    - send_order: 2相永続化の発注フローを実装（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）。OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order: broker 側ステータス照合 → 状態同期。部分約定の進行は状態一致でも filled_qty/avg_fill_price を更新。
    - cancel_order: キャンセル不可能な状態は検出して例外。broker_order_id がある場合は API 呼び出し。
    - 実装: src/kabusys/execution/order_manager.py。

  - ExecutionEngine（発注エンジン）
    - Signal Queue Pull 型の発注エンジンを実装。
    - シグナル処理ウィンドウ（デフォルト 08:50–09:10）と push ドレイン（09:10–15:30）を実装。
    - Gate チェック:
      - Gate1: signal レベル検査（RiskManager 経由）
      - Gate2: エグゼキューションレベル（rate limit / circuit breaker、最大リトライ3回）
      - Gate3: ドローダウン監視（push イベントまたは定期評価で kill_switch 発動）
    - kill_switch: 全 active 注文をキャンセルしてエンジン停止。
    - WebSocket push を受けて同期（stream_push を持たない broker の場合はスキップ）。
    - 発注結果は position_entries（DuckDB）に書き込み（BUY は entry、SELL は sell_date 更新。pending の扱いも考慮）。
    - 監視DB（MonitoringDB）へのトレードイベント記録を呼び出し可能。
    - 実装: src/kabusys/execution/execution_engine.py。

  - Broker クライアント（kabu）
    - KabuStationClient を実装（httpx を使用する同期クライアント）。
    - トークン取得を内部で管理し、401 で自動再取得+1回リトライ。
    - HTTP ステータスに応じて BrokerAPIError / RateLimitError / などを発生させる処理を実装。
    - WebSocket push の統合を想定（stream_push / on_message コールバック利用）。
    - 実装: src/kabusys/execution/kabu_client.py（トークン・リトライ・エラー処理の実装あり。レスポンス JSON のパース保護も実装）。
    - kabu ステータスコード → 内部ステータスマップを定義。

- DB / 監視
  - DuckDB と SQLite を併用する設計（DuckDB: 分析・シグナル・position_entries、SQLite: 監視・注文履歴）。
  - init_monitoring_db による監視 DB 初期化（冪等）。
  - 実装参照: run_monitoring、run_execution、および各モジュールでの DuckDB/SQLite 利用。

- ユーティリティ
  - プロセス優先度設定フック（set_process_priority を呼び出す）。
  - ロギングセットアップ（setup_logging を使用）。
  - 実装参照: run_monitoring.py/run_execution.py。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes / Migration
- 初回リリースのためアップグレード手順は不要。ただし初回セットアップ時は以下を推奨:
  - .env を作成する: python -m kabusys.config_setup
  - 設定を検証する: python -m kabusys.validate_config（--strict で警告を失敗扱い）
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD を設定すること。
  - config/*.yaml はプロジェクト配布に含めるか、scripts/generate_config.py で生成してください（validate_config がファイルの存在と YAML パースをチェック）。
  - 本番環境（KABUSYS_ENV=live）では LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID を設定し、KILL_FLAG_CLEAR_ON_START は 0 を推奨。

既知の制約 / TODO
- 一部モジュール（broker_api 等）はファイル群の他の部分に依存（今回はスナップショットの一部を基に推測した実装）。
- KabuStationClient の一部レスポンス処理やエッジケースの詳細は環境依存（kabu station アプリの挙動）であり、実運用前の検証を推奨。
- PyYAML がインストールされていない場合、validate_config の YAML 内容検証はスキップされる（警告）。

---
この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴やリリースノートに合わせて適宜追記・修正してください。
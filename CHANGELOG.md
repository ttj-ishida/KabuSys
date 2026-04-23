# Changelog

すべての注目すべき変更はこのファイルに記録します。
このファイルは Keep a Changelog の形式に準拠しています。
参照: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム KabuSys のコア実装を追加しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加 (src/kabusys/__init__.py, __version__ = 0.1.0)。
- 環境設定 / 設定読み込み
  - Settings クラスを実装（src/kabusys/config.py）。環境変数から各種設定値を取得する統一 API を提供。
  - 自動 .env 読み込み機能を追加。読み込み順序は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能。
  - .env パーサーを実装（export 形式対応、クォート／エスケープ処理、インラインコメント処理）。
  - 必須／任意の環境変数、設定値検証ロジック（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実装。無効値は ValueError を送出する。
- 設定ウィザード CLI
  - 対話式 .env 作成/更新ツールを追加（src/kabusys/config_setup.py）。
  - 入力項目定義、既存 .env 読み込み、秘密項目のマスク表示、保存確認、.env ファイル書き出し機能を備える。
- 設定検証 CLI
  - 起動前に .env と config/*.yaml の設定を検証する CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 値検査、DB パス存在確認、YAML パース検証（PyYAML 必須）を実施。
  - --strict オプションで警告も失敗扱いにするモードを提供。
  - 本番環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
- 実行ランナー
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。ExecutionEngine を使ったセッション起動フローを提供。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能。
  - 両スクリプトともプロセス優先度設定（utils/process_priority）とログセットアップを組み込む。
- 発注／実行関連
  - OrderRecord（状態遷移ロジックを含む純粋モデル）を実装（src/kabusys/execution/order_record.py）。
    - 明確な状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と許可遷移テーブルを導入。
    - 不正遷移時に InvalidStateTransitionError を発生。
  - OrderManager を実装（src/kabusys/execution/order_manager.py）。
    - シグナルからの発注フロー（作成→送信→同期→キャンセル）を担当。
    - DuplicateOrderError による signal_id 重複検知。
    - send_order の 2 相永続化（OrderSent を永続化 → ブローカ呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）によるクラッシュ耐性設計。
    - OrderSentPendingError（発注番号は発行されるが約定しないケース）の扱いを実装。
    - sync_order による broker 側状態同期と部分約定情報（filled_qty/avg_fill_price）の差分更新を実装。
  - ExecutionEngine を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル読み込み、Gate1/Gate2（シグナル/エグゼキューション検査）、ドレインループ、Gate3（ドローダウン監視）等の発注ポリシーを実装。
    - size_multiplier 適用（BUY のみ、100株単位に丸め）、position_entries への約定予定登録（DuckDB 経由）。
    - リスクマネージャ連携（API 成功/失敗の記録、レート制限リトライ、サーキットブレーカ判定を尊重）。
    - push (WebSocket) 処理スレッドの実装と _push_queue による非同期通知処理。
    - kill_switch を実装：全 active 注文のキャンセルとループ停止。
    - PID ファイル書き出し・削除、kill.flag の取り扱い（KILL_FLAG_CLEAR_ON_START を尊重）を実装。
    - paper_trading 環境では paper 用の SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
    - モニタリング DB へ発注イベント（Sent）のログ記録（latency 等）に対応。
  - ブローカークライアント抽象と kabu station 実装
    - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期 REST 呼び出し。トークン取得（遅延初期化）と 401 時の再取得＆1回リトライを実装。
    - レスポンス JSON パースエラー・タイムアウト・ネットワークエラー等を BrokerAPIError や RateLimitError に変換。
    - websocket / push 処理のための流し込みインタフェース（stream_push を想定）に対応。
- DB / 監視
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を使用して起動時にテーブルを保証（監視用 SQLite）。
  - DuckDB 接続（分析用 DB）利用を明示。

### Changed
- （初版のため該当なし）初回リリースでは主に機能追加により構成。

### Fixed / Reliability improvements
- .env パーサーの堅牢化
  - export プレフィックス、クォート中のバックスラッシュエスケープ、クォートなし行のインラインコメント処理などに対応。
  - .env 読み込み時に既存 OS 環境変数を保護するため protected set を導入。`.env.local` は override=True で上書き可能。
- 発注フローのクラッシュ耐性
  - send_order の二段階永続化や OrderSentPendingError の扱いにより、クラッシュ後の Reconciliation で状態回復しやすく設計。
- ExecutionEngine の安全停止
  - kill.flag 検査・KILL_FLAG_CLEAR_ON_START の取り扱い、stop フローでの安全なキャンセル処理を追加。

### Notes / Known limitations
- YAML ファイルの内容検証は PyYAML がインストールされている場合のみ実行されます。未インストール時は警告を出してスキップします。
- KabuStationClient は同期実装（httpx.Client）であり、将来的に async 実装へ移行可能（httpx.AsyncClient）。
- 一部の例外（BrokerAPIError 等）は上位で捕捉せず OrderSent のまま残る設計です（Reconciliation により回復を想定）。

---

今後のリリースではテストカバレッジ、ドキュメント強化、非同期クライアント対応、監視・アラート強化（LINE 統合の自動テスト）などを予定しています。
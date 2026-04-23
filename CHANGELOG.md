# CHANGELOG

すべての重要な変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

今後のバージョンでは Unreleased セクションを使用してください。

## [0.1.0] - 2026-04-23

初回リリース — KabuSys 自動売買フレームワークのコア機能を実装。

### Added
- 全体
  - パッケージ初期バージョンを追加。パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。
- 環境設定 / 設定ロード
  - Settings クラスを追加し、環境変数からアプリケーション設定を取得可能に（src/kabusys/config.py）。
  - .env の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env ファイルパース機能を強化:
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなし行のインラインコメント取り扱い改善（直前に空白がある場合のみコメント扱い）。
- 設定ウィザード
  - 対話式 .env 生成/更新ウィザードを追加（src/kabusys/config_setup.py）。
  - 複数の設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）。
  - 既存 .env 読み込み、シークレット値のマスク表示、確認後ファイル書き込み機能を実装。
- 設定検証 CLI
  - validate_config CLI を追加（src/kabusys/validate_config.py）。
  - 必須/任意環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、データベースパスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース検証（PyYAML があればパースを試行）を行う。
  - --strict オプションを追加（警告を FAIL 扱いにして exit(1)）。
- 実行スクリプト
  - run_execution スクリプトを追加（src/kabusys/run_execution.py）:
    - ExecutionEngine 起動フロー、プロセス優先度設定、高可用停止フラグ（data/stop_requested.flag）対応。
    - paper_trading 環境では paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
  - run_monitoring スクリプトを追加（src/kabusys/run_monitoring.py）:
    - SystemMonitor のポーリングループ。MONITOR_POLL_INTERVAL により間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用。
- Execution / 発注関連
  - ExecutionEngine 実装（src/kabusys/execution/execution_engine.py）:
    - シグナル読み込み（DuckDB）→ Gate1/2（リスクチェック、レート制限）→ 発注 → push drain（Gate3）までのセッション制御。
    - WebSocket push を別スレッドで受け取り同期処理する仕組み（_push_queue）。
    - kill_switch 機構（全 active 注文キャンセル）を実装。PID ファイル管理、kill.flag の起動時取り扱い（KILL_FLAG_CLEAR_ON_START オプション対応）。
  - OrderRecord と状態遷移ロジックを追加（src/kabusys/execution/order_record.py）:
    - OrderState 列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可遷移テーブルと transition_to メソッド（不正遷移で InvalidStateTransitionError を送出）。
  - OrderManager を追加（src/kabusys/execution/order_manager.py）:
    - create_order, send_order, sync_order, cancel_order の外向き API。
    - create_order で同一 signal_id の active 注文重複検出（DuplicateOrderError）。
    - send_order はクラッシュ安全性を考慮した「OrderSent を先に永続化→broker 呼び出し→broker_order_id 保存→OrderAccepted に遷移」フロー（2相永続化の説明をコメントで明記）。
    - OrderSentPendingError（ブローカーが注文番号を発行したが約定しないケース）を取り扱い、pending 状態の扱いを明示。
    - sync_order で broker 側ステータスを内部状態に同期。部分約定の進行で filled_qty/avg_fill_price を更新。
- Broker / kabu station クライアント
  - KabuStationClient を追加（src/kabusys/execution/kabu_client.py）:
    - httpx を用いた同期 REST クライアント。トークン取得（/token）を遅延初期化し、401 時に再取得して再試行する実装。
    - レスポンスの JSON パース失敗やネットワーク/タイムアウトを BrokerAPIError 等に変換。
    - HTTP 429 を RateLimitError にマップ。
    - WebSocket push 用の stream_push 接続を想定した設計（push の受信は ExecutionEngine 側で扱う）。
- 監視 / DB 初期化
  - monitoring_db 初期化関数を呼び出す箇所を run_execution/run_monitoring に追加し、監視テーブル存在を保証（冪等）。
  - ExecutionEngine で発注成功時に監視 DB (MonitoringDB) へ trade event を記録するフックを実装（監視 DB 存在時のみ）。
- その他ユーティリティ
  - process_priority 設定ユーティリティ呼び出しを追加（実行開始時に優先度を "high" に設定）。
  - logging_setup を用いたログ初期化を追加。

### Changed
- 設定管理
  - Settings のプロパティ実装により、無効な KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値で ValueError を送出するようにして早期検出が可能に。
  - DUCKDB/SQLite 等のデフォルトパスは Path.expanduser() を使用してチルダ展開に対応。
- 発注フロー
  - 発注ロジックのエラー処理設計を詳細化（OrderSentPendingError の明示的扱い、Reconciliation を考慮した broker_order_id 永続化順序）。
  - ExecutionEngine のセッション制御を時間帯ベース（signal_send_start/end, market_close）に分離。

### Fixed
- .env パース
  - クォート内のエスケープ処理や inline コメントの誤判定に関する問題を修正（より現実的な .env ファイルに対応）。
- DB/ファイルパスチェック
  - 実行前に親ディレクトリ存在チェックを行い、起動時自動作成される可能性を警告することで誤ったパス設定による起動失敗を緩和。

### Security
- `.env` に関する注意喚起を config_setup の出力に明示（.env を絶対に Git にコミットしない旨のヘッダーを追加）。

### Known limitations / Notes
- config/*.yaml の内容検証は PyYAML がインストールされている場合にのみ実行。PyYAML がない場合は検証をスキップして警告を出力する。
- KabuStationClient は同期 httpx.Client ベースで実装しており、将来的に async 対応が可能（httpx.AsyncClient に置き換えれば対応可能）。
- 実行環境の一部（MonitoringDB 実装、BrokerAPI 実装等）はこの公開コード片では抽象化されており、具体的なブローカー実装と統合が必要。

---

このリリースはコードベースから推測して記載しています。実装内容の詳細（追加のモジュールやユーティリティ、外部依存など）はソースコードやドキュメントを参照してください。
# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-23

### 追加
- 全体
  - 初期リリース。環境変数ベースの設定管理、起動用スクリプト、発注エンジン、監視ループ、注文状態管理など自動売買システムの基盤機能を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 設定関連
  - Settings クラスを追加し、環境変数から各種設定を取得する API を提供（src/kabusys/config.py）。
    - 必須項目の取得時には未設定で ValueError を送出する `_require()` を実装。
    - DuckDB / SQLite / PID ファイルパスや各種しきい値、KABUSYS_ENV / LOG_LEVEL 判定などのプロパティを実装。
    - .env 自動ロード機能を導入（プロジェクトルートを `.git` または `pyproject.toml` で検出）し、読み込み順序を OS 環境 > .env.local > .env としている。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` のパース実装を強化（クォートやエスケープ、`export KEY=val` 形式、インラインコメントの扱いなどに対応）。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを追加し、.env の初期作成・更新を対話的に支援（src/kabusys/config_setup.py）。
    - シークレット項目は表示時にマスク。
    - 選択肢チェック、既存 .env の読込・再利用、確認後の書き込み（ファイル化）をサポート。
    - `--env-file` オプションで出力先ファイルを指定可能。

- 設定検証 CLI
  - `kabusys.validate_config` を追加し、起動前に .env と `config/*.yaml` の不備を検出するツールを提供（src/kabusys/validate_config.py）。
    - 必須/任意環境変数チェック、プレースホルダ検出（`_here` / `your_value` 等で警告）、KABUSYS_ENV / LOG_LEVEL の妥当性検査。
    - DuckDB/SQLite パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば safe_load で検証。未インストール時はスキップ）。
    - `--strict` オプションで警告を FAIL として exit(1) で終了するモードを提供。

- 実行・監視ランナー
  - `run_execution` スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine 起動用。paper_trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - プロセス優先度の設定、PID ファイルの書き出し、停止フラグ検知（data/stop_requested.flag）に対応。
  - `run_monitoring` スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを実装。環境に関係なく本番 sqlite_path を使用。
    - `MONITOR_POLL_INTERVAL` 環境変数で間隔上書き（デフォルト 60 秒、無効値は警告してデフォルトを使用）。

- 発注エンジン関連
  - ExecutionEngine を追加し、シグナルプル方式での発注フロー（シグナル処理ウィンドウと WebSocket push ドレイン）を実装（src/kabusys/execution/execution_engine.py）。
    - 信号読み込み、Gate1（シグナル単位リスクチェック）、Gate2（エグゼキューションレベルのレート制御・サーキットブレーカー）、Gate3（ドローダウン検査→kill switch）のチェックを実装。
    - size_multiplier 適用、発注レイテンシの計測、発注後の position_entries 更新（DuckDB）を行う。
    - WebSocket push を別スレッドで受信して _push_queue に投入、プッシュ処理で sync と Gate3 判定を実施。
    - kill_switch による全 active 注文キャンセル処理を実装。
  - ExecutionEngine のセッション制御（シグナル時間帯、market_close、PID 管理、kill.flag クリアポリシー）を提供。

- 注文管理・状態機構
  - OrderRecord と OrderState を追加（src/kabusys/execution/order_record.py）。
    - 明示的な状態列挙と許可遷移表を持つ（不正遷移は InvalidStateTransitionError）。
    - transition_to による状態遷移、関連フィールドの更新と updated_at 自動更新を実装。
  - OrderManager を実装（src/kabusys/execution/order_manager.py）。
    - create_order（signal_id の重複チェック、client_order_id の UUID4 採番）、send_order（2相永続化の説明付き: OrderSent を先にコミット → ブローカー呼び出し → broker_order_id を保存 → OrderAccepted へ遷移）、sync_order（broker 側状態と同期）、cancel_order（キャンセル不可状態のチェック）を実装。
    - Broker 側の特殊状況（OrderRejectedError, OrderSentPendingError）を適切に扱い、pending 情報を DB に残すことでリコンシリエーション可能に設計。
    - DuplicateOrderError を導入。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx を同期クライアントとして利用。トークン取得ロジック（遅延初期化・401 リトライ）を実装。
    - レスポンス JSON パース時のエラーを BrokerAPIError に変換、HTTP ステータス 429 を RateLimitError に、500 以上をサーバーエラー扱いにする等のエラーハンドリングを追加。
    - kabu station の状態コード → 内部ステータスのマッピングを定義。
    - WebSocket push の受信機能（stream_push）を期待する設計（有無を判定してスレッドスキップ可能）。

- 監視 DB 初期化
  - monitoring 用 DB 初期化関数（init_monitoring_db）と SystemMonitor を使う起動フローを run_monitoring/run_execution に組み込み（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。

### 変更
- 設定パースの挙動
  - .env のクォート付き値でバックスラッシュエスケープを考慮するよう強化。
  - コメント処理のルールを明確化（クォートなし値中の '#' は直前がスペース/タブの場合のみコメントと見なす）。

### 修正
- 発注のクラッシュ耐性を設計に反映
  - send_order の処理で OrderSent を先に永続化し、その後 broker_order_id をコミットすることで、途中クラッシュ時にもリコンシリエーションで状態回復可能な仕組みを採用（src/kabusys/execution/order_manager.py）。

### 注意点 / ドキュメント
- validate_config は PyYAML が未インストールの場合、YAML の内容検証をスキップして警告する。
- run_monitoring は監視用でも本番 sqlite_path を使用する設計であるため、本番データベースにアクセスする点に注意。
- ExecutionEngine は kill.flag の存在により起動拒否する挙動（KILL_FLAG_CLEAR_ON_START によるクリアはオプション）を持つ。

### 既知の制限
- 一部のブローカー API 抽象（BrokerAPIProtocol, BrokerAPIError など）は外部モジュール／他ファイルで定義される想定であり、環境による実装差分が存在する。
- KabuStationClient は同期 httpx.Client ベースで実装されており、将来的な async 対応は httpx.AsyncClient への差し替えを想定。

---

今後のリリースではユニットテスト、ドキュメント（API 仕様書）、および各種例外・ロギングのさらなる整備を予定しています。
# CHANGELOG

すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

<!--
Note: 日付はリリース日を表します（ここではパッケージ版初回リリースとして 2026-04-23 を使用）。
-->

## [0.1.0] - 2026-04-23

### 追加 (Added)
- パッケージ基本情報
  - パッケージ初期リリース。バージョンは `__version__ = "0.1.0"`。

- 環境設定 / 読み込み
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env の読み込みでは OS 環境変数を保護するため protected キーの仕組みを導入。
    - .env パース処理の強化:
      - export KEY=val 形式に対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
      - インラインコメントの扱いを改善（クォート有無で取り扱いが異なる）。
    - Settings のプロパティ群を定義（必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。各種パスや閾値、paper_trading 用パス・モードなどを取得するプロパティを提供。
    - `paper_fill_mode` で有効値検査を行い、不正値は ValueError を送出。
    - `env` / `log_level` の検証を行い、不正値は ValueError を送出。

- .env 設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードにより .env を初期作成 / 更新するコマンドラインツールを追加。
    - 使用例: `python -m kabusys.config_setup`
    - 各設定項目 (KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等) の対話的入力をサポート。シークレットはマスク表示。
    - デフォルト値、選択肢、説明表示、既存 .env の読み込み（Enter で再利用）をサポート。
    - .env を書き出すテンプレートを用意（書き込み時に Git にコミットしない旨の注記を挿入）。
    - `--env-file` オプションで書き出し先を変更可能。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 起動前に環境変数や config/*.yaml の設定不備を検出する CLI を追加。
    - 使用例: `python -m kabusys.validate_config`、警告を FAIL 扱いにする `--strict` オプションをサポート。
    - チェック内容:
      - 必須環境変数の未設定検出およびプレースホルダ値の警告。
      - KABUSYS_ENV の妥当性検査（development / paper_trading / live）。
      - LOG_LEVEL の妥当性検査（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
      - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在確認（存在しない場合は警告）。
      - config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）の存在確認と（PyYAML がインストールされている場合の）パース検証。PyYAML 未インストール時はパース検証をスキップして警告を出力。
      - KABUSYS_ENV=live の場合に追加ガード（LINE 通知設定, KILL_FLAG_CLEAR_ON_START の危険設定など）をチェック。
    - 検証結果を INFO/WARNING/ERROR として出力し、エラー発生時は exit(1)。`--strict` で警告も exit(1)。

- 実行・監視ランナー
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプト。
    - paper_trading モード時は専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
    - 停止フラグファイル (data/stop_requested.flag) を検出して安全に停止。
    - PID ファイル (data/execution.pid) を書き込み。スレッド監視と安全なシャットダウンを実装。
    - プロセス優先度を高く設定するユーティリティ呼び出しを行う（set_process_priority）。

  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - Monitoring は環境にかかわらず本番 SQLite を使用する（監視データは共通）。
    - stop フラグファイルでループ停止。例外はログに残して次ポーリングへ復帰。

- 注文状態管理と発注フロー
  - src/kabusys/execution/order_record.py
    - OrderRecord データモデル（dataclass）と状態遷移ロジックを実装。
    - OrderState 列挙型を導入（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可される状態遷移セットを明示し、不正遷移時は InvalidStateTransitionError を発生させる。
    - transition_to メソッドで updated_at を UTC で自動更新し、broker_order_id/filled_qty/avg_fill_price/error_message をキーワード更新可能。

  - src/kabusys/execution/order_manager.py
    - OrderRecord と OrderRepository（SQLite）を組み合わせ、外向き API を提供。
    - create_order: signal_id 毎の重複防止（部分ユニーク index / DB 制約の扱いを含む）。重複時は DuplicateOrderError。
    - send_order: 発注フローを二段階永続化で安全に実装（OrderCreated -> OrderSent を先に DB に永続化してから broker に送信）。broker_order_id を先にコミットし、その後 OrderAccepted へ遷移する等、クラッシュ後の再同期待ち問題を考慮した設計。
    - send_order は OrderRejectedError, OrderSentPendingError を適切に扱う。OrderSentPendingError は broker が注文番号を発行したが約定しないケースで伝播させる（DB 上は broker_order_id 保存 + state OrderSent）。
    - sync_order: broker 側状態取得と DB 同期処理を実装（部分約定の更新、状態遷移の補正）。OrderSent→Filled/PartialFill は OrderAccepted を経由して遷移するロジックを含む。
    - cancel_order: DB の現在状態を確認し、キャンセル不可能な状態では InvalidStateTransitionError を発生。broker_order_id があれば API で cancel を呼び、Cancelled に遷移して更新。

- ExecutionEngine 本体
  - src/kabusys/execution/execution_engine.py
    - Signal Queue Pull 型発注エンジンを実装。
    - EngineConfig により target_date と時間帯（signal_send_start, signal_send_end, market_close）を指定可能。デフォルトは 8:50 / 9:10 / 15:30。
    - シグナル処理 (_process_signals): size_multiplier 適用（BUY のみ）、100 株単位切り捨て、Gate1（シグナルレベル）・Gate2（エグゼキューションレベル / レート制限）を順に検査。Gate2 は最大 3 回リトライ、Circuit Breaker の場合はシグナルループを停止。
    - 発注後は position_entries（DuckDB）へ約定予定日を記録（BUY は挿入、SELL は sell_date 更新。ただし SELL pending は記録しない）。
    - 発注時のレイテンシを監視 DB に記録する仕組みを追加（monitoring_db が渡されている場合）。
    - push ドレイン処理 (_drain_push_queue / _handle_push): broker からの push 通知を処理し、broker_order_id→client_order_id を照合して sync_order を呼ぶ。push 受信時に Gate3（ドローダウン監視）を評価し、NG の場合は kill_switch を発動。
    - kill_switch: 全ループ停止と全 active 注文のキャンセルを実施。cancel 時の例外処理（InvalidStateTransitionError, BrokerAPIError 等）を許容して継続。
    - WebSocket スレッドを起動して kabu push を queue に投入（broker が stream_push を持たない場合はスキップ）。
    - セッション起動時に Reconciliation を実行可能（reconciler が指定されている場合）。kill.flag の存在は設定により自動クリアまたは起動拒否（KILL_FLAG_CLEAR_ON_START を参照）。

- kabu station クライアント
  - src/kabusys/execution/kabu_client.py
    - KabuStation REST API 用同期クライアント実装（httpx を利用）。
    - トークン管理を内部で行う（遅延初期化、401 の際の再取得 + 1 回リトライ）。
    - レスポンス JSON パース失敗は BrokerAPIError に変換。
    - タイムアウトやネットワークエラーを BrokerAPIError に変換して扱う。
    - 429 (Too Many Requests) を受けた場合は RateLimitError を発生させる。
    - kabu station の注文状態コードを内部ステータス ('open', 'partial', 'filled', 'cancelled', 'rejected') にマップする辞書を導入。
    - 将来的な非同期対応は httpx.AsyncClient への切替で対応可能な設計。

- 監視 / DB 初期化
  - monitoring_db 初期化ユーティリティを呼び出すコードを run_monitoring / run_execution に組み込み、監視テーブルの存在を保証。

- ユーティリティ
  - ロギングセットアップ、プロセス優先度制御、などのユーティリティ関数を使用して起動時に適切な初期化を行う。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

---

注記:
- このリリースは初期実装であり、外部依存（例: PyYAML, httpx, websocket, duckdb 等）の有無によって一部機能は挙動が変わります（validate_config の YAML 検証や KabuStation の通信等）。
- .env ファイルは秘匿情報を含むため、README 等で .env の取り扱い（Git にコミットしない）を徹底してください。
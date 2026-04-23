Keep a Changelog
================

すべての重大な変更はこのファイルに記載します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 初期公開: KabuSys コア機能を追加。
  - パッケージメタ情報
    - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として設定。
  - 環境設定 / ロード
    - src/kabusys/config.py
      - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロードする仕組みを実装。
      - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
      - .env のパース機能を実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行中コメント処理）。
      - .env 読み込み時、OS 環境変数を保護するための protected キーセットをサポート（.env.local は既存 OS 変数を上書き可能）。
      - Settings クラスを実装し、設定プロパティ（トークン・パスワード・DB パス・LINE トークン・PID/kill flag パスなど）を提供。
      - 環境値の検証を行うプロパティ（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を実装。無効値は ValueError を送出。
  - 設定ウィザード CLI
    - src/kabusys/config_setup.py
      - 対話式ウィザードで .env を初期作成/更新する機能を実装。
      - シークレット項目は表示をマスク、選択肢やデフォルトをサポート。
      - 生成される .env にヘッダコメントを付与し、Git にコミットしない旨の注意書きを含む。
      - 実行例: python -m kabusys.config_setup
  - 設定検証 CLI
    - src/kabusys/validate_config.py
      - .env と config/*.yaml の起動前検証ツールを提供。
      - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェックを行う。
      - PyYAML が存在すれば config/*.yaml をパースして内容検証を行う。未インストール時はパース検証をスキップして警告を出力。
      - --strict オプションを実装（警告を FAIL として exit(1)）。
      - 実行例: python -m kabusys.validate_config
  - 実行スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine の起動スクリプトを実装。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
      - PID ファイル、停止フラグ（data/stop_requested.flag）検知、プロセス優先度設定を組み込み。
      - 実行例: python -m kabusys.run_execution（エントリポイントスクリプト）
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを実装。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックして警告。
      - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
  - Execution / 発注系コア
    - src/kabusys/execution/order_record.py
      - OrderRecord データモデルと状態遷移ロジックを実装（状態列挙 OrderState と許可遷移マップ）。
      - 不正な状態遷移に対する InvalidStateTransitionError を導入。
      - updated_at の自動更新や部分フィールド更新をサポート。
    - src/kabusys/execution/order_manager.py
      - OrderManager を実装し、create/send/sync/cancel の外向き API を提供。
      - create_order: signal_id に対する重複（active 注文）検出と DuplicateOrderError を実装。DB の一部ユニーク制約違反を DuplicateOrderError にマッピング。
      - send_order: 2 段階永続化（OrderSent を DB にコミット → broker API 呼び出し → broker_order_id を先に保存 → OrderAccepted へ遷移）によりクラッシュ耐性を考慮したワークフローを実装。
      - OrderRejectedError / OrderSentPendingError を適切にハンドリング（pending 時は broker_order_id を保存して再送出）。
      - sync_order: broker 側のステータス取得とローカル状態の同期（部分約定更新を含む）。注文未発行（broker_order_id None）や broker が None を返すケースを考慮。
      - cancel_order: 終端状態判定後に API 呼び出しと Cancelled への遷移を行う。
    - src/kabusys/execution/execution_engine.py
      - ExecutionEngine 実装（Signal Queue Pull 型）。
      - EngineConfig で日付・発注時間窓・マーケット終了時刻を指定可能。
      - シグナル取り込み (_read_signals)、Gate1/2/3 によるリスク検査フロー、レート制限リトライ、DuplicateOrder の回避、発注レイテンシ計測、監視DB ログ連携を実装。
      - kill_switch による全 active 注文キャンセルの仕組みを実装。外部 stop() は kill_switch の公開エイリアス。
      - WebSocket スレッド（broker が stream_push を持つ場合）で push を受け取り _push_queue を処理する仕組みを実装。
      - セッション起動時に Reconciler を用いたリコンシリエーションを実行するフックを用意。
      - PID ファイル管理、kill.flag の起動時動作（KILL_FLAG_CLEAR_ON_START による自動クリア制御）を実装。
    - src/kabusys/execution/kabu_client.py
      - kabu station REST API クライアント（同期 httpx ベース）を実装。
      - トークン管理を内部で行い、401 を受けたら自動再取得して 1 回リトライする実装。
      - レスポンス JSON パース失敗やネットワーク/タイムアウトを BrokerAPIError に変換して扱う。
      - 429 を RateLimitError にマップ、5xx をサーバエラーとして扱うなどエラー分類を実装。
      - push（WebSocket）受信を想定した stream_push 連携を想定可能な設計。
  - リスク管理 / ブローカー抽象
    - ExecutionEngine と OrderManager で RiskManager / BrokerAPIProtocol と連携するインターフェースを想定した設計。Rate limit / circuit breaker / API 成功/失敗の記録などを組み込みやすい構成。
  - DB / 分析
    - DuckDB / SQLite を併用する構成を採用。Execution/Monitoring でそれぞれ用途を分離。
    - ExecutionEngine から DuckDB に対して position_entries の INSERT / UPDATE を行うことで約定・保有日管理を行う処理を追加。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- config_setup において .env にシークレット値（トークン/パスワード）を書き込むが、README 等で .env を Git にコミットしないよう注意喚起するヘッダを出力する設計。

Notes / 備考
- validate_config は PyYAML が存在しない場合に YAML 内容の検証をスキップして警告を出すため、 config/*.yaml のパース検証を行いたい場合は PyYAML をインストールしてください。
- KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE などの不正値は Settings のプロパティで例外を投げる設計になっているため、ライブラリを利用するコード側で適切にエラー処理を行ってください。
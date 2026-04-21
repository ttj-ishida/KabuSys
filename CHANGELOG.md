# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-04-21

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主な追加・実装内容は次のとおりです。

### Added
- 設定・環境周り
  - Settings 設定管理モジュールを追加（src/kabusys/config.py）。
    - 環境変数・.env ファイルからの設定読み込み。
    - 自動 .env ロード（プロジェクトルートの検出：.git または pyproject.toml 基準）。
    - .env/.env.local の読み込み順序、OS 環境変数の保護（上書き禁止）をサポート。
    - .env のパース機能を強化（export 形式、クォート文字列、行内コメント等に対応）。
    - 必須値取得時に未設定なら ValueError を投げる _require を実装。
    - PAPER_FILL_MODE、データベースパス、PID/KILL フラグ等の各種プロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを行い、不正値で例外を発生させる。

  - .env 初期化ウィザードを追加（src/kabusys/config_setup.py）。
    - 対話式で .env を作成・更新する CLI（python -m kabusys.config_setup）。
    - シークレット値のマスク、選択肢・デフォルト値表示、キャンセル/確認フローを実装。
    - .env のテンプレート出力ロジックを提供。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - .env と config/*.yaml の起動前検証用ツール（python -m kabusys.validate_config）。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の存在チェックとプレースホルダ検出。
    - KABUSYS_ENV の値検証（development / paper_trading / live）と live 時の注意喚起。
    - LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック。
    - PyYAML があれば config/*.yaml のパース検証を実施。未インストール時はスキップして警告。
    - --strict オプションで警告を FAIL（exit 1）として扱うモードを提供。

- 実行用エントリースクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine の起動、プロセス優先度設定、DB 接続（DuckDB/SQLite）を行う。
    - paper_trading 環境では専用の paper_trading SQLite を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検出で安全停止。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL（秒）で間隔を上書き可能。
    - 監視は環境に関わらず本番 sqlite_path を使用。

- 発注エンジン / 実行ロジック
  - ExecutionEngine を実装（src/kabusys/execution/execution_engine.py）。
    - セッションスケジュール（シグナル処理 8:50-9:10、プッシュドレイン 9:10-15:30）。
    - 起動時リコンシリエーションの実行（Reconciler 連携）。
    - kill.flag による起動拒否 / 自動クリア（KILL_FLAG_CLEAR_ON_START）対応。
    - PID ファイル書き出し、WebSocket プッシュ受信スレッドの実装（broker が stream_push を持つ場合）。
    - DuckDB からのシグナル読み込み、Gate1/2（シグナル・エグゼキューション検査）による発注制御、Gate3（ドローダウン監視）での kill_switch 発動。
    - 発注処理における監視 DB へのイベント記録（遅延計測等）。

- 注文状態管理 / 永続化
  - OrderRecord（状態機械のデータモデル）を実装（src/kabusys/execution/order_record.py）。
    - 明確な OrderState 列挙、許容遷移テーブル、遷移検証ロジック（InvalidStateTransitionError）を実装。
    - broker_order_id、filled_qty、avg_fill_price、error_message 等の更新をサポート。
  - OrderManager を実装（src/kabusys/execution/order_manager.py）。
    - create_order：signal_id に対する重複チェック（DB の部分ユニーク制約と整合）。
    - send_order：クラッシュ安全性を考慮した 2 相永続化フロー（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 保存 → OrderAccepted へ遷移）。
    - OrderRejectedError / OrderSentPendingError の扱いを実装（pending は broker_order_id を保存して例外透過）。
    - sync_order：broker 側の状態を照会してローカル状態を同期（部分約定時のフィールド更新も対応）。
    - cancel_order：終端状態の取り扱いと broker cancel 呼び出し、キャンセル遷移の永続化。
    - DuplicateOrderError 型で同一 signal_id の重複を表現。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期 API クライアント。
    - トークン取得（/token）を遅延初期化し、401 時の自動再取得 + 再試行を実装。
    - レスポンス JSON パース失敗、ネットワークタイムアウトなどを BrokerAPIError に変換してハンドリング。
    - 429 を RateLimitError として扱う。
    - send_order：発注ペイロード組立て（成行は Price=0 に強制）、発注拒否時に OrderRejectedError を返す。
    - cancel_order、注文照会の骨格を実装（get_order_status の実装途中まで含む）。
    - websocket（push）受信用に websocket クライアントの利用想定（stream_push 経由で ExecutionEngine と連携）。

- 監視（Monitoring）
  - init_monitoring_db の呼び出しを通じて監視用 SQLite テーブルの初期化処理を導入。
  - ExecutionEngine / シグナル発注フローから監視 DB へトレードイベントを記録する機能を追加。

- ユーティリティ
  - ロギングセットアップ、プロセス優先度設定ユーティリティ（setup_logging, set_process_priority）を利用。
  - パッケージ初期化ファイルにバージョン定義を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

### Changed
- 初回リリースのため、既存の外部仕様は新規追加の実装に合わせて定義。

### Fixed
- 初回リリースのため、バグ修正履歴は無し。

### Notes / 制約・既知の挙動
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途向け）。
- validate_config は PyYAML が未インストールの場合、YAML パース検証をスキップして警告を出します。
- KabuStationClient の注文照会周りの詳細実装は今後の拡張で完成予定（スニペット末尾で実装継続の痕跡あり）。
- ExecutionEngine は WebSocket プッシュを broker 側で提供していることを前提に設計されています（提供されない場合は警告を出してスレッドをスキップ）。

今後の予定: KabuStationClient の注文照会/パースロジックの完成、テストカバレッジの追加、Reconciler / Broker 抽象の拡張と堅牢性向上。
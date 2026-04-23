# CHANGELOG

すべての注目すべき変更を時系列で記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-23

初回リリース。KabuSys の基本的な設定管理・実行・監視・発注基盤を提供します。

### Added
- パッケージ初期化とバージョン情報
  - package: kabusys、__version__ = 0.1.0

- 環境変数 / 設定管理
  - Settings クラス（kabusys.config）を実装。プロパティ経由で設定値を取得（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、環境判定等）。
  - .env 自動読み込み機能：
    - プロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）。
    - _parse_env_line により export KEY=val、クォート（シングル／ダブル）とバックスラッシュエスケープ、行内コメントルール等を取り扱う堅牢なパーサを実装。

- 設定ウィザード CLI（kabusys.config_setup）
  - 対話式ウィザードで .env の作成・更新を支援。
  - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DBパス, LINE 通知設定等）とデフォルト値、選択肢、シークレット対応。
  - 既存 .env の読み込み、確認、保存処理を実装。保存時に .env を上書きするテンプレート出力を提供。
  - .env を絶対に Git にコミットしない旨のヘッダを出力。

- 設定検証 CLI（kabusys.validate_config）
  - .env と config/*.yaml の事前検証ツール。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）とプレースホルダ検知、KABUSYS_ENV 値チェック（development/paper_trading/live）、LOG_LEVEL 検証などを実施。
  - config/*.yaml 存在チェックと（PyYAML があれば）パース検証を実行。
  - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定未設定の警告、KILL_FLAG_CLEAR_ON_START の危険値警告）。
  - --strict オプションで警告も FAIL（exit 1）として扱う。

- 実行・監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト。プロセス優先度設定、PID/停止フラグ管理、DB 接続の確立。
    - Paper Trading 時は settings.paper_sqlite_path（data/paper_trading.db など）を使用して本番 DB と完全分離。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は実行環境にかかわらず本番 sqlite_path を使用。

- 発注フロー実装（execution サブパッケージ）
  - OrderRecord（order_record.py）
    - 注文状態の列挙 OrderState と状態遷移の許可テーブルを実装。
    - transition_to による状態遷移検証（不正遷移で InvalidStateTransitionError を raise）。
  - OrderRepository（参照のみ、SQLite を通じた永続化を想定）
  - OrderManager（order_manager.py）
    - signal_id の重複検出（DuplicateOrderError）。
    - create_order / send_order / sync_order / cancel_order の外向き API を提供。
    - send_order はクラッシュ耐性を考慮した二相的永続化（OrderSent を永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）および OrderSentPendingError の取り扱いを実装。
    - sync_order による broker 状態との再同期ロジック（部分約定の更新、OrderSent→OrderAccepted の中間遷移処理等）。
  - ExecutionEngine（execution_engine.py）
    - Signal Queue Pull 型の発注エンジン。シグナル処理（8:50-9:10）、WebSocket push ドレインループ（9:10-15:30）を想定したセッション実行。
    - Gate1（シグナルレベル）、Gate2（エグゼキューションレベル/レート制限、Circuit Breaker）、Gate3（ドローダウン監視）によるリスクチェックと kill_switch 発動の仕組みを実装。
    - kill_switch により全 active 注文のキャンセルを試行し、ループを停止。
    - WebSocket push を受けて _push_queue に投入、push を基に sync_order を呼び出す処理を実装。
    - 発注後の position_entries 更新（DuckDB で次営業日を計算）や監視 DB への trade event ログ記録（MonitoringDB 経由）を実装。

- ブローカークライアント - kabu station 実装（kabu_client.py）
  - KabuStationClient: httpx を用いた同期 REST クライアント。
  - トークン管理（遅延初期化、自動再取得）と 401 リトライ処理を実装。
  - レスポンス JSON パース失敗やネットワーク例外を BrokerAPIError に変換。
  - 429 を RateLimitError にマッピング、サーバーエラーは BrokerAPIError に変換。
  - kabu の注文状態コードを内部状態文字列にマップするロジックを実装。
  - 将来的な async 対応は httpx.AsyncClient への切り替えで容易に対応できる設計。

- その他ユーティリティ
  - process_priority の設定呼び出し（utils.process_priority）, ロギングセットアップ（utils.logging_setup）を参照して使用。
  - Monitoring 初期化（monitoring_db.init_monitoring_db）を実行して監視テーブルの存在を保証。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security / Notes
- .env ファイルは絶対にリポジトリにコミットしないことを README と .env ヘッダで明記。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に設定することを推奨。1 にすると起動時に kill_flag を自動クリアし、危険な動作につながる可能性がある。
- validate_config や config_setup での警告・検証を起動前に実行することを推奨。

---

将来的改善案（メモ）
- KabuStationClient の async サポート（httpx.AsyncClient）の追加。
- config/*.yaml のより詳細なスキーマ検証（PyYAML によるロードだけでなく型/値チェック）。
- 監視・発注フローの e2e テスト増強。
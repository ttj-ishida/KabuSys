# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。

このプロジェクトの初回リリースを記録しています。

## [0.1.0] - 2026-04-22

### 追加
- 基本的なパッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / 設定管理
  - .env ファイルの読み込みとパースを行う config モジュールを追加
    - .git / pyproject.toml を基準にプロジェクトルートを探索して自動的に .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
    - export KEY=val 形式、クォート文字中のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮した堅牢なパーサを実装
    - OS 環境変数を保護するための protected 上書き制御を実装
  - Settings クラスを提供し、環境変数から型変換・検証済みのプロパティを取得可能に
    - 必須値取得時のエラー (_require)
    - env/log_level 等の値検証（許容値チェック）
    - データベースパス（duckdb/sqlite）、PID/kill flag パス、監視閾値などのプロパティ
    - Paper Trading 用設定（paper_sqlite_path, paper_fill_mode）

- .env 作成ウィザード CLI
  - kabusys.config_setup: 対話式ウィザードで .env の初期作成・更新を支援
    - シークレット入力（マスク表示）、選択肢、デフォルト値、説明文をサポート
    - 既存 .env の読み込みおよび Enter による既存値再利用
    - ファイル書き出しテンプレートを提供（.env を絶対にコミットしない旨の注意を含む）

- 設定検証 CLI
  - kabusys.validate_config: 起動前に環境変数・config/*.yaml の設定不備を検出する CLI を追加
    - 必須/任意環境変数の検査、プレースホルダ検出（_here / your_value）で警告
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（存在しない場合は警告）
    - config/*.yaml の存在確認・パース検証（PyYAML がインストールされている場合）
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）
    - --strict オプションで警告を fail（exit(1)）扱いにできる

- 実行・監視プロセス起動スクリプト
  - run_execution: ExecutionEngine の起動スクリプトを追加
    - プロセス優先度設定、PID ファイル書き出し、停止フラグ検出による安全終了
    - paper_trading 環境では専用 SQLite（paper_sqlite_path）を利用して本番 DB と分離
  - run_monitoring: SystemMonitor のポーリング起動スクリプトを追加
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境にかかわらず本番 sqlite_path を使用

- 発注エンジン関連
  - ExecutionEngine：Signal Queue Pull 型発注エンジンを実装
    - シグナル処理（指定時間窓）と WebSocket push ドレインループ（別窓）をサポート
    - kill.flag 検査・kill switch ロジック、PID ファイル管理、WebSocket ワーカー統合
    - Gate1（シグナルレベル）, Gate2（エグゼキューション・レート制御）, Gate3（ドローダウン監視）を導入
    - size_multiplier の適用（BUY のみ）、position_entries への書き込み（DuckDB）を実装
    - 監視 DB への発注イベント記録（MonitoringDB）へのフックを実装
  - run_session / run loop とスレッド管理・例外ハンドリングを整備

- 注文関連コンポーネント
  - OrderRecord：状態機械（OrderState）と状態遷移検証ロジックを純粋ロジックで実装
    - 許可される遷移テーブルと transition_to による更新（updated_at 自動更新、オプションフィールド更新）
    - InvalidStateTransitionError を定義
  - OrderManager：外向き API として create/send/sync/cancel を実装
    - create_order: signal_id による重複チェック（DB の部分ユニーク制約違反を DuplicateOrderError に変換）
    - send_order: 二相永続化戦略
      - OrderSent へ遷移して DB に commit した後に broker API を呼ぶ（クラッシュ耐性）
      - broker_order_id の先行コミット → OrderAccepted へ遷移の順序により、クラッシュ後の Reconciliation を想定
      - OrderRejectedError / OrderSentPendingError のハンドリング（pending は OrderSent のまま broker_order_id を保存）
    - sync_order: broker の状態照会によりローカル状態を同期（部分約定の進捗更新を含む）
    - cancel_order: 終端状態判定により API 呼び出し有無を決定

- ブローカ API クライアント
  - KabuStationClient（kabu_client）を追加
    - httpx を用いた同期 REST クライアント実装
    - トークン取得の遅延初期化と 401 時の自動再取得（1 回リトライ）
    - レスポンス JSON パース例外、タイムアウト、ネットワークエラー、429（RateLimitError）等を専用例外に変換
    - kabu ステーションの注文状態コードを内部ステータス（open/partial/filled/...）へマッピング
    - WebSocket push 受信（stream_push）を想定した stream_push 呼び出しフックに対応（ExecutionEngine の WebSocket ワーカーから利用）

- リスク管理 / リコンサイル / その他ユーティリティ（インテグレーション）
  - RiskManager / Reconciler / OrderRepository / BrokerClientFactory 等の組立てを行う Execution 起動フローを整備（実装ファイルは本リリースに含まれる）
  - init_monitoring_db を用いた監視用 SQLite の初期化をサポート
  - logging_setup, process_priority ユーティリティと統合

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 既知の注意点 / 運用メモ
- .env は決してリポジトリにコミットしないこと（config_setup の生成ヘッダーにも明記）
- 本番稼働時は KABUSYS_ENV=live を慎重に扱う（validate_config の警告を参照）
- KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると起動時に kill.flag が自動クリアされるため危険（validate_config で警告）
- Paper Trading は DB を分離（PAPER_TRADING_SQLITE_PATH / paper_sqlite_path）しているため、本番データと混在しない
- PAPER_FILL_MODE の許容値: instant / partial / never / reject。無効値は起動時に例外を発生させる
- MONITOR_POLL_INTERVAL に 0 以下や非整数を指定した場合、デフォルト（60 秒）にフォールバックする

### 今後の検討事項（非破壊的改善案）
- KabuStationClient の非同期対応（httpx.AsyncClient）による WebSocket / API の統合
- validate_config の YAML スキーマ検証（PyYAML のみでなく stricter な検証）
- send_order の永続化に関するさらなる堅牢化（トランザクションメトリクス、追跡情報の増強）
- テスト用フックの拡充（ExecutionEngine の時間制御、WebSocket モックなど）

-- End of changelog --
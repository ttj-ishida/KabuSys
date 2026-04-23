# Changelog

すべての注目すべき変更点はここに記録します。
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース。日本株自動売買システム "KabuSys" の基本機能を実装しました。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。

- 環境設定・読み込み周り
  - Settings クラスを追加（src/kabusys/config.py）。
    - 環境変数から各種設定（J-Quants トークン、kabu API パスワード、DB パス、PID/KILL フラグ等）を取得。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値検証を実装。
    - paper_trading 用の別 SQLite DB（PAPER_TRADING_SQLITE_PATH）サポート。
    - kill_flag_clear_on_start 等のフラグをプロパティとして提供。
  - .env 自動読み込み機能を追加。
    - プロジェクトルート（.git または pyproject.toml が基準）を探索して .env / .env.local を読み込む。
    - OS 環境変数を保護し、.env.local は上書き可能（優先度: OS > .env.local > .env）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
  - .env パーサを実装（_parse_env_line）。
    - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱いなどに対応。

- 環境設定ウィザード CLI
  - config_setup.py を追加（src/kabusys/config_setup.py）。対話式で .env を生成/更新できる。
    - 設定項目定義（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DB パス / LINE トークン 等）。
    - 既存 .env の読み込み、入力補助、シークレット表示マスク、ファイル書き出し機能を実装。
    - 出力テンプレートで .env を生成し、保存案内を表示。

- 設定検証 CLI
  - validate_config.py を追加（src/kabusys/validate_config.py）。
    - 必須/任意環境変数の存在と妥当性チェック（プレースホルダ検出を含む）。
    - KABUSYS_ENV / LOG_LEVEL の検証と "live" 時の注意喚起（LINE 通知設定・KILL_FLAG_CLEAR_ON_START など）。
    - DUCKDB/SQLite の親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - --strict オプションで警告も失敗扱いにできる。
    - 実行例: python -m kabusys.validate_config

- 実行スクリプト
  - run_execution.py を追加（src/kabusys/run_execution.py）。
    - ExecutionEngine の起動スクリプト。process priority 設定、PID/stop フラグ管理、SQLite/duckdb 接続、paper_trading 用DB分離等を実装。
  - run_monitoring.py を追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor ポーリングループ。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。

- 注文管理・発注エンジン
  - OrderRecord（状態機械）を追加（src/kabusys/execution/order_record.py）。
    - 明示的な OrderState 列挙、許可遷移、transition_to による遷移検証、InvalidStateTransitionError を実装。
  - OrderManager を追加（src/kabusys/execution/order_manager.py）。
    - create_order / send_order / sync_order / cancel_order を実装。
    - 同一 signal_id に関する DuplicateOrderError の検出（DB の部分ユニーク制約処理含む）。
    - send_order はクラッシュ耐性を考慮した 2 段階永続化（OrderSent へ更新 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ更新）。
    - OrderRejectedError / OrderSentPendingError の扱い（pending の永続化と伝播）をサポート。
    - sync_order による外部ブローカー照合で、部分約定や状態遷移（OrderSent→OrderAccepted 経由）を補正。

  - ExecutionEngine を追加（src/kabusys/execution/execution_engine.py）。
    - シグナル取得（DuckDB）→ Gate1/Gate2 のリスクチェック→発注の流れを実装。
    - size_multiplier の適用（BUY のみ）や qty の 100 株単位丸め対応。
    - API レート制限リトライ、Circuit Breaker 判定によりシグナルループ停止。
    - 発注後の position_entries 記録（次営業日を fill_date として登録。BUY は登録、SELL は pending で分岐）。
    - WebSocket push ドレイン機構（_push_queue）と _websocket_worker（broker の stream_push を利用する場合のみ起動）。
    - Gate3（ドローダウン等）で NG の場合は kill_switch を発動して全 active 注文をキャンセル。
    - セッションライフサイクル（signal_send_start, signal_send_end, market_close）を管理し、PID ファイルと kill.flag の扱いを実装。
    - run_session で Reconciliation の実行（設定されている場合）と例外耐性を備える。

- Broker / kabu station クライアント
  - KabuStationClient を追加（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期 REST クライアント実装。
    - トークン取得の遅延初期化・自動再取得（401 時に再取得してリトライ）。
    - レスポンス JSON パース例外を BrokerAPIError に変換。
    - HTTP ステータスに基づくエラー分類（401/429/5xx など）と RateLimitError の導入。
    - kabu station の状態コードを内部ステータス文字列にマッピング。

- 監視関連
  - Monitoring 初期化呼び出しと DB 接続を run_monitoring/run_execution に組み込み。
  - ExecutionEngine の発注イベントを監視 DB にログする箇所を追加（監視DB が提供されている場合）。

- ユーティリティ
  - process_priority 設定、ログセットアップ等のユーティリティ呼び出しを起動スクリプトに組み込み（高優先度設定、ログカテゴリ設定等）。
  - stop/kill flag による外部制御（data/stop_requested.flag, data/execution.pid 等）を採用。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- 本リリースでは特記すべきセキュリティ修正はありませんが、.env は絶対に Git にコミットしないよう注意書きを config_setup の出力に明記しています。

注:
- 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時はコミット履歴や意図した変更点に基づいて調整してください。
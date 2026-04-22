# Changelog

すべての重要な変更をこのファイルに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

[Unreleased]

## [0.1.0] - 2026-04-22
初回リリース。KabuSys のコア設定管理、実行エンジン、監視ランナー、発注ロジック周りの主要コンポーネントを追加しました。

### Added
- パッケージバージョンを定義
  - pkg: __version__ = "0.1.0"
- 環境変数/設定管理
  - 自動 .env ロード機能（プロジェクトルートを .git または pyproject.toml から検出）
  - .env パース機能の実装（export プレフィックス対応、クォート文字・バックスラッシュエスケープ、インラインコメント処理）
  - _load_env_file による上書き制御（override, protected）と KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - Settings クラス: アプリケーション設定のプロパティ群（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、各種しきい値など）を提供
  - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証ロジック

- 環境設定ウィザード CLI
  - python -m kabusys.config_setup で対話式に .env を作成/更新可能
  - 多数の設定項目を定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）
  - .env 読み書き（既存値の読み込み、シークレット表示マスク、保存確認）

- 設定検証 CLI
  - python -m kabusys.validate_config により起動前に .env や config/*.yaml の不備を検出
  - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック
  - config/*.yaml の存在チェックと PyYAML があればパース検証（PyYAML 未インストール時は警告）
  - --strict オプション：警告を FAIL として扱う

- 実行・監視ランナー
  - run_execution: ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）
    - paper_trading 環境では専用の paper_trading DB を使用して本番 DB と分離
    - プロセス優先度設定、PID ファイル書き出し、停止フラグ検出（data/stop_requested.flag）
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（python -m kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は常に本番 sqlite_path を使用

- 発注ロジック
  - OrderRecord: 注文状態のデータモデルと状態遷移ロジック（OrderState enum、遷移許可表、InvalidStateTransitionError）
  - OrderManager: 外向き API（create_order, send_order, sync_order, cancel_order）
    - create_order: signal_id 重複検出と部分ユニークインデックス違反を DuplicateOrderError に変換
    - send_order: クラッシュ安全性を考慮した二相的永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 保存 → OrderAccepted へ遷移）
    - OrderSentPendingError の扱い（注文番号は永続化した上で pending として残す）
    - sync_order: broker 側ステータス取得による同期（部分約定の進展はフィールド直接更新）
    - cancel_order: 終端状態検査と broker API 呼び出し

  - ExecutionEngine: Signal Queue Pull 型発注エンジン
    - エントリポイント run_session（シグナル処理 8:50-9:10、push ドレイン 9:10-15:30）
    - セッション起動時の Reconciliation 実行オプション（reconciler が設定されていれば実行）
    - kill.flag の扱い（起動拒否または KILL_FLAG_CLEAR_ON_START による自動クリア）
    - PID ファイル管理、WebSocket push の受け入れ（broker に stream_push がある場合）、push を受けての sync_order 実行と Gate3（ドローダウン）評価
    - _process_signals 内の Gate 1/2（シグナルレベル・実行レベル検査）、レートリミットリトライ、size_multiplier の適用（買いのみ）
    - 発注成功時の position_entries への記録（DuckDB を使用、発注日に基づき翌営業日をエントリ日とする）

  - Broker 関連
    - kabu_client: KabuStationClient の実装（httpx 同期クライアント）
      - トークン管理（遅延取得、401 時の再取得と 1 回リトライ）
      - レスポンス JSON パース例外の BrokerAPIError 変換、HTTP 429 を RateLimitError として扱う
      - タイムアウト / ネットワークエラーを BrokerAPIError に変換
    - BrokerAPIProtocol を前提にした設計（send_order / get_order_status / cancel_order / get_positions 等を利用）

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を利用して SQLite 監視 DB テーブルの初期化（冪等）

- ユーティリティ
  - setup_logging（アプリ名指定でログ設定）
  - set_process_priority（プロセス優先度を変更）

### Changed
- なし（初回リリースのため既存からの変更はありません）

### Fixed
- なし（初回リリース）

### Notes / 操作上の注意
- .env は絶対にリポジトリにコミットしないでください（config_setup にもその旨コメントを出力します）。
- 自動 .env ロードはデフォルトで有効ですが、テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- 本番運用時は KABUSYS_ENV=live の際に LINE 関連の通知設定や KILL_FLAG_CLEAR_ON_START の値を十分に確認してください（validate_config と config_setup で注意喚起を行います）。
- Paper trading（KABUSYS_ENV=paper_trading）では監視/発注の SQLite を本番と分離します（PAPER_TRADING_SQLITE_PATH により上書き可能）。
- ExecutionEngine の kill_switch は全 active 注文をキャンセルするため、想定外の発動は重大な影響を与えます。Gate/threshold の設定に注意してください。

---

将来のリリースでは、テストカバレッジ、さらに詳細な監視メトリクス、非同期 HTTP クライアント対応（httpx.AsyncClient）や追加ブローカー実装などを予定しています。
# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/）に準拠します。

現在のリリース: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-04-22
初回リリース。日本株自動売買フレームワーク「KabuSys」の基本機能を実装しました。

### Added
- パッケージ初期化
  - バージョン番号を `src/kabusys/__init__.py` にて `0.1.0` として設定。

- 環境変数 / 設定関連
  - Settings クラスを実装（src/kabusys/config.py）。
    - 環境変数から各種設定値（J-Quants トークン、kabu API パスワード、DB パス、PID/Kill flag パス、閾値など）を取得。
    - 環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の妥当性チェック）。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - OS 環境変数を保護する override/protected のロード動作を実装。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` オプションを追加。

  - .env パーサー実装（クォートやエスケープ、コメント処理に対応）。
  - 対話式ウィザード `config_setup` を追加（src/kabusys/config_setup.py）。
    - .env の初期作成／更新を対話式で支援（--env-file オプション）。
    - J-Quants / kabu / DB / LINE / ログレベル / Kill Switch など主要項目を網羅。
    - シークレット項目は表示時にマスク表示。生成される .env に注意書きを出力。

  - 設定検証 CLI `validate_config` を追加（src/kabusys/validate_config.py）。
    - .env と config/*.yaml の事前チェック。必須環境変数未設定はエラー、プレースホルダ値や不正値は警告。
    - --strict オプションで警告を失敗扱いにできる。
    - PyYAML 未インストール時は YAML 内容検証をスキップし、警告を出力。
    - config ファイルが見つからない場合に生成スクリプトの案内を表示。

- 実行エントリ（起動スクリプト）
  - Execution エンジン起動スクリプト `run_execution` を追加（src/kabusys/run_execution.py）。
    - process priority 設定、PID ファイル管理、stop フラグ検知。
    - paper_trading 環境時は専用 SQLite を使用し、本番 DB と分離。
    - DuckDB を分析用 DB として使用。
    - デーモンスレッドで ExecutionEngine を起動し、停止フラグで安全に停止。

  - Monitoring ポーリングループ `run_monitoring` を追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。

- Execution エンジンコア
  - ExecutionEngine 実装（src/kabusys/execution/execution_engine.py）。
    - シグナル読み込み（DuckDB）、Gate（リスク）チェック、発注フロー、WebSocket push ドレイン、セッション制御（8:50-9:10 シグナル、9:10-15:30 ドレイン）を実装。
    - kill.flag 検出時の振る舞い（起動拒否または自動クリアは KILL_FLAG_CLEAR_ON_START で制御）。
    - PID ファイル書き込み／削除の管理。
    - WebSocket push を別スレッドで受信し、_push_queue に積んで同期処理を行う。
    - 発注時の監視DBへのログ書き出し（監視 DB が渡された場合）。
    - position_entries の追記／更新（次取引日での fill_date を記録）。

- 注文管理 / 再整合
  - OrderRecord（状態遷移ロジック）を実装（src/kabusys/execution/order_record.py）。
    - 状態列挙 OrderState と許可遷移テーブル、InvalidStateTransitionError を定義。
    - transition_to により状態遷移と付随フィールド（broker_order_id、filled_qty 等）を安全に更新。

  - OrderManager 実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id 重複チェック（DB とレコードレベル両方）、client_order_id は uuid4。
    - send_order: 2相永続化フロー（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）。
      - OrderRejectedError / OrderSentPendingError の扱いを明確化。OrderSentPendingError は broker_order_id を保存して再スロー。
      - クラッシュ耐性（途中クラッシュ時に Reconciliation で回復可能となる設計）。
    - sync_order: broker 側ステータス照合による同期（部分約定更新の差分反映、OrderSent→Filled のケースで OrderAccepted を経由して遷移）。
    - cancel_order: 終端状態のキャンセル不許可チェック、broker_order_id があれば broker API を呼びキャンセルし DB を更新。

  - Reconciler / RiskManager / OrderRepository などコンポーネントを統合する設計（実装ファイルは参照）。

- ブローカークライアント（kabu）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期 REST クライアント実装、トークン管理（遅延取得と 401 リトライ）。
    - レスポンス JSON パースエラー / タイムアウト / ネットワークエラーを BrokerAPIError に変換。
    - 429 は RateLimitError として扱う。
    - WebSocket 経由の push を想定した stream_push 呼び出し（存在しない場合は WebSocket スレッドをスキップ）。

- 監視 / DB 初期化
  - monitoring_db 初期化関数を呼び出すフローを追加（起動スクリプトと run_execution/run_monitoring で使用）。

- ロギング・プロセス優先度ユーティリティ（参照）
  - setup_logging と set_process_priority を起動時に呼び出す設計（外部モジュールから導入）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 仕様上の注意
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされます（パッケージ配布後の環境でも CWD に依存しない設計）。
- PyYAML が未インストールでも validate_config は実行可能だが、YAML 内容検証はスキップされ警告が出ます。
- ExecutionEngine のセッションタイミング（シグナル/ドレイン）は現行実装に従い固定されている（テスト時は直接メソッド呼び出しで代替可能）。
- PAPER_TRADING 時は paper 用 SQLite を使用して本番 DB とデータ分離を行う設計。
- kill.flag の挙動は設定（KILL_FLAG_CLEAR_ON_START）により起動時に自動クリアされる可能性があるため、本番では 0 を推奨。

--- 

将来的な変更はこのファイルに追記してください。
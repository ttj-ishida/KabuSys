# Changelog

すべての重要な変更はこの文書に記録します。これは Keep a Changelog の形式に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-23

### Added
- 全体
  - 初期リリース。KabuSys 自動売買システムの基盤モジュール群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 設定関連
  - 環境変数・設定管理モジュールを追加 (src/kabusys/config.py)。
    - .env ファイルの自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env の行パースは `export ` プレフィックス、クォート文字、エスケープ、インラインコメントを適切に処理。
    - Settings クラスを提供し、型付きプロパティ経由で各種設定へアクセス（例: `settings.jquants_refresh_token`, `settings.duckdb_path`）。
    - 環境値の検証（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` など）はプロパティで行い、不正値は ValueError を発生させる。

  - 対話式設定ウィザード CLI を追加 (src/kabusys/config_setup.py)。
    - `.env` の初期作成・更新を支援するウィザード。
    - 複数の設定項目定義（実行環境、J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、ログレベル、Kill Flag 設定など）を提供。
    - 既存 .env の読み込み、シークレットのマスク表示、選択肢チェック、保存確認機能を実装。
    - `.env` の書式を統一して生成（.env を Git にコミットしない旨のヘッダを含む）。

  - 設定検証 CLI を追加 (src/kabusys/validate_config.py)。
    - `.env` と `config/*.yaml` の起動前検証を行うユーティリティ。
    - 必須環境変数チェック（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック等を行う。
    - PyYAML が存在する場合は `config/*.yaml` のパース検証を行う（無ければ警告を出力してスキップ）。
    - `--strict` オプションで警告も失敗扱いにする機能を追加。

- 実行スクリプト
  - Execution エンジン起動スクリプト (src/kabusys/run_execution.py) を追加。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite を使用する（本番 DB と分離）。
    - プロセス優先度の設定、PID ファイル管理、停止フラグ検出、DB 初期化を実装。
  - Monitoring ポーリングスクリプト (src/kabusys/run_monitoring.py) を追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する仕様。
    - 停止フラグ検出、例外キャッチでのログ出力、接続クローズ処理を実装。

- 発注・実行関連
  - OrderRecord と状態遷移ロジックを追加 (src/kabusys/execution/order_record.py)。
    - 状態列挙 OrderState、許可遷移テーブル、状態遷移検証（InvalidStateTransitionError）を実装。
    - dataclass による注文レコード表現（client_order_id、signal_id、broker_order_id、filled_qty 等）。
    - transition_to メソッドで updated_at 自動更新およびオプションフィールド更新を実装。

  - OrderManager を追加 (src/kabusys/execution/order_manager.py)。
    - create_order/send_order/sync_order/cancel_order の外向き API を提供。
    - DuplicateOrderError を定義し、同一 signal_id のアクティブ注文重複を防止。
    - send_order はクラッシュ安全性を考慮した 2 相永続化フローを実装（OrderSent に遷移して DB 保存 → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移）。
    - OrderSentPendingError（発注保留）や OrderRejectedError のハンドリング、OrderSent のまま残るケースへの対処、sync_order による復旧ロジックを実装。
    - cancel_order は終端状態のチェックを行い、必要なら broker の cancel を呼ぶ。

  - ExecutionEngine を追加 (src/kabusys/execution/execution_engine.py)。
    - Signal Queue Pull 型の発注エンジン本体を実装。
    - セッションの時間管理（signal_send_start/end, market_close）に基づくシグナル処理と WebSocket push ドレインを実装。
    - Gate1（シグナルレベル）、Gate2（エグゼキューションレベル：レート制限・サーキットブレーカー）、Gate3（ドローダウン監視） の複数段階のリスク評価を統合。
    - size_multiplier による BUY 数量調整、重複注文スキップ、リトライや rate-limit 対応を実装。
    - 発注後の position_entries 追記（バックテスト整合を考慮して約定日は次営業日で記録）。
    - push 通知処理での同期(sync_order) と Gate3 評価、kill_switch による全注文キャンセルを実装。
    - kill.flag による起動拒否/自動クリア（KILL_FLAG_CLEAR_ON_START）処理、PID ファイル書き込みとクリーンアップを実装。
    - WebSocket ワーカー（broker が stream_push を持たない場合はスキップ）。

  - kabu station REST クライアントを追加 (src/kabusys/execution/kabu_client.py)。
    - httpx を用いた同期 API クライアント（将来的に AsyncClient へ切替可能な設計）。
    - トークン取得の遅延初期化と 401 時の自動再取得・リトライ処理。
    - HTTP エラーとタイムアウト、ネットワーク例外を BrokerAPIError / RateLimitError 等にマッピング。
    - kabu の注文状態コードを内部ステータスへ変換するマッピングを実装。
    - WebSocket push（stream_push）連携用の実装が想定された設計。

- ユーティリティ
  - ロギング設定やプロセス優先度設定ユーティリティが利用される（実装は別モジュール）。起動時に高優先度へ設定する呼び出しを組み込んでいる。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / 開発上の注意
- validate_config により本番環境（KABUSYS_ENV=live）では追加の警告チェック（LINE 設定、KILL_FLAG_CLEAR_ON_START）を行う。strict モードでは警告もプロセスを失敗扱いにできるため、CI 等での利用が想定される。
- ExecutionEngine と OrderManager はクラッシュ時の整合性（OrderSent レコード等）を考慮した設計になっている。Reconciliation により broker 側との突合せで状態回復を行う設計が組み込まれている。
- .env は機密情報を含むため、生成された .env を Git にコミットしないこと（config_setup でも注意書きを出力）。

---

今後のリリースではテストカバレッジ、エラーハンドリングの拡張、broker API の追加実装、監視・メトリクス収集の強化などを予定しています。
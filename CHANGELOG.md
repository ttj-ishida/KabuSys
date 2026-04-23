# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

- リリースはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム「KabuSys」の基礎となる設定管理、監視・発注エンジン、ブローカークライアント、注文状態管理等を実装しました。

### Added
- 環境変数・設定管理
  - Settings クラスを導入し、環境変数から各種設定値（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、環境種別など）を取得・検証する機能を追加（src/kabusys/config.py）。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出し、.env → .env.local を順にロード）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルのパース実装: export 構文、クォート（シングル/ダブル）内のエスケープ、インラインコメント処理に対応。

- 環境設定ウィザード CLI
  - 対話式ウィザードで .env を作成/更新する CLI を追加（python -m kabusys.config_setup）。各項目の説明、選択肢、シークレット扱い、デフォルト値をサポート（src/kabusys/config_setup.py）。
  - .env を書き出す際のテンプレートと注意書きを出力する機能を実装。

- 設定検証 CLI
  - .env と config/*.yaml の起動前検証を行う CLI を追加（python -m kabusys.validate_config）。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、環境種別（KABUSYS_ENV）やログレベルの妥当性チェック、DB パス（DUCKDB_PATH, SQLITE_PATH）の親ディレクトリ存在確認、YAML ファイルの存在・パース検証（PyYAML が無ければ警告）などを実施。--strict オプションで警告を FAIL 扱いにできる（src/kabusys/validate_config.py）。

- 実行スクリプト / デーモン機能
  - ExecutionEngine: Signal Queue 型の発注エンジンを追加（src/kabusys/execution/execution_engine.py）。発注ウィンドウ（例: 8:50–9:10）の処理、WebSocket push のドレイン処理（9:10–15:30）などのセッション制御を実装。
  - run_execution スクリプトを追加。プロセス優先度設定、PID ファイル書き出し、kill.flag の扱い（起動時のクリア挙動）や paper_trading 時の DB 分離などをサポート（src/kabusys/run_execution.py）。
  - run_monitoring スクリプトを追加。SystemMonitor のポーリングループを起動、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（src/kabusys/run_monitoring.py）。

- 注文管理・状態機械
  - OrderRecord: 注文状態（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）を表すデータモデルと状態遷移ロジックを実装。不正遷移時に InvalidStateTransitionError を送出（src/kabusys/execution/order_record.py）。
  - OrderManager: signal_queue からの発注フローを管理する高レベル API を実装。create/send/sync/cancel の各処理を担い、DuplicateOrderError の検出、send_order における二相永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 保存 → OrderAccepted への遷移）などクラッシュに強い実装を行った（src/kabusys/execution/order_manager.py）。
  - sync_order: broker 側の状態を取得してローカル状態を同期する処理を実装（部分約定の進行を考慮して差分更新）。OrderSent → Filled 等の直接遷移を扱うために OrderAccepted を経由する回復ロジックあり。

- ブローカークライアント
  - KabuStationClient を実装（同期 httpx ベース）。トークン取得、認証付きリクエストの自動リトライ（401 時のトークン再取得）、エラーハンドリング（429 レート制限、5xx サーバーエラー、タイムアウト/ネットワークエラー変換）を実装。kabu station の状態コードを内部ステータス（open/partial/filled/…）へマッピング（src/kabusys/execution/kabu_client.py）。
  - WebSocket push の受信機構（stream_push）を想定した integration ポイントを提供。

- 発注フローとリスク管理統合
  - ExecutionEngine における発注フローは Gate1（シグナル単位の検査）、Gate2（実行レベルの検査。レート制限・サーキットブレーカー対応）、Gate3（ドローダウン監視による kill_switch）を導入し、RiskManager と連携して安全性を高める設計を実装。
  - 発注時の API レイテンシ計測・監視 DB への記録機能を含む（監視 DB 書き込み失敗は警告で発注フローを継続）。

- 監視・データベース初期化
  - monitoring 用 SQLite と DuckDB の接続処理、監視 DB の初期化（init_monitoring_db）呼び出しを実装（run_monitoring / run_execution）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。

- その他ユーティリティ
  - ロギングセットアップ、プロセス優先度設定ユーティリティと統合（setup_logging, set_process_priority を各スクリプトで使用）。
  - __version__ をパッケージに追加（__init__.py: "0.1.0"）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 環境変数ファイル (.env) に関する注意喚起をウィザードで表示し、.env を Git にコミットしない運用を推奨。

---

開発者・運用者向けメモ:
- 本番環境での起動前に python -m kabusys.validate_config を実行して設定不備を検出してください（--strict で警告をエラー扱いにできます）。
- paper_trading モードでは SQLite の DB を本番から分離しているため、本番 DB を誤って上書きするリスクは低減されています。
- send_order の二相永続化や sync_order の設計はクラッシュ復旧と Reconciliation を意識した実装です。リコンシリエーション周りの動作は reconciler 実装に依存します。
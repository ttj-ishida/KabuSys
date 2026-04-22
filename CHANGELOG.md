CHANGELOG.md

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

0.1.0 - 2026-04-22
-----------------
リリース: 初回公開

Added
- 基本アーキテクチャと主要コンポーネントを実装。
  - ExecutionEngine: シグナル駆動の発注エンジンを実装。シグナル処理（8:50–9:10）→ WebSocket ドレイン（9:10–15:30）のセッション制御、PID ファイル、kill flag 処理、WebSocket ワーカースレッド、ポーリング・待機ロジックを含む。
  - OrderRecord / OrderState: 注文状態マシンと遷移ロジックを純粋ロジックとして実装（DB 非依存）。
  - OrderManager: OrderRecord と OrderRepository を組み合わせた外向き API（create/send/sync/cancel）を実装。クラッシュ耐性を考慮した send_order の 2 相的永続化（broker_order_id の先コミット）や OrderSentPendingError の扱いを実装。
  - Broker/KabuStation クライアント（KabuStationClient）: kabuステーション REST API 用クライアント（httpx ベース）。トークン管理（自動取得・401 再取得）とレスポンスエラーハンドリング、レート制限（429）等を処理。WebSocket push のストリーム受信を想定。
  - BrokerClientFactory / MockBroker の仕組みを想定した broker 抽象化を統合（実装の連携ポイントを用意）。
  - Reconciler / RiskManager（インターフェース連携）を ExecutionEngine に統合し、起動時のリコンシリエーション実行・Gate1/2/3 によるリスク制御を実現。
  - Monitoring: run_monitoring スクリプト（SystemMonitor ポーリングループ）を追加。MONITOR_POLL_INTERVAL で間隔上書き可能。監視は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定・環境管理
  - config モジュール: .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）、.env と .env.local の読み込み順序（OS 環境 > .env.local > .env）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを抑制可能。
  - .env パーサー: export プレフィックス、クォートされた値（バックスラッシュによるエスケープ考慮）、コメント処理に対応。
  - Settings クラス: 環境変数への安全なアクセスラッパ（必須変数の強制チェック、PAPER_FILL_MODE 等の列挙チェック、パス類の Path 化、環境判定ユーティリティ）。
  - config_setup CLI: 対話式ウィザードで .env を生成/更新するスクリプトを追加（項目の定義、既存 .env の読み込み、シークレットマスク、保存前の確認など）。
  - validate_config CLI: .env と config/*.yaml の起動前検証ツールを追加。--strict オプションで警告もエラー扱いにできる。PyYAML が無い場合は YAML 内容検証をスキップして警告を出す実装。

- DB / ファイルパス
  - DuckDB と SQLite を併用する設計を導入。Execution と Monitoring 用にパス設定（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を Settings 経由で管理。
  - ExecutionEngine 内で DuckDB を用いてシグナルと portfolio_targets の JOIN によるシグナル読み込み、position_entries の書き込みを実施。

- 運用性向上
  - stop_requested.flag / kill.flag / PID ファイルを利用した外部制御を整備。KILL_FLAG_CLEAR_ON_START による起動時の自動クリアオプションをサポート。
  - プロセス優先度設定ユーティリティ（set_process_priority）とログ設定ユーティリティを利用して実行時の挙動を安定化。
  - 監視 DB（MonitoringDB）へのトレードイベント記録フックを追加（発注のレイテンシや状態を記録、監視側で集計可能）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注意事項 / 実装上の挙動メモ
- validate_config はデフォルトで PyYAML の有無を検査し、未インストールの場合は YAML のパース検証をスキップして警告を出します。PyYAML を導入すると config/*.yaml の内容検証が有効になります。
- config モジュールの自動 .env 読み込みはプロジェクトルートが特定できない場合や KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されている場合はスキップされます。
- send_order の実装はクラッシュ復旧（Reconciliation）を考慮し、broker_order_id を先に永続化する二相風の手順を採っています。OrderSent のまま残る可能性があるため、reconciler / sync 系処理による復旧設計が必須です。
- PAPER_TRADING（ペーパートレード）実行時は専用の SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- ExecutionEngine の時間判定はローカルの時刻（datetime.now().time()）を使用します。テストでは内部メソッドを直接呼ぶことで制御可能です。

作者
- KabuSys チーム

（以降のリリースでは Added / Changed / Fixed / … のセクションを更新してください。）
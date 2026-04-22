# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョン: 0.1.0

---

## [0.1.0] - 2026-04-22

初回公開リリース。KabuSys の基本的な実行・設定・発注・監視の骨格を実装します。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョンを 0.1.0 に設定。

- 設定管理
  - src/kabusys/config.py
    - Settings クラスを実装し、環境変数経由で各種設定を提供（J-Quants、kabu API、LINE、DB パス、監視閾値、PID/Kill フラグ等）。
    - 自動 .env ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - .env 読み込みロジック: override/protected オプションを備え、OS 環境変数を保護。
    - .env の行解析を強化（export プレフィックスの対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
    - PAPER_FILL_MODE 等の値検証ロジックを実装（不正値は ValueError）。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット値はマスク表示、選択肢・デフォルト・説明付きで入力を促す。
    - .env の読み書き（既存値の読み込み、テンプレート出力）を実装。
    - 実行後に validate_config を推奨するメッセージを表示。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env および config/*.yaml の設定不備を起動前に検出する CLI を実装。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - プレースホルダ値（*_here / your_value）検出による警告。
    - KABUSYS_ENV や LOG_LEVEL の値検証。live モード時は追加の注意喚起（LINE 通知設定、KILL_FLAG_CLEAR_ON_START）。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック。
    - PyYAML 未インストールでもスキップ可能な YAML パースチェック。--strict オプションで警告も失敗扱いにできる。

- 実行スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動ラッパー。プロセス優先度設定・PID 書き込み・stop フラグ検出などを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番 sqlite_path を使用する設計。

- 発注エンジン / 実行ロジック
  - src/kabusys/execution/execution_engine.py
    - ExecutionEngine を実装。セッションフロー（シグナル処理 8:50-9:10、push ドレイン 9:10-15:30）を提供。
    - EngineConfig により target_date 等を指定可能。
    - Signal の読み込み（DuckDB）→ Gate1/2（リスクチェック）→ 発注→ position_entries 更新 → 監視 DB へのイベントログ、までのフローを実装。
    - WebSocket プッシュ受信用の別スレッド（_websocket_worker）と内部キュー（_push_queue）を備え、受信 push を処理して sync + Gate3 チェックを実行。
    - kill_switch 実装: 全 active 注文のキャンセル／ループ停止。
    - PID ファイル書き出し / kill.flag の起動時処理（KILL_FLAG_CLEAR_ON_START を考慮）。

- 注文状態機械と管理
  - src/kabusys/execution/order_record.py
    - OrderState 列挙と許容遷移テーブルを実装。
    - OrderRecord dataclass と transition_to() による遷移検証。InvalidStateTransitionError を導入。
  - src/kabusys/execution/order_manager.py
    - OrderManager を実装。create_order / send_order / sync_order / cancel_order の外向き API を提供。
    - create_order は signal_id の重複（active 注文）検出と DuplicateOrderError を実装。DB 側の部分ユニーク制約違反を変換。
    - send_order は「OrderCreated → OrderSent を DB に永続化」→ broker API 呼び出し→ broker_order_id を先に永続化→ OrderAccepted に遷移、という二相永続化フローでクラッシュ安全性を高める設計。
    - OrderRejectedError / OrderSentPendingError を適切に処理し、Pending ケースは DB に broker_order_id を残すことで後続の Reconciliation で復元可能に設計。
    - sync_order は broker API の状態取得に基づく状態同期と部分約定のフィールド更新を実装。
    - cancel_order はキャンセル不可状態のチェックと broker 側キャンセル呼出しを実施。

- ブローカークライアント (kabu station)
  - src/kabusys/execution/kabu_client.py
    - KabuStationClient を実装（同期 httpx ベース）。トークン管理（遅延取得・401 時再取得）を内包。
    - HTTP レスポンスの JSON パース失敗やネットワーク／タイムアウトを BrokerAPIError に変換。
    - 401（トークン切れ）時の再取得リトライ、429（レート制限）で RateLimitError を送出、5xx でサーバーエラー扱い。
    - kabu station の注文状態コードを内部ステータス（open/partial/filled/cancelled/rejected）へマップ。
    - WebSocket push の受信（websocket ライブラリ想定）に対応する設計（stream_push を持つ broker のみ利用）。

- 監視関連
  - run_monitoring/run_execution および ExecutionEngine からの監視 DB へイベント記録連携（monitoring_db 経由）。
  - monitoring の初期化ユーティリティ（init_monitoring_db）呼び出しを起動時に行うことでテーブル存在を保証。

### Changed
- 設計上の堅牢性向上
  - send_order の二相永続化により、クラッシュ時に broker_order_id を DB に残して Reconciliation で回復可能。
  - ExecutionEngine の起動時に kill.flag を検査し、KILL_FLAG_CLEAR_ON_START に応じて自動クリアするオプションを導入。
  - .env パースの振る舞いを厳密化（クォート内エスケープ、インラインコメントの扱い）して実運用での .env 設定ミスを低減。
  - settings の自動ロードで OS 環境変数を保護する protected 機能を導入。

### Fixed
- クラッシュ安全性に関する記載（設計）や例外処理の明確化（OrderSentPendingError の伝播・処理フローの明文化）。
- run_monitoring のポーリング間隔設定で 0 以下の不正値時にデフォルトへフォールバックするロジックを実装（ValueError を防止）。

---

今後の予定（例）
- Reconciler / RiskManager / BrokerAPIProtocol の追加実装・テストケース整備。
- WebSocket push の実装詳細（kabu station とのストリーミング）の改善・耐障害化。
- 単体テスト・統合テストの追加、ランタイム監視強化。

もし特定の変更点について詳細（該当ファイル、関数、例外動作など）を追記してほしい場合は教えてください。
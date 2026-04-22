# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-04-22

### Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」の基礎機能を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数/ファイル読み込み機能を追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可能）。
    - .env ファイルパースの強化：
      - export プレフィックス対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
      - インラインコメントの扱い（クォート無効時は直前が空白/タブの `#` をコメントと認識）。
    - 読み込み時の上書き制御（override / protected）をサポートし、OS 環境変数を保護。
    - Settings クラスを提供し、各種設定値（トークン・パスワード・DB パス・PID/Kill フラグ・閾値・環境値等）をプロパティ経由で安全に取得。PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。

- 設定支援ツール
  - 対話式 .env ウィザードを追加（src/kabusys/config_setup.py）。
    - 初期 .env の生成・既存 .env の更新を対話的に支援。
    - シークレット項目はマスク表示。選択肢・デフォルト表示・確認プロンプトを実装。
    - 保存時のテンプレート整形（.env ファイルの書式化）を行う。

- 設定検証ツール
  - 起動前の設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - プレースホルダ値の警告（`*_here` や `your_value` 等）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（許可値を明示）。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と、PyYAML があれば YAML パース検証（PyYAML 未インストール時はスキップして警告）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告をエラー扱いにできる exit コード出力。

- 実行エントリポイント
  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 常に「本番」sqlite_path を使用して監視 DB を初期化。
    - プロセス優先度設定、停止フラグ検出、例外時のログと継続処理、DB のクローズを実装。
  - 実行（Execution）プロセス起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV に応じて paper_trading 時は専用 SQLite（paper_trading 用）を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出、スレッドによるエンジン実行を実装。

- Execution エンジンと注文管理
  - ExecutionEngine を追加（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（発注ウィンドウ）、WebSocket push のドレインループ、kill.flag の扱い、PID ファイル管理、リコンシリエーション実行フローを実装。
    - Gate 1/2/3 による多段リスクチェック（signal レベル、実行レート制御、ポートフォリオドローダウン）を組み込み。Gate2 のレートリミットリトライ（最大3回）や circuit breaker の挙動を実装。
    - 発注成功／保留／失敗時のハンドリング、position_entries の DuckDB への記録、監視 DB へのトレードイベント記録（監視 DB があれば）を実装。
    - WebSocket push を受け取って同期処理（sync_order）を呼び出す仕組みを実装。push による portfolios の再評価で Gate3 をチェックして必要なら kill_switch を発動。
    - kill_switch による全 active 注文のキャンセル処理と stop イベント管理を実装。

  - OrderRecord（状態マシン）を追加（src/kabusys/execution/order_record.py）。
    - 注文状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と許可遷移を表現。
    - 状態遷移検証と付随フィールド（broker_order_id, filled_qty, avg_fill_price, error_message）更新を実装。
    - 不正遷移時は InvalidStateTransitionError を発生させる。

  - OrderManager を追加（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id 重複検査（DB とメモリ両方）、uuid4 による client_order_id 付与、DB 保存（IntegrityError の特定変換）。
    - send_order: クラッシュ耐性を考慮した 2 相永続化フローを実装（OrderSent を先に永続化→broker 呼び出し→broker_order_id 永続化→OrderAccepted 更新）。OrderRejectedError の扱い、OrderSentPendingError（注文番号は発行されたが約定待ち）の特別扱い。
    - sync_order: broker 側ステータス取得によりローカル状態を同期。部分約定で filled_qty/avg_price のみ更新するケースに対応。OrderSent→Filled/Partial の直接遷移不可を補正して OrderAccepted を経由する処理。
    - cancel_order: 終端状態のキャンセル禁止チェック、broker 側キャンセル呼び出し、Cancelled への遷移。

- ブローカークライアント（kabuステーション）
  - KabuStationClient を追加（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期 REST クライアント実装（将来的に AsyncClient へ移行可能な設計）。
    - トークン取得の遅延初期化と 401 時の自動再取得＋リトライ。
    - レスポンス JSON の安全なパース、Timeout / RequestError の BrokerAPIError 変換、429 を RateLimitError として扱う。
    - kabu ステーション側の注文状態コードを内部ステータス ("open"/"partial"/"filled"/"cancelled"/"rejected") にマッピング。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数ファイル (.env) を絶対に Git に含めない旨をウィザードで明示（config_setup.py）。
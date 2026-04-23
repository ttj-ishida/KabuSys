# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージの __version__ = "0.1.0" に合わせています。

## [0.1.0] - 2026-04-23

### Added
- 全体
  - 初期リリース: 自動売買システム KabuSys の基礎機能群を追加。

- 設定 / 環境変数管理
  - src/kabusys/config.py
    - .env ファイルの自動ロード機能を実装（優先度: OS 環境変数 > .env.local > .env）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
    - .env のパース処理を実装（export プレフィックス対応、クォート内エスケープ、インラインコメントの扱いを考慮）。
    - _load_env_file で OS 環境変数を保護する protected 引数を導入（.env.local が OS 環境を上書きしない）。
    - Settings クラスを追加し、環境変数から各種設定値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン等）を取得する API を提供。
    - Settings 内で KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の値検証を行い、不正値の場合は ValueError を送出。
    - デフォルト値（DB パス、Kabu API の base url 等）を設定。

- 設定支援 CLI
  - src/kabusys/config_setup.py
    - .env を対話的に生成・更新するウィザードを実装。
    - 設定候補項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン, LOG_LEVEL 等）とデフォルト・選択肢を用意。
    - 既存 .env 読み込み、シークレット項目のマスク表示、保存確認を実装。
    - .env ファイル書き出しテンプレートを提供（Git にコミットしない旨のヘッダ付き）。
    - CLI エントリポイント (python -m kabusys.config_setup)。

- 設定検証ツール
  - src/kabusys/validate_config.py
    - 起動前に環境設定（.env / 環境変数 / config/*.yaml）を検証する CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）とプレースホルダ検出。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検査、live 環境時の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - DB パス (DUCKDB_PATH, SQLITE_PATH) の親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml の存在確認と PyYAML を用いたパースチェック（PyYAML 未インストール時は検証スキップ）。
    - --strict オプションで警告も FAIL 扱いにする機能。
    - CLI エントリポイント (python -m kabusys.validate_config)。

- 実行 / 監視スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。paper_trading 環境では別 SQLite（paper_trading.db）を使用して本番 DB と分離。
    - PID / stop フラグ管理、プロセス優先度設定、監視 DB 初期化を含む起動処理。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する点を明示。

- 発注周り（Execution）
  - src/kabusys/execution/order_record.py
    - 注文状態を表す OrderState 列挙型と、許可される状態遷移テーブルを実装。
    - OrderRecord データクラスを追加し、状態遷移検証（transition_to）と更新時刻更新を提供。無効遷移時は InvalidStateTransitionError を送出。
  - src/kabusys/execution/order_manager.py
    - OrderManager を実装。signal からの注文作成（create_order）、送信（send_order）、同期（sync_order）、キャンセル（cancel_order）を提供。
    - create_order: 同一 signal_id のアクティブ注文重複検出（DuplicateOrderError）。DB 側の部分ユニーク制約違反を DuplicateOrderError にマッピング。
    - send_order: 「OrderCreated → OrderSent を先に永続化」してから broker API 呼び出しを行う 2 相永続化パターンを導入（クラッシュ耐性強化）。
    - OrderRejectedError / OrderSentPendingError の扱いを明確化。OrderSentPendingError は broker_order_id を永続化した上で再送出。
    - sync_order: broker 側の状態を取得して DB と同期するロジック（状態遷移ルール・部分約定時のフィールド更新を考慮）。
    - cancel_order: 終端状態ではキャンセル不可とし、broker 呼び出しと状態更新を行う。
  - src/kabusys/execution/execution_engine.py
    - ExecutionEngine を実装。シグナル処理ループ（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）を管理。
    - Gate 1（シグナルレベル）、Gate 2（実行レベル、レート制限・サーキットブレーカー）および Gate 3（ドローダウン監視）による多段のリスク制御を実装。
    - Gate 2 のレート制限は最大 3 回のリトライを行い、サーキットブレーカーオープン時はシグナルループ停止。
    - 発注成功/保留/失敗の流れをロギングし、position_entries（DuckDB）への記録（BUY はエントリー、SELL はクローズ）を実装。
    - push ハンドリングでは broker_order_id から client_order_id を解決して sync_order を呼び、同時にポートフォリオ評価で Gate 3 をチェック。
    - kill_switch: 全ループ停止とアクティブ注文一括キャンセル処理を実装。外部から stop() で呼べる。
    - WebSocket ワーカーを用意し、broker が stream_push を持たない場合はスキップ。
    - セッション起動時に kill.flag の既存を検査し、KILL_FLAG_CLEAR_ON_START 設定に応じて起動可否/自動クリアの挙動を実装。
    - PID ファイルの生成・削除を実装。

  - src/kabusys/execution/kabu_client.py
    - KabuStation REST API クライアント（同期 httpx ベース）を実装。
    - トークン取得（/token）を遅延取得し、401 発生時に自動で再取得して 1 回リトライする仕組みを追加。
    - HTTP ステータスコードに応じた例外マッピング（401 → 認証エラー、429 → RateLimitError、5xx → BrokerAPIError）。
    - kabu station の注文状態コードを内部ステータスにマップするテーブルを追加。
    - websocket を用いた push 処理の基盤（websocket 依存で stream_push 呼び出しを想定）。

- 監視
  - src/kabusys/monitoring/*（参照のみ、実実装は別ファイルに依存）
    - 監視 DB 初期化関数 init_monitoring_db の利用箇所を追加（run_monitoring / run_execution）。

### Changed
- 設計方針・品質
  - 発注フローのクラッシュ耐性を強化（OrderSent を先に永続化する 2 相永続化戦略、broker_order_id 永続化によるリコンシリエーション対応）。
  - 設定の自動読み込みはプロジェクトルートを .git または pyproject.toml を基準に探索するため、CWD に依存しない実装に変更。
  - 実行・監視スクリプトでプロセス優先度を設定する呼び出しを追加（set_process_priority を使用）。

### Fixed
- なし（初期リリース）

### Removed
- なし（初期リリース）

### Security
- シークレット項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN）はウィザードでマスク表示され、.env の取り扱いに関する注意書きを .env 生成ヘッダに追加。

---

注:
- 一部のモジュール（例: execution 内の broker_api/ order_repository / reconciler / risk_manager、monitoring/system_monitor 等）は本 changelog の対象コードから参照されていますが、ここに含まれる変更は本リリースで確認できる実装の範囲に基づいて記載しています。
- pyproject.toml やパッケージ配布のメタ情報は本コードからは読み取れないため、リリース日には本書作成日（2026-04-23）を使用しています。必要に応じて日付を調整してください。
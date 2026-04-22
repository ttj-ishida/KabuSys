CHANGELOG
=========

すべての注目すべき変更を記録します。本ドキュメントは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- Unreleased: 現在進行中の変更（無ければ空）
- 各リリースは日付とともに分類（Added / Changed / Fixed / Security / Breaking Changes 等）

Unreleased
----------

- 現在未リリースの変更はありません。

0.1.0 - 2026-04-22
-----------------

Added
- 初期公開: KabuSys のコア機能を実装。
  - 環境 / 設定管理:
    - Settings クラス (kabusys.config) を導入。環境変数から各種設定を取得するプロパティ群を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, LOG_LEVEL 等）。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）により、.env/.env.local の自動読み込みを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env のパースロジックを強化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
  - 環境設定ウィザード:
    - config_setup CLI (python -m kabusys.config_setup)。対話的ウィザードで .env 作成・更新を支援。--env-file オプションで保存先を指定可能。
    - .env の読み書き（雛形ヘッダ、重要なキーの表示/マスク、保存前の確認）。
  - 設定検証:
    - validate_config CLI (python -m kabusys.validate_config)。起動前に .env と config/*.yaml の不備を検出。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）・KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML があれば実行、未インストール時はスキップ）など。
    - --strict フラグで警告を FAIL 扱いにできる。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の警告等）。
  - 実行スクリプト:
    - run_execution (python -m kabusys.run_execution): ExecutionEngine を起動するエントリポイント。paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - run_monitoring (python -m kabusys.run_monitoring): SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
  - 発注・実行エンジン:
    - ExecutionEngine 実装（kabusys.execution.execution_engine）。シグナル処理（8:50–9:10）、WebSocket push ドレイン（9:10–15:30）、kill.flag / PID ファイル管理、WebSocket プッシュ受信による同期処理をサポート。
    - EngineConfig により target_date 等を注入可能で、テスト用に個別メソッドを呼べる設計。
  - 注文管理:
    - OrderRecord（kabusys.execution.order_record）: 状態マシン（OrderState）と状態遷移ロジックを純粋なデータモデルとして実装。InvalidStateTransitionError を定義。
    - OrderManager（kabusys.execution.order_manager）: create/send/sync/cancel の高レベル API を実装。DuplicateOrder の検出（signal_id の DB 部分ユニーク）や send_order の二相永続化戦略を導入してクラッシュ時の回復性を高める。
    - sync_order では broker からのステータスをマッピングし、部分約定の増分更新をサポート。
    - キャンセル不可能状態の定義（Filled を含む）により誤ったキャンセルを防止。
  - ブローカークライアント:
    - KabuStationClient（kabusys.execution.kabu_client）: httpx を用いた同期 REST クライアント実装。
      - トークン取得（/token）を遅延取得かつ 401 発生時に再取得してリトライする仕組み。
      - レスポンス JSON のパースを厳格化し、HTTP ステータスに応じた例外（RateLimitError など）を投げる。
      - WebSocket push の受信（stream_push 想定）に対応するフック（_websocket_worker 経由）。
  - リスク管理 / Reconciliation / 監視連携:
    - ExecutionEngine と組み合わせて Gate1/Gate2/Gate3 の考え方を導入（リスクチェック、レートリミット / サーキットブレーカーへの対応、ポートフォリオ価値チェックでの kill_switch 発動）。
    - 監視 DB へのトレードイベント記録インタフェースを用意（monitoring_db 経由）。
  - インフラ周り:
    - DuckDB / SQLite を併用。duckdb は分析・シグナル取得に利用、SQLite は監視/注文履歴に利用。
    - プロセス優先度設定フック（set_process_priority）とログ設定（setup_logging）を起動時に呼び出すよう統合。
    - stop_requested.flag / kill.flag / pid ファイルを使った外部制御をサポート。

Changed
- （初期リリースにつき該当なし）

Fixed
- （初期リリースにつき該当なし）

Breaking Changes
- Settings の一部プロパティは環境変数の不正値に対して ValueError を投げる設計になっている点に留意（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）。既存運用でこれらに不正な値が混在する場合は .env を修正してください。
- kill.flag の扱い:
  - 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START=1 のときのみ自動クリアして起動する（デフォルトは 0: 起動拒否）。運用スクリプトが kill.flag を用いている場合は設定を確認してください。

Security
- 特になし（ただし .env は絶対に Git にコミットしないことを README / ウィザードのヘッダで強く注意）。

Notes / Usage Hints
- 設定検証: python -m kabusys.validate_config（--strict オプションで警告をエラー扱い）
- 設定作成: python -m kabusys.config_setup（ウィザードで .env を生成）
- 実行:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
- YAML 内容検証は PyYAML がインストールされている場合にのみ行われます。PyYAML 未導入時はファイル存在チェックのみになります。

今後の予定
- async 対応（httpx.AsyncClient への置換）やテストカバレッジの拡充、Reconciler の詳細な実装と CLI 制御の強化を検討しています。
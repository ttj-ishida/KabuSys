CHANGELOG
=========

この CHANGELOG は Keep a Changelog 準拠の形式で、リポジトリ内の現行コードから推測して作成しています。

[0.1.0] - 2026-04-22
-------------------

Added
- パッケージの初期リリース相当の実装を追加。
- 設定関連
  - Settings クラスを追加し、環境変数からアプリケーション設定を取得する仕組みを提供。
  - .env 自動読み込み機能を実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env のパースを robust に実装（export プレフィックス対応、クォート文字列内のバックスラッシュエスケープ、コメントの扱いなど）。
  - PAPER_FILL_MODE（paper trading の fill モード）などのバリデーションを実装（有効値チェック）。
  - 各種パス（DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH など）を Path として扱うプロパティを実装。
  - 環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）の妥当性チェックを組み込み。
- 設定作成ウィザード
  - 対話式 CLI (python -m kabusys.config_setup) を追加。.env の生成・更新を支援。
  - デフォルト値やパラメータ説明、シークレット項目のマスク表示、既存 .env の読み込み・再利用に対応。
- 設定検証ツール
  - validate_config CLI (python -m kabusys.validate_config) を追加し、起動前に .env と config/*.yaml の不足や不正を検出する仕組みを提供。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在確認、PyYAML がない場合の YAML 検証スキップ、--strict モード（警告を FAIL 扱い）を実装。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。process priority の設定、DB 接続（paper_trading 時は paper 用 SQLite を使用）、PID ファイル管理、停止フラグ検出、スレッドでのエンジン実行/停止を実装。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。MONITOR_POLL_INTERVAL によるポーリング間隔上書き、監視用 DB の初期化を実装。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
- 発注エンジン / 実行ロジック
  - ExecutionEngine: シグナル読み込み、発注ウィンドウ管理（signal_send_start/ end / market_close）、WebSocket push ドレイン、push による同期処理、kill switch（全 active 注文キャンセル）などのセッション管理ロジックを実装。
  - EngineConfig により target_date 等を設定可能に。
- 注文周りのビジネスロジック
  - OrderRecord: 注文の状態 (OrderState) を列挙した状態機械と、状態遷移検証ロジックを提供（不正遷移時に InvalidStateTransitionError を送出）。
  - OrderManager: create/send/sync/cancel の外向き API を実装。　
    - create_order: signal_id の重複排除（DB の部分ユニークインデックスを考慮）と UUID による client_order_id 発番を実装（DuplicateOrderError）。
    - send_order: クラッシュ耐性を考慮した二段階永続化フロー（OrderSent を先に永続化→ broker 呼び出し → broker_order_id を保存 → OrderAccepted へ遷移等）を実装。OrderSentPendingError の扱い、OrderRejectedError の反映を実装。
    - sync_order: broker 側のステータス照合による状態同期と部分約定フィールド更新を実装。
    - cancel_order: 終端状態のキャンセル不可チェックと broker API 呼び出し後の Cancelled への遷移を実装。
- ブローカークライアント
  - KabuStationClient を実装（httpx を使用した同期 REST クライアント）。
  - トークン管理（遅延初期化、401 時の再取得とリトライ）およびエラー分類（RateLimitError、BrokerAPIError）を実装。
  - kabu ステーションの状態コード -> 内部 status へのマッピングを実装。stream_push（WebSocket）へのフックも想定。
- リスク / リコンシリエーション / 監視連携
  - ExecutionEngine と OrderManager の連携で Gate1/2/3 のチェックを呼び出す設計（RiskManager / Reconciler の存在を前提）。
  - 発注イベントを監視 DB に記録するフック（監視DB が設定されている場合）。
- DB 初期化
  - monitoring 用 DB 初期化 helper (init_monitoring_db) を run_monitoring/run_execution で利用。
- ユーティリティ
  - process_priority 設定、ログ設定セットアップ（setup_logging）を起動時に適用する流れを標準化。

Changed
- （初版のため差分情報はなし。実装方針や API を明記）

Fixed
- （初版のため差分情報はなし）

Notes / 実装上の重要点（利用者向け）
- .env はセキュリティ上 Git にコミットしないこと。config_setup のヘッダコメントでも注意喚起済み。
- validate_config は PyYAML が未インストールでも動作する（YAML 内容チェックはスキップされるがファイルの存在は警告される）。
- run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視データは本番 DB を参照する設計）。
- ExecutionEngine は kill.flag の存在を見て起動可否を制御。KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に kill.flag を自動クリアする挙動があるため、本番ではデフォルト 0 を推奨。
- OrderManager の send_order はクラッシュシナリオを考慮した永続化順序になっており、Reconciliation により不整合回復を図る設計。

今後の改善候補（推測）
- KabuStationClient の非同期 (httpx.AsyncClient) 対応や WebSocket 統合の改善。
- YAML のスキーマ検証（PyYAML + スキーマ）による config/*.yaml の内容チェック強化。
- 設定検証ツールでの自動修復オプションやより詳細な診断メッセージ。
- テストカバレッジの拡充（状態遷移、クラッシュ再現テスト、reconciliation の包括的テスト等）。

--- 

注: 本 CHANGELOG は提供されたソースコードの内容から推測して作成したものであり、実際のコミット履歴やリリース履歴を完全に再現するものではありません。必要であれば、この CHANGELOG を基に実際の git 履歴や担当者への確認を行い確定版を作成してください。
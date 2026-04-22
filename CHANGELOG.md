CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- （今後の変更をここに記載）

[0.1.0] - 2026-04-22
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- 設定管理
  - 自動 .env ロード機能を追加（プロジェクトルートの .git または pyproject.toml を探索して .env / .env.local を読み込み）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 環境変数パーサ実装: export 形式、クォート内エスケープ、行内コメントの扱い等に対応。
  - Settings クラスを追加し、環境変数経由で設定値（J-Quants トークン、kabu API パスワード、DB パス、PID / kill flag パス、しきい値等）を提供。
  - 必須取得メソッド _require により未設定時に明確なエラーを発生させる。

- 設定ウィザード CLI
  - src/kabusys/config_setup.py: 対話式ウィザードで .env を作成/更新する機能を提供。
  - シークレット項目のマスク表示、選択肢・デフォルト表示、既存 .env の読み込み・再利用、保存確認を実装。
  - .env 書き出し時のテンプレート（各カテゴリのコメント）を含む。

- 設定検証ツール
  - src/kabusys/validate_config.py: 起動前に .env と config/*.yaml の基本的妥当性を検査する CLI を追加。
  - 検査内容: 必須環境変数の存在とプレースホルダチェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けの追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の警告）。
  - --strict オプションで警告を FAIL 扱いにする挙動を実装。
  - 検査結果は (errors, warnings, infos) を返す validate() を提供。

- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - paper_trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - PID ファイル管理、stop_requested.flag による外部停止フラグ検出、プロセス優先度設定、logging 初期化を行う。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数で間隔上書き可（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する。

- 注文エンジン（Execution）
  - ExecutionEngine 実装（セッション管理、シグナル処理ループ、WebSocket push ドレイン、kill switch、PID ファイル管理）。
  - EngineConfig により target_date / 時間帯（発注開始・締切・終了）を設定可能。
  - シグナル処理: DuckDB からシグナルを読み込み、size_multiplier 適用、Gate1/2 のリスクチェックを実施して発注。
  - push ドレイン時に sync_order を呼び、Gate3（ドローダウン監視）で必要なら kill_switch を発動。
  - position_entries への書き込み（発注成功時のエントリ記録）を実装（DuckDB を利用）。

- 注文管理・状態機械
  - OrderRecord（純粋ロジック）: 注文状態列挙 OrderState と許可遷移表を実装。transition_to による遷移検証。
  - OrderManager:
    - create_order: signal_id による重複検査（部分ユニーク制約を考慮）と OrderCreated レコード生成。
    - send_order: クラッシュ耐性を考慮した 2 相永続化（OrderSent を先にコミットし、broker_order_id を保存してから OrderAccepted に遷移）と例外ハンドリング（OrderRejectedError、OrderSentPendingError の扱い）。
    - sync_order: broker からの状態取得でローカル状態を同期。部分約定の進捗更新をサポート。
    - cancel_order: 終端状態判定後に broker cancel を呼び、Cancelled に遷移。
    - DuplicateOrderError / InvalidStateTransitionError の定義。

- ブローカー API 抽象と kabu station 実装
  - BrokerAPIProtocol 等（API 抽象）はコード内で利用（詳細実装はモジュール内で）。RateLimitError 等の例外運用を想定。
  - KabuStationClient:
    - httpx 同期クライアントで kabu station REST API に接続。
    - トークン取得の遅延初期化、401 時のトークン再取得と再試行、429 のレート制限検知、500 系のサーバーエラー扱い等の堅牢なリクエスト処理を実装。
    - kabu のステータスコードを内部状態("open", "partial", "filled", "cancelled", "rejected") にマッピング。
    - WebSocket push（stream_push）を用いた push 処理の受け取りに対応（ExecutionEngine の websocket ワーカーと連携）。

- リスク管理・再照合（Reconciliation）設計（コアフローを追加）
  - RiskManager / RiskConfig（パラメータ例を Execution 側で指定）を利用する Gate チェック（Signal レベル、Execution レベル、Metrics／Gate3）を実装。
  - Reconciler を利用した起動時のリコンシリエーションフロー（ExecutionEngine 起動時に呼び出し、同期結果のログ出力）を追加。
  - Execution 側で API 成功/失敗カウントの記録や rate limit 再試行のロジックを実装。

- データベース周り
  - DuckDB と SQLite 両対応（DuckDB を分析・シグナル取得に使用、SQLite を監視/注文履歴に使用）。
  - monitoring_db.init_monitoring_db による監視 DB 初期化（起動時にテーブルを保証）。
  - 監視 DB へのトレードイベント記録フロー（監視失敗時は警告で継続）。

- ユーティリティ
  - プロセス優先度設定ユーティリティ（set_process_priority）や logging セットアップの利用により、起動時の環境整備を行う。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / その他
- config/*.yaml の内容検証は PyYAML の有無に依存する。PyYAML がない場合はパース検証をスキップして警告を出力する。
- 環境変数の既定値や有効値はコード内で明示（例: KABUSYS_ENV 有効値 development/paper_trading/live、LOG_LEVEL の候補など）。
- 本リリースはアーキテクチャと主要な実行フローの基盤を提供することを目的としています。今後、テストカバレッジの拡充、CLI の UX 改善、非同期化（httpx.AsyncClient）や追加ブローカー実装などを予定しています。
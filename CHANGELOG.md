CHANGELOG
=========

すべての重要な変更履歴はここに記録します。  
フォーマットは Keep a Changelog に準拠しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

Unreleased
----------
- なし（開発中の変更はここに記載してください）

0.1.0 - 2026-04-22
------------------

Added
- 基本機能の初期実装として KabuSys のコアコンポーネントを追加。
  - 環境設定/ロード
    - Settings クラスを実装。環境変数から設定を読み取るためのプロパティ群を提供（J-Quants / kabu API / LINE / DB パス /監視閾値など）。
    - settings = Settings() をモジュールレベルで公開。
  - .env 自動読み込み
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読込。
    - OS 環境変数を保護する仕組み（.env.local は上書き、ただし OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読込を無効化可能。
  - .env 読み込みの柔軟なパース実装
    - export KEY=val 形式対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメント取り扱い等を実装。
  - 環境設定ウィザード CLI（python -m kabusys.config_setup）
    - 対話式ウィザードで .env の初期作成/更新をサポート。
    - デフォルト・選択肢・シークレット入力・既存値の再利用をサポート。
    - .env 書き出しロジックを実装（テンプレートヘッダ付）。
  - 設定検証 CLI（python -m kabusys.validate_config）
    - .env と config/*.yaml の存在・基本妥当性を起動前にチェック。
    - 必須環境変数未設定の検出、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の検証、DB パス親ディレクトリ検査、PyYAML がない場合の YAML 検証スキップ、--strict モード（警告を FAIL 扱い）を実装。
  - 実行/監視用起動スクリプト
    - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、PID ファイル管理、kill flag の扱い、paper_trading 時の DB 分離を実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite パスを使用。
  - 発注サブシステム
    - OrderRecord: 注文状態の列挙（State Machine）と遷移検証を実装。allowed transitions を定義し、不正遷移で InvalidStateTransitionError を送出。
    - OrderManager: 外向き API を実装（create/send/sync/cancel）。クラッシュ安全性を考慮した二相永続化フロー（OrderSent 前後の扱い）、OrderSentPendingError の扱い、DuplicateOrderError の定義と DB 制約からの変換を実装。
    - ExecutionEngine: シグナル処理ループ（8:50–9:10）と push ドレイン（9:10–15:30）を実装。Gate1/2/3 によるリスクチェック、kill_switch による全注文キャンセル、WebSocket push の受信処理、position_entries の更新処理などを追加。
    - 複数補助コンポーネントの統合: BrokerClientFactory、OrderRepository、RiskManager、Reconciler などと連携する実行フローを実装。
  - kabu station クライアント（KabuStationClient）
    - httpx を使った同期 REST クライアントを実装。トークン取得の遅延初期化と 401 時の自動再取得・リトライを実装。
    - HTTP レスポンスの JSON パース失敗を BrokerAPIError に変換、429 を RateLimitError に変換、タイムアウト/ネットワークエラーを適切にラップ。
    - kabu ステータスコード → 内部ステータス ("open"/"partial"/"filled"/"cancelled"/"rejected") のマッピングを実装。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）および SystemMonitor の利用を追加。
  - ユーティリティ
    - プロセス優先度設定、ログセットアップ等のユーティリティを利用して起動一貫性を確保。

Changed
- ログ出力レベルと環境名の検証を Settings に追加。無効な値は ValueError を送出して早期検出できるようにした。
- 環境変数のデフォルト値・パス関連の標準化（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH 等）。
- ExecutionEngine のセッション管理:
  - 起動時に kill.flag を検査し、KILL_FLAG_CLEAR_ON_START=1 の場合は自動でクリアするオプションを追加。
  - PID ファイル書き出しをセッション管理の一部として実装。

Fixed
- .env の読み込みでファイルアクセス失敗時に警告を発するようにして、プロセスが静かに失敗するのを防止（warnings.warn）。
- OrderManager.create_order で SQLite の部分ユニークインデックス違反を DuplicateOrderError に変換し、データベースの制約違反を意味のある例外にマッピング。
- send_order フローで broker から注文番号が返ってきたが約定しないケース（OrderSentPendingError）を扱い、broker_order_id を保持して Reconciliation の対象にできるようにした。
- validate_config の YAML パース時、PyYAML がない場合は検証をスキップして警告を出すようにして、依存性がない環境でも CLI が実行できるようにした。

Security
- .env を絶対に Git にコミットしない旨を生成されるファイルヘッダに明記（config_setup の書き出しテンプレート）。

Notes / Usage
- 環境設定ウィザード:
  - 実行: python -m kabusys.config_setup
  - 生成後は python -m kabusys.validate_config で設定を検証することを推奨。
- 実行:
  - 監視プロセス: python -m kabusys.run_monitoring
  - エンジン（発注）プロセス: python -m kabusys.run_execution
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

今後
- 非同期 httpx.AsyncClient による非同期対応の検討（kabu クライアントの将来対応）。
- さらなるユニットテスト・統合テストの拡充（特にリコンシリエーション周り・クラッシュ復旧シナリオ）。
- モニタリング／アラートルーティングの強化（LINE 以外の通知エンドポイント対応など）。
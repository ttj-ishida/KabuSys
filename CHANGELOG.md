CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の改善
- Fixed: バグ修正
- Removed / Deprecated / Security: 該当なしの場合は省略

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-23
-------------------

Added
- プロジェクト初回リリース: KabuSys v0.1.0 を追加。
- 設定関連
  - Settings クラスを導入し、環境変数を型付きプロパティとして安全に取得できるようにしました。
    - 必須値取得時に未設定なら ValueError を送出する _require() を実装。
    - env/log_level/paper_fill_mode 等の値検証を行い、不正な値は明確なエラーに変換。
    - paper_trading 用の paper_sqlite_path を分離（本番 DB と完全に分離）。
  - .env 自動ロード機能を追加（プロジェクトルートの .env / .env.local を読み込み）。
    - OS 環境変数を保護する protected 上書きロジックを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装:
    - export KEY=val 形式やシングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
- 設定ウィザード CLI
  - config_setup.py に対話式ウィザードを追加。.env の初期作成・更新を支援。
  - シークレット項目はマスク表示、選択肢／デフォルト表示、確認プロンプト、.env 書き込み機能を提供。
- 設定検証 CLI
  - validate_config.py を追加。起動前に .env と config/*.yaml の不備をチェック。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値検証、DB パスの親ディレクトリ存在チェック等を実装。
    - PyYAML がインストールされていれば config/*.yaml の YAML パース検証を実行。
    - --strict オプションで警告を FAIL 扱いにできる。
- 実行・監視エントリポイント
  - run_execution.py を追加。ExecutionEngine を起動する CLI スクリプトを提供。
    - paper_trading 環境では mock 用の SQLite を使用し、本番 DB と完全分離。
    - PID ファイル、停止フラグ（stop_requested.flag / kill.flag）を扱う起動フローを実装。
    - プロセス優先度の設定、WebSocket push ドレイン、セッション時間管理（発注期間/市場終了）を実装。
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する点を明記。
- 注文処理コア
  - OrderRecord（データモデル＋状態遷移）を追加。
    - 明確な OrderState 列挙、許可遷移テーブル、遷移検証（InvalidStateTransitionError）を実装。
    - transition_to により updated_at を自動更新し、必要なメタ情報を安全に更新可能。
  - OrderManager を追加（外向き API）。
    - create_order：signal_id の重複検出（DB とメモリ両方）と DuplicateOrderError の導入。
    - send_order：クラッシュ耐性を考慮した 2 相永続化フローを実装（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）。
      - OrderRejectedError / OrderSentPendingError をハンドリング（pending ケースは broker_order_id を保存して例外を伝播）。
    - sync_order：broker 側のステータス取得→内部状態への同期（部分約定の進行に応じた更新を含む）。
    - cancel_order：終端状態チェックと broker cancel 呼び出し、および内部遷移処理。
- ExecutionEngine
  - Signal Queue Pull 型の発注エンジンを実装。シグナルの読み込み、Gate 1/2（シグナル/実行レベル）検査、発注、position_entries への記録、監視DB へのログ出力を行う。
  - WebSocket push を非同期に受け取り _push_queue を排他処理する設計を導入。
  - Gate3（ドローダウン監視）で NG の場合は kill_switch() を発動して全 active 注文をキャンセルする保護機構を実装。
  - リコンシリエーション（起動時に reconciler を実行）をサポート。
  - kill.flag の扱い（KILL_FLAG_CLEAR_ON_START による起動時自動クリアオプション）を導入。
- Broker クライアント（kabu station）
  - KabuStationClient を実装（httpx を用いた同期 REST クライアント）。
    - トークン取得の遅延初期化、自動再取得（401 時に再試行）を実装。
    - レスポンス JSON パース失敗を BrokerAPIError に変換。
    - 429（レート制限）/5xx（サーバーエラー）を専用例外に変換。
    - WebSocket push（stream_push）との統合を想定した設計。
    - kabu station の状態コードを内部ステータスにマッピングする定義を追加。
- 監視・DB 初期化
  - monitoring_db 初期化ロジック（init_monitoring_db）を run_monitoring/run_execution から呼び出すように統一。
- ログ・プロセス関連ユーティリティ
  - setup_logging / set_process_priority を想定して呼び出す箇所を追加し、起動時の可観測性と優先度制御を強化。

Changed
- .env の取り扱いポリシー整理
  - 自動ロード順序を OS 環境 > .env.local > .env として明文化し、.env.local による上書きをサポート。
- DB 接続ポリシー
  - 監視系（monitoring）は環境にかかわらず本番 sqlite_path を使用するように仕様を明確化。
- 発注フローの堅牢化
  - send_order における永続化タイミングや pending 処理を明示してクラッシュ後の回復性を向上。

Fixed
- .env のパース挙動改善（コメント / クォート / export 対応）で実運用での誤解析を軽減。
- validate_config において PyYAML 未導入時は YAML 内容検証をスキップしつつ警告することで、環境に依存した検証失敗を回避。

Notes / Usage
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit code 1）
- 実行:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- 開発者向け:
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

開発中の既知制限 / 今後の改善候補
- KabuStationClient は同期 httpx.Client を使用。将来的に async 対応（httpx.AsyncClient）へ変更する余地あり。
- 一部のエラーハンドリング（細かな BrokerAPIError の分類やリトライ戦略）は運用実績に応じて調整予定。
- config/*.yaml の詳細スキーマ検証は現状 PyYAML の安全パースのみ。Schema バリデーションの追加検討。

---
Changelog
=========
すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[0.1.0] - 2026-04-23
-------------------

Added
- 初回リリース。KabuSys の基本機能一式を実装。
- 環境/設定管理
  - .env 自動読込機能を実装（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - .env / .env.local の読み込み順と上書きルール（OS 環境変数を保護）を実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 行パーサーを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの解釈に対応）。
  - Settings クラスを提供し、環境変数から型安全に設定値を取得できるプロパティ群を実装（API トークン、DB パス、PID/KILL フラグ、閾値、環境 / ログレベル等）。
  - 必須設定未提供時は明示的に ValueError を送出する _require() を実装。

- 設定作成ウィザード
  - 対話式 CLI (kabusys.config_setup.run_wizard) により .env の初期作成・更新を支援。
  - シークレット値は表示時にマスク、デフォルト値と選択肢をサポート。
  - .env のテンプレート書き込み機能を実装（書き込み時に注意文やセクション付き）。

- 設定検証ツール
  - kabusys.validate_config: 起動前に環境変数や config/*.yaml の不備を検出する CLI を実装。
  - 必須環境変数チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェックを実装。
  - PyYAML が存在すれば config/*.yaml をパースして内容検証、未インストール時は警告を出してスキップ。
  - --strict フラグで警告を FAIL 扱いにできる exit コード制御を実装。

- 実行 / 監視ランナー
  - run_execution スクリプト: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、PID ファイル管理、stop フラグ監視、paper_trading 用 DB 分離などを実装。
  - run_monitoring スクリプト: SystemMonitor のポーリングループ。MONITOR_POLL_INTERVAL 環境変数で間隔を指定可能。監視は本番 sqlite_path を使用（環境に依らず）。
  - 両スクリプトで duckdb / sqlite を使用した DB 接続処理を整備。

- 発注エンジン / 注文管理
  - ExecutionEngine: シグナル処理（発注窓: 8:50–9:10）、push ドレインループ（9:10–15:30）、WebSocket push の取り込み、position_entries 書き込み、Gate1/2/3 によるリスク検査、kill_switch 機構を実装。
  - ExecutionEngine は Reconciler による起動時リコンシリエーションを呼び出すフックを持つ。
  - ExecutionEngine は PID/kill.flag の扱い（起動時クリアポリシー: KILL_FLAG_CLEAR_ON_START）をサポート。

- 注文状態機構（Order State Machine）
  - OrderRecord dataclass を実装。状態列挙 OrderState と許容遷移を定義。
  - transition_to による遷移検証と更新時刻自動更新を実装。無効遷移は InvalidStateTransitionError を送出。

- OrderManager
  - create_order / send_order / sync_order / cancel_order の外向き API を実装。
  - send_order はクラッシュ耐性を考慮した2相永続化（OrderSent 保存 → broker 呼び出し → broker_order_id 保存 → OrderAccepted へ遷移）を実装。
  - OrderSentPendingError / OrderRejectedError の取り扱いに対応。DuplicateOrderError を導入（同一 signal_id の active 注文重複を防止）。
  - sync_order は broker 側ステータスを照合して部分約定や終端遷移を反映。状態が同じでも filled_qty / avg_fill_price の更新を検出して保存。

- ブローカークライアント（kabuステーション）
  - KabuStationClient を実装（同期 httpx を利用）。トークン取得、401 時の自動再取得、HTTP タイムアウト・ネットワークエラーを BrokerAPIError に変換。
  - レスポンス JSON パース失敗の明示的扱い、429 の RateLimitError マップ、500 系は BrokerAPIError として扱う実装。
  - WebSocket/stream_push による push 処理フックを想定（stream_push を持たない broker の場合は警告してスキップ）。

- モニタリング
  - 監視DB初期化（init_monitoring_db）との連携。発注イベントを監視DBへログ記録するフックを ExecutionEngine に実装（監視DB 書き込み失敗時は警告して処理継続）。

- その他ユーティリティ
  - logging_setup, process_priority と連携するフローを統合。
  - duckdb を用いたシグナル/portfolio_targets の読み取りと position_entries 操作を実装。
  - Paper Trading 用の DB 分離（PAPER_TRADING_SQLITE_PATH / paper_sqlite_path）や PAPER_FILL_MODE の妥当性検査を実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- .env ファイルは絶対に Git にコミットしない旨をテンプレートに明記。

Notes / 想定・補足（コードから推測）
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ行い、未インストール時は YAML 構文チェックをスキップして警告する設計。
- ExecutionEngine の挙動（発注窓、ドレイン、kill_switch、リコンシリエーション等）は、ライブ運用を想定した堅牢性（PID ファイル・stop フラグ・クラッシュ復旧）を考慮した作りになっている。
- DB 周りは duckdb（分析/シグナル）と sqlite（監視・注文履歴）を役割分担して使用。
- .env パーサーは実運用でよくある記法（export、クォート、エスケープ、コメント）に細かく対応している。

今後の改善候補（推測）
- 非同期対応（httpx.AsyncClient への置換）やテスト用モックの拡充。
- YAML スキーマ検証の導入（PyYAML + スキーマ）による設定検証強化。
- より詳細な監視メトリクスや可観測性（メトリクスエンドポイント、Prometheus など）。

---
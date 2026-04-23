# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-23

初回公開リリース（コードベースの初期実装を反映）。主な追加・実装内容は以下の通りです。

### Added
- 全体
  - パッケージ初期バージョンを追加: `__version__ = "0.1.0"`。
  - 型注釈・ドキュメンテーション文字列を随所に追加し、可読性を向上。

- 設定管理
  - Settings クラスを実装し、環境変数から各種設定（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、KABUSYS_ENV など）を取得する統一インターフェースを提供。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。読み込み順序: OS 環境 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - .env ファイルのパース機能を実装:
    - export プレフィックスの対応、クォート文字（単一／二重）の内部エスケープ処理、インラインコメントの適切な無視処理などを考慮した堅牢な解析ロジック。
  - _load_env_file にて「override」「protected（OS 環境変数保護）」の概念を実装。
  - PAPER_FILL_MODE（paper trading の振る舞い）や各種閾値（CPU/MEM/DISK など）の取得プロパティを実装し、値検査（有効値チェック）を行う。

- CLI / 開発補助
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を実装。
    - 設定項目一覧（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）
    - 既存 .env 読み込み、シークレットマスク表示、選択肢・デフォルトの提示、確認プロンプト、ファイル出力テンプレートの生成。
  - validate_config.py: 起動前に設定不備を検出する検証 CLI を実装。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML が利用可能な場合の）パース検証、KABUSYS_ENV=live 時の追加ガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定等）。
    - --strict オプションで警告も FAIL として扱う。

- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。
    - paper_trading 環境向けに paper 用 SQLite DB を分離して使用。
    - PID ファイル管理、停止フラグファイル検出、プロセス優先度設定（high）、監視 DB 初期化（init_monitoring_db）などを統合。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検出、例外時のログ出力、リソースクリーンアップ。

- 実行系コア
  - execution/execution_engine.py: Signal Queue Pull 型の発注エンジンを実装。
    - セッション管理（signal_send_start/end、market_close）、WebSocket push のドレイン処理、PID 書き出し、kill.flag の処理（起動時とループ中）、Reconciliation の起動、WebSocket ワーカーの実装。
    - シグナル処理フロー: DuckDB からのシグナル読み取り、size_multiplier 適用、Gate 1（シグナルレベル）/ Gate 2（エグゼキューションレベル）/ Gate 3（ドローダウン監視）の統合。
    - 発注時の監視 DB へのイベントログ記録（監視 DB が設定されている場合）。
    - position_entries の更新（buy/sell に応じた処理）を実装し、fill_date は次の営業日にすることでバックテストと整合性を持たせる。

- ブローカー関連 / 注文管理
  - execution/order_record.py: OrderRecord のデータモデルと状態遷移ロジックを実装。
    - 明示的な OrderState 列挙、許可遷移マップ、transition_to による遷移検証（不正遷移は InvalidStateTransitionError を raise）。
    - 更新時刻 updated_at の自動更新など。
  - execution/order_manager.py: OrderManager を実装し、OrderRecord（純粋ロジック）と OrderRepository（SQLite）を組み合わせた外向き API を提供。
    - create_order（重複検知: DuplicateOrderError）、send_order（2相永続化戦略: OrderSent の永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）、OrderSentPendingError の扱い、sync_order（broker 側ステータス同期待ち・部分約定更新）、cancel_order（キャンセル不可状態の検査）を実装。
    - クラッシュ時の整合性を考慮した設計（OrderSent のまま残るケースや broker_order_id の先保存による再同期対応）。

- broker client（kabu）
  - execution/kabu_client.py: KabuStationClient を実装。
    - httpx を使った同期 REST 呼び出し、レスポンス JSON パースラッパ、トークン取得（遅延初期化）と 401 時の再取得→再試行の実装。
    - HTTP ステータスに応じた例外変換（401 の再試行/エラー、429 を RateLimitError に変換、5xx を BrokerAPIError に変換など）。
    - websocket（push）処理のための stream_push 対応を想定（存在しない broker に対してはワーニングを出してスキップ可能）。

- 監視（monitoring）統合
  - monitoring 側の DB 初期化（init_monitoring_db）や SystemMonitor を実行するための接続確立ロジックを run_monitoring/run_execution に統合。
  - DuckDB と SQLite の両方を使用する設計（分析用と監視用の分離）。

### Changed
- 設定ロードの挙動
  - OS 環境変数を保護対象（protected）として .env/.env.local のロード時に上書きを防止する仕組みを導入。
  - .env のクォート/エスケープ・コメント処理を強化し、より多様な .env フォーマットに対応。

- DB パスの取り扱い
  - paper_trading 環境では paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番と DB を分離する挙動を明確化。

### Fixed / Robustness
- 発注と同期の信頼性向上
  - send_order における「broker_order_id の先保存」や OrderSent の扱いなど、クラッシュ後の再同期（Reconciliation）を容易にするための耐障害性向上策を実装。
  - sync_order において、同一状態でも部分約定の進行がある場合は filled_qty / avg_fill_price を更新するよう改善。

- エラーハンドリング
  - KabuStationClient の HTTP/ネットワーク例外を明確な BrokerAPIError / RateLimitError 等に変換して呼び出し側での扱いを容易に。
  - run_monitoring/run_execution のループ内での予期せぬ例外はログに例外情報を残して待機を継続するようにして監視の安定性を高めた。

### Security / Safety
- 本番ガード
  - validate_config と ExecutionEngine に本番用チェックを実装（KABUSYS_ENV=live の警告、本番での LINE 設定未設定や KILL_FLAG_CLEAR_ON_START=1 に対する警告、本番での kill.flag 挙動の拒否など）。
  - kill_switch による全 active 注文のキャンセル処理を実装し、重大なリスク検出時に自動停止できるようにした。

### Other
- ロギング・プロセス優先度
  - setup_logging と set_process_priority を起動フロー冒頭で呼ぶようにして、実行時のログ/優先度設定を統一。
- ドキュメント
  - 各モジュールに用途や使い方を説明する docstring を追加。

---

注: 上記はコード内容から推測してまとめた変更点・機能一覧です。実際の変更履歴（コミットメッセージや PR）の粒度とは異なる場合があります。必要であれば、各ファイルや機能ごとにさらに分解したエントリを作成します。
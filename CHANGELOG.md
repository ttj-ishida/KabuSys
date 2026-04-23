CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[Unreleased]
------------

（現在のリポジトリのスナップショットはバージョン 0.1.0 として初期リリースされています。
今後の変更はここに追記してください。）

[0.1.0] - 2026-04-23
--------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークのコア機能を追加。
  - CLI/ユーティリティ
    - config_setup: 対話式ウィザードで .env を生成・更新するツールを追加。
      - 各種設定項目（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH / LINE_* / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START など）を対話的に入力可能。
      - シークレット項目はマスク表示。既存 .env の読み込みと Enter による再利用をサポート。
      - 保存時のテンプレート出力と注意書き（.env を Git にコミットしない旨）を含む。
    - validate_config: 起動前に .env と config/*.yaml の設定不備をチェックする CLI を追加。
      - --strict: 警告も FAIL として扱い exit(1) にするオプション。
      - 必須環境変数の検証、KABUSYS_ENV / LOG_LEVEL の値チェック、DB パスや親ディレクトリの存在確認、config/*.yaml の存在確認・YAML パースチェック（PyYAML 非必須で未導入時はスキップ）などを行う。
      - 本番（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定の未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）を実装。
  - 設定管理
    - config モジュールを実装。Settings クラスを提供して環境変数からアプリ設定を取得可能。
    - .env 自動読み込み機能を実装（ルート検出: .git または pyproject.toml を探索）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - .env パーサ実装（_parse_env_line）:
      - export KEY=val 形式対応、クォート文字列のバックスラッシュエスケープ対応、インラインコメント処理（クォートなし時は '#' の前に空白があればコメントとして扱う）などをサポート。
    - Settings による入力検証:
      - env (KABUSYS_ENV)、log_level (LOG_LEVEL)、paper_fill_mode (PAPER_FILL_MODE) 等の値チェックを実装。無効値は ValueError を送出。
    - 本番 / ペーパートレード用の DB パス分離:
      - paper_sqlite_path を導入し、KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用するよう実装。
  - 実行スクリプト
    - run_execution: ExecutionEngine の起動スクリプトを追加。
      - プロセス優先度を高に設定し（set_process_priority）、PID/停止フラグ管理、SQLite / DuckDB への接続、スレッドによるエンジン実行と停止フラグ監視を実装。
      - paper_trading 環境では専用の paper_trading DB を使用して本番 DB と完全分離。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバックし警告を出す）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - Execution / Order subsystem
    - OrderRecord: 注文状態遷移を表す純粋ビジネスロジックのデータモデルを追加。
      - OrderState enum と許可遷移マップを定義し、不正遷移で InvalidStateTransitionError を送出する実装。
      - transition_to により updated_at を自動更新し、broker_order_id / filled_qty / avg_fill_price / error_message の更新をサポート。
    - OrderRepository / OrderManager / ExecutionEngine の主要フローを実装（DB 周りは既存モジュールと連携）。
      - OrderManager:
        - create_order: signal_id の同一 active 注文を検出して DuplicateOrderError を送出する仕組み。
        - send_order: 2相永続化の設計（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を保存 → OrderAccepted へ遷移）によりクラッシュ耐性を強化。
        - sync_order: broker 側の状態照合（get_order_status）で DB を最新化。部分約定の進行は差分更新。
        - cancel_order: キャンセル不可能な状態をチェックしてから broker cancel を実行。
      - ExecutionEngine:
        - シグナル読み込み（DuckDB）→ Gate1/2 のリスクチェック → 発注 → push ドレインと Gate3（ドローダウン監視）で kill_switch を実行するフローを実装。
        - Gate2 のレート制限は最大3回のリトライ、Circuit Breaker 発動時はシグナルループを停止。
        - 発注時の遅延計測を監視 DB に記録する仕組み（monitoring DB が渡されている場合）。
        - push イベント処理で broker_order_id から注文同期を実行し、portfolio valuation に基づく Gate3 チェックを行う。
        - kill_switch: 全 active 注文をキャンセルしループを停止する安全機構を実装。
    - Reconciler を呼び出した起動時のリコンシリエーションを実装（オプションで起動）。
  - Broker / KabuStation client
    - KabuStationClient を実装（httpx ベースの同期クライアント）。
      - トークン取得の遅延初期化、401 発生時のトークン再取得とリトライ処理を実装。
      - レスポンス JSON パース失敗 / タイムアウト / ネットワークエラーを BrokerAPIError に変換。
      - 429 を RateLimitError に変換。500 系は BrokerAPIError。
      - kabu station の状態コードを内部ステータス ("open"/"partial"/"filled"/"cancelled"/"rejected") にマッピング。
      - 将来の async 対応を考慮して設計（httpx.AsyncClient への切替で対応可能）。
    - WebSocket push の受信処理（stream_push が存在する broker のみ）を ExecutionEngine の ws スレッドで受け取りキューへ投入。

Changed
- 設計上の注意点・振る舞いの明文化:
  - ExecutionEngine の発注フローはクラッシュ時の状態回復（Reconciliation）を想定した永続化順序で設計。
  - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用する決定を採用。
  - .env の自動読み込みはプロジェクトルート検出に依存するため、配布後でも安定して動作するよう実装。

Fixed
- N/A（初期リリースのためバグ修正履歴はなし）。

Notes / その他
- config/*.yaml の自動生成スクリプトを示唆（validate_config の警告に
  python scripts/generate_config.py へ誘導）。
- .env の読み込みは OS 環境変数を保護する仕組み（protected set）を持ち、
  .env.local による上書きを許容する実装（テストやローカルのみの上書き用途に便利）。
- KILL_FLAG_CLEAR_ON_START のデフォルトは 0（本番推奨）。validate_config と Settings により本番での危険設定に対して警告/例外を出す。

今後の予定（例）
- 非同期対応の BrokerClient（httpx.AsyncClient）実装
- 監視・テスト補助用のモック broker 実装の整備
- config/*.yaml のスキーマ検証（PyYAML + JSON Schema 等）によるより厳密なチェック
- さらなるテストカバレッジ追加（状態遷移・リコンシリエーション・kill switch 等）

---

訳注: 上記はコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴やリリースノートと差異がある場合があります。
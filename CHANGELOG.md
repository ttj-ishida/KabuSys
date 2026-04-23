# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のリリース履歴:

## [0.1.0] - 2026-04-23
初回公開リリース — KabuSys 基本機能の第一版を追加。

### 追加
- パッケージメタ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

- 設定管理
  - 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート検出: .git または pyproject.toml によって自動でプロジェクトルートを特定。
    - .env 自動読み込み:
      - 読み込み順: OS 環境変数 > .env.local > .env。
      - OS 環境変数は保護され上書きされない。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパース機能:
      - export KEY=val 形式やシングル/ダブルクォート内のエスケープ、コメント処理に対応。
    - Settings クラス:
      - 必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）や各種パス/フラグ/しきい値のプロパティを用意。
      - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の値検証を実施（不正値で ValueError を送出）。
      - Paper Trading 用 DB パス分離（PAPER_TRADING_SQLITE_PATH 対応）。
      - kill flag 関連設定（KILL_FLAG_CLEAR_ON_START 等）。

- 設定ウィザード CLI
  - src/kabusys/config_setup.py を追加。
    - 対話的に .env を新規作成・更新するウィザードを提供。
    - シークレット項目は表示でマスク、選択肢/デフォルト値/説明付き。
    - .env の読み書きロジック（既存値を再利用、キャンセル時は保存しない）。
    - デフォルト項目群: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等。
    - 書き出しテンプレートには Git にコミットしない旨の注記を含む。
    - 実行例: python -m kabusys.config_setup

- 設定検証 CLI
  - src/kabusys/validate_config.py を追加。
    - .env および config/*.yaml の設定不備を起動前に検出する CLI。
    - 検査内容:
      - 必須環境変数の存在チェック、プレースホルダ（_here / your_value）検出で警告。
      - KABUSYS_ENV の妥当性検査（development / paper_trading / live）。
      - LOG_LEVEL の妥当性検査。
      - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（存在しない場合は警告）。
      - config/*.yaml の存在確認。PyYAML 未インストール時はパース検証をスキップして警告。
      - KABUSYS_ENV=live の際の追加ガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START=1 の警告など）。
    - --strict オプション: 警告も FAIL として exit(1) を返す。
    - 実行例: python -m kabusys.validate_config, python -m kabusys.validate_config --strict

- 実行スクリプト
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine の起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ（data/stop_requested.flag）検出に対応。
    - 実行例: python -m kabusys.run_execution
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視では環境にかかわらず本番 sqlite_path を使用。
    - プロセス優先度設定、停止フラグ対応。
    - 実行例: python -m kabusys.run_monitoring

- Execution / Order 管理
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態列挙型 OrderState と許可遷移表を実装。
    - transition_to による遷移検証と updated_at の自動更新。
    - 不正遷移時は InvalidStateTransitionError を送出。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - DB（OrderRepository）と OrderRecord を組み合わせた外向き API を実装。
    - create_order: signal_id の重複チェック（部分ユニークインデックス / DB 制約に対応）で DuplicateOrderError を送出。
    - send_order: 2 相永続化パターン（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新）を採用し、クラッシュ耐性を強化。
      - OrderRejectedError による拒否処理、OrderSentPendingError（注文IDはあるが約定しないケース）の取り扱いを実装。
    - sync_order: broker 側ステータス照合 → 状態同期（部分約定の更新はフィールド差分更新で対応）。OrderSent → Filled/PartialFill の場合は中間状態 OrderAccepted を経由して遷移。
    - cancel_order: 終端状態ではキャンセル不可とし InvalidStateTransitionError を送出、broker_order_id があれば API 呼び出しを行う。
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - シグナル読み込み（DuckDB）→ Gate1/2 によるリスク検査 → 発注フローの実装。
    - size_multiplier の適用（買いのみ）と最小単位処理（100株単位）対応。
    - レート制限（Gate 2）でリトライロジック（最大3回）を実装。Circuit Breaker 開放時はシグナルループを停止。
    - 発注時の監視（latency ロギング、monitoring DB へのイベント記録）に対応（監視 DB はオプショナル注入）。
    - push (kabu push) を受ける WebSocket ワーカーをスレッドで実装し、_push_queue を介して処理。
    - push 受信時は broker のポジションを参照して Gate 3（ドローダウン）を評価し、必要なら kill_switch を発動。
    - kill_switch: 全 active 注文のキャンセル処理とループ停止。cancel の失敗は種別ごとにハンドリング。
    - セッション全体のライフサイクル（8:50 発注開始 → 9:10 発注締切 → 15:30 セッション終了）を実装。起動時に reconciliation を実行可能。

- Broker / KabuStation クライアント
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx を用いた同期 REST クライアントを実装。
    - トークン遅延初期化と 401 発生時の自動再取得 & 1 回リトライ処理を実装。
    - レスポンスの JSON パース失敗やネットワークエラーを BrokerAPIError に変換。
    - 429 に対して RateLimitError を送出する実装。
    - kabu station の独自ステータスコードを内部ステータス ("open"/"partial"/"filled"/"cancelled"/"rejected") にマッピング。

- DB / 監視基盤
  - DuckDB（分析）と SQLite（監視/履歴）を併用する設計を採用。
  - run_monitoring / run_execution での DB 初期化・接続とクローズ処理を実装。
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）呼び出しを統合（冪等）。

- ユーティリティ
  - ロギング設定、プロセス優先度設定ユーティリティ呼び出しを起動スクリプトに統合。
  - stop_requested.flag / kill.flag / pid ファイルの取り扱いを共通化。

### 変更
- なし（初回リリースのため過去互換変更は無し）

### 修正
- なし（初回リリース）

### 既知の注意点 / マイグレーション
- .env の自動読み込みはプロジェクトルートが検出できない場合スキップされます（パッケージ配布後の挙動を想定）。
- PyYAML 非依存時は config/*.yaml のパース検証をスキップして警告のみ出力します。YAML 内容検証を行いたい場合は PyYAML をインストールしてください。
- KABUSYS_ENV=live を使用する際は LINE 関連の通知設定や KILL_FLAG_CLEAR_ON_START の値を必ず確認してください。validate_config によるチェックが用意されていますが、起動前に手動確認を推奨します。
- PAPER_FILL_MODE の不正値は Settings の参照時に例外を送出します（事前に validate_config 等で確認してください）。

---

今後の予定（例）
- Broker API のエラー再試行ポリシー強化
- 非同期 (async) クライアント対応（httpx.AsyncClient への置換）
- ユニットテスト・統合テストの追加、自動 CI の整備
- 監視アラートの強化（LINE 以外のチャネル追加）

もし CHANGELOG に追記してほしい重点項目（例えばセキュリティ関連、特定ファイルの変更点の詳細等）があれば教えてください。
# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の慣習に従っています。  

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主要コンポーネントの追加、設定管理・検証ツール、発注エンジン、監視プロセス、kabu station クライアント等を含みます。

### 追加
- 環境設定 / 設定管理
  - 自動 .env ロード機能
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み（OS 環境変数が優先）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト等で利用）。
    - .env 読み込みは既存 OS 環境変数を保護する仕組み（protected keys）。
  - 強化された .env パーサー
    - export 句対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い等に対応。
  - Settings クラス（型付きプロパティ）
    - J-Quants / kabu API の設定、DB パス、監視設定（PID/Kill Flag/閾値）、環境（KABUSYS_ENV）、ログレベル等をプロパティで提供。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証（不正な値は ValueError を投げる）。
  - config_setup CLI
    - 対話式ウィザードで .env の初期作成・更新を支援。シークレット項目はマスク表示。
    - キー一覧・デフォルト・選択肢・説明を備えた項目定義を提供し、.env のテンプレートとして保存する機能を搭載。

- 設定検証ツール
  - validate_config CLI
    - .env と config/*.yaml の起動前検証を実行。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）・プレースホルダ警告・KABUSYS_ENV/LOG_LEVEL 検証・DB パスの親ディレクトリ確認・config/*.yaml の存在と PyYAML によるパース検証（PyYAML 未インストール時はスキップ）・KABUSYS_ENV=live 時の追加ガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）。
    - --strict オプションで警告も失敗（exit(1)）扱いにできる。

- 実行関連スクリプト
  - run_execution
    - ExecutionEngine を起動するエントリポイント。プロセス優先度設定、PID ファイル管理、停止フラグ検出、DB 接続処理（paper_trading 時は専用 SQLite を使用）を実装。
  - run_monitoring
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。監視 DB は環境にかかわらず本番 sqlite_path を使用。

- 発注・実行エンジン
  - ExecutionEngine
    - Signal Queue ベースの発注フロー（シグナル処理、WebSocket push ドレイン、セッション制御）を実装。
    - Gate 1/2/3 によるリスクチェック（シグナルレベル、実行レベルのレート制御、ポートフォリオ指標チェック）。Gate 2 はリトライ/サーキットブレーカ動作を持つ。
    - kill_switch 実装: 全 active 注文のキャンセル（外部停止・Gate 3 NG 時等に発動）。
    - WebSocket push の処理ループ（broker が stream_push を提供する場合）と push に伴う同期処理（sync_order）。
    - 起動時にリコンシリエーション（Reconciler）があれば実行し、PID 書き込みと kill.flag の取り扱い（KILL_FLAG_CLEAR_ON_START による自動クリア）を行う。
    - DuckDB を用いてシグナルを読み込み、position_entries の更新（約定日を次営業日で記録）を行う。

  - OrderRecord（状態機械）
    - 注文の状態を表す OrderState 列挙と遷移定義を実装。許可されない遷移は InvalidStateTransitionError を発生させる。
    - transition_to により更新時刻自動更新・オプションフィールド更新をサポート。

  - OrderManager
    - create_order / send_order / sync_order / cancel_order の外向き API を実装。
    - create_order は同一 signal_id の active 注文をチェックし、重複時は DuplicateOrderError を送出。DB の一意制約違反も DuplicateOrderError に変換する。
    - send_order はクラッシュ安全性を考慮した二相永続化手順を実装（OrderSent の永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移等）。OrderSentPendingError を扱い pending 状態を DB に残して呼び出し元に伝播する。
    - sync_order は broker 側の状態を取得してローカル状態と同期。部分約定の進行はフィールド単位で更新。
    - cancel_order は終端状態をチェックして不許可なら例外を投げ、可能なら broker の cancel を呼んで Cancelled に遷移させる。
    - 発注成功時に monitoring DB（存在する場合）へ Sent イベントを記録するフックを提供。

- broker / API クライアント
  - KabuStationClient
    - httpx 同期クライアント実装。トークンの遅延取得・自動再取得（401 に対して再取得してリトライ）を実装。
    - レスポンス JSON パース失敗、ネットワーク・タイムアウトエラー等を BrokerAPIError に変換。
    - 429 (Too Many Requests) は RateLimitError にマッピング。
    - 注文状態コード -> 内部ステータスのマッピングを実装（open/partial/filled/cancelled/rejected 等）。
    - 将来的な async 対応は httpx.AsyncClient への差し替えで可能とする設計。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### セキュリティ
- config_setup の対話入力ではシークレット項目をマスク表示。
- .env を生成する際に「.env を絶対に Git にコミットしないこと」を明記したヘッダを出力。

### 注意事項 / 補足
- validate_config は PyYAML が未インストールだと YAML 内容検証をスキップします（警告）。YAML パース検証を行う場合は PyYAML をインストールしてください。
- run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用します（監視 DB の一貫性確保のため）。
- ExecutionEngine 起動時に既存の kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START=1 ならクリアして起動、そうでない場合は起動を拒否します。
- PAPER_FILL_MODE の不正な指定は Settings のプロパティで ValueError を投げます。
- .env の自動読み込みは OS 環境変数より下位に位置します。OS 側の環境変数を上書きしたくない場合は自動ロードを利用しないか、.env.local の挙動に注意してください。

### CLI（主な使用例）
- .env 作成 / 更新（対話式）
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする: python -m kabusys.validate_config --strict
- 実行プロセス起動
  - 実エンジン: python -m kabusys.run_execution
  - 監視ループ: python -m kabusys.run_monitoring

---

今後のリリースでは、テストカバレッジの強化、非同期クライアントの追加、より詳細な監視メトリクスの出力や UI/運用ツールの充実を予定しています。
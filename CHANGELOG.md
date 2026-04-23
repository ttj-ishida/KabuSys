# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリースノートには API 変更点・新機能・重要な挙動や既知の注意点を記載しています。

なお、本 CHANGELOG はコードベースの内容から推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装。

### Added
- 全体
  - パッケージの初期バージョンを追加。パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)。
  - DuckDB と SQLite を組み合わせたデータ保存/分析基盤の利用が可能。

- 設定管理・CLI
  - 環境変数・.env の自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml で検出し、.env / .env.local を自動ロード。
    - OS 環境変数を保護しつつ .env.local で上書き可能（override の挙動）。
    - 複雑な .env 行のパースに対応（export プレフィックス、クォート、エスケープ、インラインコメントの扱い）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - Settings クラスを追加し、アプリケーション固有の設定をプロパティ経由で提供（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_fill_mode 等）。
    - paper_fill_mode のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション。
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 複数の項目定義（実行環境、J-Quants トークン、kabu API パスワード、DB パス、LINE 通知設定、ログレベル、Kill Flag 挙動 等）。
    - 既存 .env 読み込み、シークレットマスク表示、確認プロンプト、保存機能を備える。
    - デフォルト値・選択肢表示、キャンセル・中断時の振る舞い。

- 設定検証ツール
  - 起動前に環境設定の不備を検出する CLI を追加（src/kabusys/validate_config.py）。
    - 必須/任意の環境変数チェック、プレースホルダ値の検出、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在とパース検査（PyYAML が無い場合はスキップ）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険な設定を警告）。
    - --strict オプションで警告も失敗（exit 1）として扱う。

- 実行スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - paper_trading 環境時に専用 SQLite（paper_trading.db）を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ(stop_requested.flag)の検出、スレッド管理。
  - 監視プロセス起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL によるポーリング間隔調整（デフォルト 60 秒、無効値は警告してフォールバック）。
    - 監視は環境に関係なく本番 sqlite_path を使用。

- Execution / 発注関連
  - ExecutionEngine 実装（src/kabusys/execution/execution_engine.py）。
    - シグナル（DuckDB）読み込み、Gate1/Gate2/Gate3 によるリスクチェック、発注ループ（8:50-9:10）と push ドレイン（9:10-15:30）の制御。
    - kill.flag に応じた起動拒否/自動クリアの挙動（KILL_FLAG_CLEAR_ON_START を考慮）。
    - WebSocket (kabu push) の受信を並列スレッドで扱い、受信ペイロードをキュー化して処理。
    - position_entries の更新（買い・売りの扱い差分、pending 注文の扱いについて整合性確保）。
    - 発注時の監視DBへのログ記録サポート（監視 DB が設定されている場合）。
  - OrderRecord（純粋ロジックとしての状態遷移モデル）を追加（src/kabusys/execution/order_record.py）。
    - OrderState 列挙、許可される遷移を明示、transition_to の検証と自動 updated_at 更新、無効遷移時の例外 InvalidStateTransitionError。
  - OrderManager（外向き API）を追加（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id 単位の重複検出（DB の部分ユニークインデックスとも整合）。
    - send_order: 2相永続化（OrderSent の永続化 → broker 呼び出し → broker_order_id の永続化 → OrderAccepted へ遷移）によるクラッシュ耐性向上。OrderRejectedError / OrderSentPendingError の扱い。
    - sync_order: broker 側のステータス照合と部分約定の進行反映（filled_qty / avg_fill_price の更新を含む）。OrderSent→Filled/PartialFill の場合は OrderAccepted を経由して安全に遷移。
    - cancel_order: 終端状態の判定とキャンセル API 呼び出し、状態遷移管理。
    - DuplicateOrderError の導入。
  - Reconciler / RiskManager 等のコンポーネントを組み合わせる設計を採用（src のほかのモジュールと統合することでリコンシリエーションやレート制限機構と連携）。

- Broker クライアント
  - KabuStationClient 実装（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期 REST クライアント。
    - トークン取得の遅延初期化および 401 時の自動再取得とリトライ実装。
    - レスポンス JSON パース失敗を BrokerAPIError に変換、タイムアウト/ネットワークエラーの詳細化。
    - HTTP 429 (rate limit) の専用例外 RateLimitError を識別。
    - （注）WebSocket の stream_push は websocket 等を用いて別スレッドで処理（実装の一部として存在）。

- 監視・DB 初期化
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）が利用される箇所を追加（run_monitoring / run_execution で呼出し）。

### Fixed
- 発注ワークフローのクラッシュ耐性を強化
  - send_order の 2 相永続化（broker_order_id を先に永続化してから状態遷移を確定）により、クラッシュ後のリコンシリエーションで照合可能に改善（Issue #32 に対する設計的対応として明示）。
- .env パーサーの堅牢化
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理や、インラインコメントの取り扱いを改善。

### Changed
- なし（初回リリース）

### Removed
- なし

### Security
- なし（既知の機密情報取り扱い: .env を絶対に Git にコミットしない旨を config_setup のヘッダに明記）

---

既知の注意点 / 推奨事項:
- .env にプレースホルダ（例: your_value, xxx_here 等）が残っていると validate_config が警告を出します。実運用前に必ず validate_config を実行してください。
- KABUSYS_ENV=live の場合、KILL_FLAG_CLEAR_ON_START=1 の設定は危険です（自動で kill flag をクリアしてしまうため）。
- PAPER_TRADING 環境は本番 DB とデータを分離する設計ですが、設定ミスにより本番 DB を上書きしないよう .env の確認を推奨します。
- PyYAML 未インストール時は config/*.yaml の文法チェックがスキップされます。YAML 検証を行うには PyYAML を導入してください。

もし差分（過去バージョンとの比較）やリリース日付の変更など追加の要望があれば教えてください。
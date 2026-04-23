# Changelog

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
リリース日: 2026-04-23

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-23

### Added
- 全体
  - 初期リリース。KabuSys 自動売買システムのコアコンポーネントを追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env ファイルパーサーは export 構文、クォート（シングル/ダブル）、バックスラッシュエスケープ、行中コメントの扱いに対応。
    - 必須値取得時に未設定なら ValueError を送出する `_require()` を提供。
    - Settings クラスで各種設定（トークン、API パスワード、DB パス、PID / kill flag パス、しきい値、env/log_level 判定、paper trading 用設定等）をプロパティとして取得可能。

- .env 作成ウィザード
  - 対話式設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - .env の読み取り/保存機能、既存値の再利用、シークレット値のマスク表示、入力候補・デフォルトをサポート。
    - KILL_FLAG_CLEAR_ON_START 等の項目を含むテンプレート出力を提供。
    - 保存後に設定検証のため `python -m kabusys.validate_config` を推奨するメッセージを出力。

- 設定検証 CLI
  - 起動前に .env / config/*.yaml を検証する CLI を追加（src/kabusys/validate_config.py）。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パースチェック、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START チェック）を行う。
    - --strict オプションで警告も失敗扱いにできる。
    - 出力は INFO/WARNING/ERROR を列挙し、終了コードで成否を示す。

- 実行系ランチャー
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、無効値時はフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop_requested.flag による外部停止・例外時のログ出力・リソースクローズを含む。
  - エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - paper_trading 環境時は専用の paper_trading DB を使用し本番 DB と完全分離。
    - stop_requested.flag と execution.pid の取り扱いを実装。

- Execution（発注）コア
  - ExecutionEngine を追加（src/kabusys/execution/execution_engine.py）。
    - シグナル取得（DuckDB）→ Gate1/2 のリスクチェック → 発注 → push ドレイン処理 → Gate3（ドローダウン）評価までの一貫したフローを提供。
    - セッションスケジューリング（signal_send_start/ end / market_close）、WebSocket push ハンドラ、PID ファイル管理、kill.flag の扱い、Reconciliation の実行（任意）を実装。
    - 発注成功/保留/失敗に応じたログ・モニタリング DB への書き込み（可能な場合）を行う。
    - position_entries の更新（BUY/SELL 処理、翌営業日での fill_date 記録）を含む。
  - EngineConfig dataclass によりターゲット日と時間設定を管理。

- 注文管理（Order）
  - OrderRecord（状態機械とデータモデル）を追加（src/kabusys/execution/order_record.py）。
    - 明示的な OrderState 列挙、許可遷移テーブル、InvalidStateTransitionError を実装。
    - transition_to により状態遷移の検証・タイムスタンプ更新・任意フィールド更新を行う。
  - OrderManager を追加（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id の重複検査 → DB 永続化。DB 側の部分ユニーク制約違反を DuplicateOrderError に変換。
    - send_order: 送信前に OrderSent を永続化 → broker API 呼び出し → broker_order_id を先に永続化（2 相永続化戦略）→ OrderAccepted へ遷移。OrderRejected/OrderSentPending の扱いと例外伝播を実装。
    - sync_order: broker 側ステータス取得→同一状態での部分更新、状態遷移の補助（OrderSent→Filled 等のための OrderAccepted 経由遷移）を実装。
    - cancel_order: 終端状態はキャンセル不可として InvalidStateTransitionError を投げる。broker_order_id があれば API cancel を呼ぶ。
    - DuplicateOrderError とキャンセル不可状態の定義を含む。

- ブローカー API と kabu station クライアント
  - KabuStationClient 実装を追加（src/kabusys/execution/kabu_client.py）。
    - httpx 同期クライアントを利用し、トークン取得を内部で管理（遅延取得・401 再取得ロジック）。
    - JSON パース失敗やネットワークエラーを BrokerAPIError / RateLimitError に変換。
    - 429 (rate limit) / 401 / 5xx 応答の扱いを実装。
    - WebSocket push (stream_push) をサポートする設計（存在しない場合はスキップ）。

- モニタリング / DB 初期化
  - monitoring DB 初期化ユーティリティを使用（init_monitoring_db）。監視用 sqlite 接続や DuckDB 接続の初期化をランチャーで行う（run_monitoring / run_execution）。
  - 監視ループは stop_requested.flag を確認して安全に終了。

- リスク管理連携
  - RiskManager（外部モジュール想定）との連携点を実装（Gate1/2/3）。
    - レート制限のリトライ、サーキットブレーカーでのループ停止、API 成功/失敗の記録等。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- .env ファイルは Git にコミットしないよう README/ウィザード内で注意喚起を出力。  
  （.env 作成ウィザードで「.env は絶対に Git にコミットしないこと」を明記）

### Notes / Upgrade instructions
- 初回導入時は以下を推奨:
  - python -m kabusys.config_setup で .env を生成・設定
  - python -m kabusys.validate_config で設定検証（本番時は --strict を推奨）
- 本番運用時の注意:
  - KABUSYS_ENV=live を設定する場合、LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を確認すること。
  - KILL_FLAG_CLEAR_ON_START はデフォルト 0（本番は 0 を推奨）。1 にすると起動時に kill.flag を自動クリアします（開発向け）。
  - PID / kill flag 用のディレクトリは自動作成されるが、適切なファイルパーミッション・監視を行ってください。

### Known issues
- 現時点で既知の重大な不具合はありません。運用中の環境差異や broker 実装に依存するエラーは発生し得ます（ログと監視 DB を用いて運用監視してください）。

---
この CHANGELOG はコードベース（src/ 以下）から推測して作成しています。リリースノートの追加・修正は必要に応じて行ってください。
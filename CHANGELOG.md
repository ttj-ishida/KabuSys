# CHANGELOG

すべての重要な変更点を記載します。形式は「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-22

### 追加
- 環境設定・検証関連
  - 対話式環境設定ウィザードを追加（python -m kabusys.config_setup）
    - .env の初期作成・更新を支援。デフォルト値、選択肢、シークレット入力に対応。
    - .env を生成する際のテンプレート出力を実装（.env に書き込む際に注意書き付き）。
    - --env-file で保存先を指定可能。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）
    - .env および config/*.yaml の存在や値の妥当性を起動前にチェック。
    - --strict オプションで警告を失敗扱いにできる。
    - PyYAML の未インストール時には YAML 検証をスキップして警告を出す。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）やプレースホルダ値の検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック等を実装。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認）。
- 設定読み込み・管理
  - 環境変数自動読み込み機構を実装（プロジェクトルートの .env → .env.local の順、OS 環境変数を保護）
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して検出。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサーを実装
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート囲み・バックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォートあり/なしでの違い）を実装。
    - 既存の OS 環境変数を保護する機能（protected set）。
  - Settings クラスを追加（kabusys.config）
    - アプリケーションで使用する環境変数をプロパティとして提供（トークン、API パスワード、DB パス、PID/KILL フラグなど）。
    - 値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。不正値は ValueError を送出。
    - paper_trading 環境向けの paper_sqlite_path を提供。
    - 設定インスタンス settings をモジュールレベルで公開。
- 実行スクリプト
  - ExecutionEngine 起動スクリプトを追加（python -m kabusys.run_execution）
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite DB を使用して本番 DB と分離。
    - プロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
    - stop フラグ（data/stop_requested.flag）検知により終了。
  - Monitoring ポーリングスクリプトを追加（python -m kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
- 発注・状態管理（Execution 系コア）
  - OrderRecord（状態機械のドメインモデル）を追加
    - OrderState 列挙体と許可される状態遷移テーブルを実装。
    - transition_to() で遷移検証と更新時刻自動更新。
    - 不正遷移時は InvalidStateTransitionError を送出。
  - OrderManager を追加
    - signal_id ごとの重複注文検出（DuplicateOrderError）。
    - create_order / send_order / sync_order / cancel_order の振る舞いを実装。
    - send_order はクラッシュ耐性を考慮した「OrderSent の永続化を先に行い、broker_order_id を DB に保存 → OrderAccepted に更新」という 2 相永続化パターンを採用。
    - OrderSentPendingError の扱い（注文番号は発行されるが約定しないケース）を考慮。
    - sync_order では broker の状態とローカル状態を照合し、部分約定や平均約定価格の更新を行う。Record の状態遷移ルールに従って間を経由する（例: OrderSent → Filled は OrderAccepted を経由）。
    - cancel_order はキャンセル不可状態の判定（Filled を含む）と broker への取消要求を実行。
  - ExecutionEngine（発注エンジン）を追加
    - シグナルループ（8:50–9:10）と push ドレインループ（9:10–15:30）を実装。
    - Gate1（シグナル単位のリスクチェック）、Gate2（実行時のレート制限・サーキットブレーカー）、Gate3（ドローダウン監視）を導入。Gate2 はリトライ / Circuit Breaker を考慮。
    - kill_switch 機構（全注文キャンセル・ループ停止）を実装。外部停止用 stop() を公開。
    - WebSocket push を受け取って _push_queue に投入し、sync / Gate3 評価を行うスレッドを持つ（broker が stream_push を持つ場合）。
    - position_entries テーブルへの約定記録処理を実装（buy / sell の扱い差分、次営業日での fill_date 計算）。
    - 発注の監視ログを監視 DB（MonitoringDB）へ記録するフックを追加。
- broker / API クライアント
  - KabuStationClient を追加（kabu station REST API 実装）
    - httpx.Client を使用した同期実装。認証トークン取得・保持（必要時自動再取得）を内部で管理。
    - 401 時はトークンを再取得してリトライする実装。
    - 429（レート制限）や 5xx を適切な例外に変換。
    - WebSocket push 用に websocket クライアント（stream_push を想定する）での受信処理フックを設計。
- 監視用 DB 初期化ユーティリティと SystemMonitor の実行スクリプトを追加（monitoring モジュールと run_monitoring スクリプトで利用）

### 変更（設計／既定値）
- デフォルトの DB パスや PID/KILL フラグのパスを固定化
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（デフォルト、本番用）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - PID_FILE_PATH: data/execution.pid（デフォルト）
  - KILL_FLAG_PATH: data/kill.flag（デフォルト）
- 自動 .env ロードの優先順位
  - OS 環境 > .env.local > .env の順で適用（OS 環境変数は protected され上書きされない）
- ExecutionEngine の挙動
  - 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START=1 なら自動クリアして起動、それ以外は起動拒否する動作を追加。
  - 実行中の stop フラグ / kill.flag 検出により安全に停止するロジックを強化。
- Execution の DB 書き込みや監視処理は失敗しても発注フローを中断しない（耐障害性を重視した設計）

### 修正
- .env のパースロジック改善
  - クォート内部のバックスラッシュエスケープやインラインコメント処理の不整合を修正。
  - export プレフィックスや空行・コメント行の扱いを改善。
- validate_config の診断情報を充実
  - プレースホルダ値（末尾が "_here" や "your_value"）の検出と警告。
  - PyYAML 未インストール時のフォールバック警告を追加。

### セキュリティ / 注意事項
- .env は絶対にリポジトリにコミットしないでください（config_setup の出力ヘッダに注意書きを付記）。
- KABUSYS_ENV=live は本番挙動となるため、validate_config や config_setup のメッセージに従って LINE 通知設定等を確認してください。
- KILL_FLAG_CLEAR_ON_START のデフォルトは "0"（本番での自動クリアは推奨しない）。本番で誤って "1" を設定すると kill_flag が自動クリアされ危険です。

### 既知の注記（運用上の挙動）
- send_order の中間クラッシュ時の回復は Reconciler（照合処理）で想定しており、OrderSent のまま残るケースを照合で補正する設計になっています（Issue #32 に対応する意図の実装）。
- MONITOR_POLL_INTERVAL が 0 または不正な値の場合はデフォルト（60 秒）にフォールバックします。

---

今後のリリースでは、テストカバレッジの追加、async 対応（httpx.AsyncClient への移行）、および broker/API の拡張（複数ブローカー対応等）を予定しています。
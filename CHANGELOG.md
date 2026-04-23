# CHANGELOG

すべての注目すべき変更点を記載します。本ファイルは Keep a Changelog の形式に従います。

## [0.1.0] - 2026-04-23

### 追加 (Added)
- 初回公開リリース。
- 環境設定・起動補助 CLI を追加
  - python -m kabusys.config_setup: 対話式ウィザードで .env を初期作成 / 更新可能。複数項目（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH / LINE_* / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START 等）を扱う。
  - python -m kabusys.validate_config: 起動前に .env および config/*.yaml の設定不備を検出する検証ツール。--strict オプションで警告も失敗扱いにできる。
- 設定読み込み・管理モジュールを追加
  - kabusys.config: .env 自動読込機能（プロジェクトルートの検出: .git または pyproject.toml を探索）、export 形式やクォート/コメントを考慮したパーサ、OS 環境変数保護（上書き制御）。
  - Settings クラスを提供: 環境変数から型変換された設定値を取得するプロパティ群（パス、閾値、KABUSYS_ENV 判定、PAPER_FILL_MODE 検証など）。
- 実行用スクリプトを追加
  - run_execution: ExecutionEngine を起動するエントリポイント。paper_trading 時は専用 SQLite を使用。
  - run_monitoring: SystemMonitor をポーリング実行するエントリポイント。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能。
- 実行エンジンと注文運用ロジックを実装
  - ExecutionEngine: シグナルループ（8:50–9:10）と push ドレイン（9:10–15:30）を含むセッション実行、WebSocket push の受信 / キュー処理、PID ファイル管理、kill.flag の扱い、リコンシリエーション呼び出し等。
  - OrderManager: 注文作成(create_order)、送信(send_order)、同期(sync_order)、取消(cancel_order) の高レベル API。DB 一貫性を考慮した 2 段階永続化フローとエラー種別の扱い（OrderRejectedError / OrderSentPendingError の処理）。
  - OrderRecord: 注文状態を表す状態機械（OrderState）と遷移検証。InvalidStateTransitionError を導入。
  - ExecutionEngine 内での Gate1/2/3 によるリスクチェック統合（signal レベルチェック、実行レベルチェック、ドローダウン監視）。
- ブローカ API 実装（kabu station クライアント）を追加
  - KabuStationClient: httpx を用いた同期 REST クライアント。トークン取得の遅延初期化、401 発生時のトークン再取得とリトライ、429（レート制限）や 5xx を専用例外に変換。WebSocket push（stream_push）を想定した受信フック設計。
- DB 初期化 / 監視関連
  - monitoring 用 DB 初期化関数 init_monitoring_db の利用。Monitoring は環境に依らず本番 sqlite_path を使用する旨を明記。
- ユーティリティ
  - .env 生成時にシークレットを伏せる表示、選択肢・デフォルトの提示、キャンセル処理、.env 書き込みテンプレートを提供。
  - MONITOR_POLL_INTERVAL の不正値対策（0 以下や文字列はデフォルトにフォールバック）。

### 変更 (Changed)
- .env 自動読み込みのポリシー:
  - デフォルトで OS 環境変数 > .env.local > .env の順で読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって自動ロードを無効化可能。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml が見つかった場合）のみ実行され、発行環境（パッケージ配布後）でも CWD に依存しない挙動になるよう設計。
- .env パース仕様の強化:
  - export キーワード対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメント取り扱いルールを明確化。

### 修正 (Fixed)
- 起動前検証（validate_config）の強化
  - 必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）の未設定検出とプレースホルダ判定（末尾が "_here" または "your_value"）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性検証とメッセージ出力。live 環境時の注意喚起チェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定検出）。
  - config/*.yaml ファイル存在確認と、PyYAML が利用可能な場合は safe_load によるパース検証（PyYAML 未導入時はスキップして警告を出力）。
- 注文フローの耐障害性向上
  - send_order の実装で、broker 呼び出し前に OrderSent を永続化し、その後 broker_order_id を先にコミットする 2 相的な永続化を行うことでクラッシュ後のリカバリ（リコンシリエーション）を容易に。
  - OrderSentPendingError の扱いを明確化（broker が注文番号を発行するが約定しない場合は broker_order_id を永続化して OrderSent のまま残す）。
  - sync_order での状態差分検出（同一状態でも filled_qty/avg_fill_price の変化は更新）を追加。
- ExecutionEngine の停止 / kill スイッチ挙動の明確化
  - kill.flag の検査タイミングを明示（起動前・ループ内）し、KILL_FLAG_CLEAR_ON_START=1 の場合は起動時にクリアして続行するオプションを追加。
  - セッション終了時に PID ファイルを確実に削除する処理を追加。

### ドキュメント / メッセージ改善 (Documentation)
- CLI の使い方や出力メッセージを日本語で整備（validate_config / config_setup / run_* の説明）。
- .env 書き込みテンプレートに注意文（.env を絶対に Git にコミットしない）を追加。

### セキュリティ (Security)
- .env 生成時にシークレット項目はマスクして表示。デフォルトで .env をリポジトリに含めない運用を推奨する注記を追加。

### 既知の制限 / 注意点 (Known issues / Notes)
- config/*.yaml の構文検査は PyYAML がインストールされている場合のみ実行される（未導入時はスキップして警告）。
- KabuStationClient の WebSocket 部分は broker 実装が stream_push をサポートする前提の実装で、未実装ブローカーは WebSocket スレッドをスキップする。
- PAPER_FILL_MODE の不正値は Settings.paper_fill_mode で ValueError を投げるため、呼び出し側での取り扱いに注意。

---

このリリースは初回の包括的な実装を含み、設定管理、起動スクリプト、注文フロー、監視、ブローカクライアント等の主要コンポーネントを備えています。今後のリリースではテストカバレッジの拡充、非同期化対応（httpx.AsyncClient など）、および外部依存の抽象化強化を予定しています。
# CHANGELOG

すべての変更は「Keep a Changelog」形式に従います。  
バージョニングは SemVer に従います。

## [0.1.0] - 2026-04-23

最初の公開リリース。KabuSys のコア設定管理、起動スクリプト、発注エンジンと監視ロジック、kabu station クライアントなどを含みます。

### 追加 (Added)
- パッケージ初期リリース (バージョン 0.1.0)。
- 設定管理
  - Settings クラスを実装し、環境変数から各種設定を取得する API を提供（J-Quants / kabuステーション / LINE / DB パス / PID/Kill flag /閾値など）。
  - .env 自動ロード機能を実装（プロジェクトルート検出：.git または pyproject.toml を基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - ロード優先順位：OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き防止）。
  - .env ファイルのパース実装：export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、行内コメントの扱いなど細かいルールに対応。
- 設定ウィザード CLI
  - python -m kabusys.config_setup による対話式 .env 生成/更新ウィザードを実装。
  - 各設定項目の説明・デフォルト・選択肢・シークレット表示（保存時はマスク）をサポート。
  - .env ファイルの読み書きロジックを提供 (.env テンプレートヘッダー含む)。
- 設定検証 CLI
  - python -m kabusys.validate_config による起動前検証ツールを実装。
  - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
  - --strict オプションで警告も失敗扱い（exit code 1）にできる。
  - PyYAML 未導入時は YAML 検証をスキップして警告を出す。
- 実行スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。paper_trading モードでは paper 用 SQLite を使用し、本番 DB と分離。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 発注サブシステム
  - OrderRecord: 注文状態を表す State Machine と遷移検証を実装。InvalidStateTransitionError を導入。
  - OrderManager: DB と OrderRecord を組み合わせた外向き API を提供（create_order / send_order / sync_order / cancel_order）。同一 signal_id の重複検出 (DuplicateOrderError) やクラッシュ対策を考慮した 2 段階永続化（OrderSent 前後の扱い）、OrderSentPending の取り扱いなどを実装。
  - ExecutionEngine: シグナル読み込み → Gate1/Gate2 を経て発注、WebSocket push のドレイン、Gate3（ドローダウン監視）による kill_switch 発動など、セッションフロー（8:50-9:10 シグナル処理、9:10-15:30 push drain）を実装。PID ファイル、kill.flag の扱い（起動時の既存 kill.flag チェックと KILL_FLAG_CLEAR_ON_START フラグ対応）を実装。
  - Reconciliation の呼び出し（存在する場合）や position_entries への書き込み（発注成功時の保有日管理）をサポート。監視 DB へのトレードイベントロギングを実装するフックあり。
- broker クライアント
  - KabuStationClient: kabu station REST API クライアントを実装（httpx 同期クライアント）。トークン取得を遅延初期化・自動再取得（401 時に再取得してリトライ）する設計。HTTP エラーやタイムアウトは BrokerAPIError / RateLimitError などにマッピング。WebSocket push（stream_push）を想定した push ハンドリングの土台を用意。
- モニタリング / プロセス運用
  - 起動時にプロセス優先度を設定するユーティリティ呼び出し（set_process_priority("high")）を run_execution / run_monitoring で実行。
  - 停止要求は data/stop_requested.flag ファイルで検知する仕組みを導入。

### 変更 (Changed)
- 設定の検証ロジックと Settings クラスで KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の許容値チェックを実装し、不正な値は ValueError を raise するようにした（早期検出）。
- .env の読み込みは配布後も安定動作するように __file__ ベースでプロジェクトルートを検出する実装に変更（CWD に依存しない）。

### 修正 (Fixed)
- 発注フローのクラッシュ耐性向上:
  - send_order のフローは DB に OrderSent を永続化してから broker 呼び出しを行い、broker_order_id は受信後に先に保存する「2 相永続化」パターンを採用。これによりクラッシュ時でも再照合 (Reconciliation) が可能。
  - OrderSentPending (注文番号はあるが約定しない状態) を明示的に扱い、永続化してから例外を伝播することで不整合を検出しやすくした。
- cancel_order は現在状態をチェックしてキャンセル不可能な状態は InvalidStateTransitionError を返すようにし、安全なキャンセル処理を確保。

### セキュリティ (Security)
- .env テンプレートに「.env を絶対に Git にコミットしないこと」という注意を明示的に追加。
- ウィザードでシークレット項目は表示時にマスク表示し、保存時も .env に平文で保存する旨をユーザーに明示（運用上の注意）。

### 既知の制限 / 注意点 (Known issues / Notes)
- config/*.yaml の内容検証は PyYAML (yaml パッケージ) がインストールされている場合にのみ実行され、未インストール時は検証をスキップして警告が出力されます。
- KabuStationClient は同期 httpx.Client を使用。将来的に非同期対応が必要な場合は httpx.AsyncClient への切り替えを検討してください。
- run_monitoring は環境にかかわらず本番 sqlite_path を使用します（設計上の意図）。paper_trading 用の分離は run_execution 側で行われます。
- PAPER_FILL_MODE の不正値は Settings.paper_fill_mode で ValueError を送出します。許容値は "instant" / "partial" / "never" / "reject"。

---

今後の予定（例）
- テストカバレッジの拡充（特に状態遷移、再試行・クラッシュケース）。
- KabuStationClient の WebSocket 実装の安定化と async 対応オプション。
- config/*.yaml のスキーマ検証（JSON Schema 等）導入検討。
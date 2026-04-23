# CHANGELOG

すべての注目すべき変更点を記載します。本ファイルは Keep a Changelog 準拠の形式で書かれています。

フォーマット:
- 追加: 新機能・新 CLI・API 等
- 変更: 既存機能の振る舞い変更
- 修正: バグ修正や堅牢性向上
（各項目はコードから推測して記載しています）

## [Unreleased]

(現在の差分はまだリリースされていません。)

---

## [0.1.0] - 2026-04-23

Added
- パッケージ初期版リリース。
- 設定管理
  - Settings クラスを追加。環境変数から設定値を取得し、各種プロパティ（J-Quants トークン、kabu API パスワード、DB パス、PID/kill flag パス、閾値設定、環境種別判定等）を提供。
  - 自動 .env 読み込み機能を追加（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装: export KEY=val 形式のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント処理など（細かなフォーマット差に耐える）。
  - _require() による必須環境変数チェック（未設定時は ValueError）。

- 環境設定ウィザード
  - python -m kabusys.config_setup により対話式で .env を作成・更新する CLI を追加。
  - 標準項目の定義と既存 .env 読み込み、シークレット値マスク表示、選択肢・デフォルト表示、書き込みヘッダ付き .env 出力を実装。
  - 保存前に設定内容確認を行い、保存キャンセル機能を備える。

- 設定検証ツール
  - python -m kabusys.validate_config により起動前に設定の妥当性を検証する CLI を追加。
  - 必須/任意環境変数チェック、KABUSYS_ENV の妥当性判定（development/paper_trading/live）、LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証を実装。
  - KABUSYS_ENV=live 時に追加の「本番ガード」チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定の警告）。
  - --strict オプションを追加（警告も FAIL 扱いで exit(1)）。

- 実行用スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。プロセス優先度設定、PID/stop flag の取り扱い、DB 接続 (SQLite / DuckDB)、paper_trading の DB 分離（paper_trading 用 SQLite を使用）を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能。monitoring は環境にかかわらず本番 sqlite_path を使用。

- Execution / 発注フロー
  - ExecutionEngine を実装。シグナル処理（8:50-9:10）と WebSocket push ドレインループ（9:10-15:30）を含むセッション制御。
  - EngineConfig により target_date / 時刻境界を設定可能。
  - 発注フローに Gate1（シグナルレベル検査）/ Gate2（エグゼキューションレベル検査）/ Gate3（ドローダウン監視）を導入。Gate2 はレート制限対応でリトライ／サーキットブレーカー検出。
  - シグナル読み出しは DuckDB を利用し、position_entries へ約定予定日の記録（BUY は追加、SELL は売却日更新）を実装（失敗しても発注フローは継続）。

- 注文管理コンポーネント
  - OrderRecord: 状態遷移ロジックとデータモデルを純粋なビジネスロジックとして実装。OrderState 列挙と許容遷移テーブル、transition_to による検証を提供。InvalidStateTransitionError を定義。
  - OrderManager: signal_queue からシグナルを受け取り、OrderRecord と OrderRepository（SQLite）を組み合わせて発注・同期・キャンセルを実装。
    - create_order: 同一 signal_id の active 注文検出による DuplicateOrderError。
    - send_order: クラッシュ耐性を考慮した 2 相永続化（OrderSent の永続化 → broker 呼び出し → broker_order_id を先に永続化 → OrderAccepted に遷移して永続化）。OrderRejectedError, OrderSentPendingError の扱いを実装。
    - sync_order: broker 側状態を取得して DB と同期。部分約定の進行は差分更新。
    - cancel_order: 終端状態はキャンセル不可として InvalidStateTransitionError、そうでなければ broker cancel を呼び Cancelled に遷移。
  - DuplicateOrder の DB 一貫性を SQLite のユニーク制約の例外から変換。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（同期 httpx を利用）。機能:
    - トークン取得の遅延初期化と再取得（401 リトライ）。
    - 共通 _request でタイムアウト／ネットワークエラーの例外を BrokerAPIError に変換。
    - 429（レート制限）を RateLimitError として扱う。
    - kabu station の状態コードと内部ステータスのマッピング実装。
    - 将来の WebSocket / push 対応（stream_push が存在する場合は ExecutionEngine の websocket スレッドが利用）。

- 監視関連
  - monitoring_db 初期化、SystemMonitor の利用、run_monitoring によるポーリングと stop flag 検出・終了処理を実装。
  - 発注イベントを監視 DB に記録するフックを装備（latency_ms 等）。

Changed
- なし（初回リリース）。

Fixed / Improvements
- .env パーサの堅牢化: クォート内エスケープ、export プレフィックス、コメント処理の改善。
- 発注のクラッシュ安全性向上: OrderSent と broker_order_id の永続化順序を明確にし、リコンシリエーションで不整合を回復できるように設計。
- run_execution / run_monitoring でプロセス優先度を設定するユーティリティ呼び出しを追加（高優先度設定）。
- 設定検証とウィザードでユーザー体験を向上（シークレットマスク、既存値の再利用提示、保存確認）。

Notes / その他
- .env はセキュリティ上、必ず Git 管理対象から除外するようヘッダで注意喚起を出力します。
- KABUSYS_ENV の有効値は development / paper_trading / live。live を指定すると validate_config で強い警告が出ます。
- PAPER_FILL_MODE の妥当性チェックは Settings.paper_fill_mode で実行され、不正値は ValueError を発生させます。
- 実装には DuckDB と sqlite3 を組み合わせて分析用データと監視データを分離する設計が採用されています。
- config/*.yaml のパース検証は PyYAML がインストールされている場合にのみ実行され、未インストール時は警告を出してスキップします。

既知の注意点（想定）
- 実行には外部パッケージ（httpx, websocket, duckdb, PyYAML 等）が必要です。validate_config は PyYAML の有無で挙動が変わります。
- 実際の発注を行うためには kabu ステーションが稼働している必要があります（KabuStationClient の前提）。

---

参考コマンド
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視起動: python -m kabusys.run_monitoring
- エンジン起動: python -m kabusys.run_execution

（以上はコードベースから推測して作成した CHANGELOG です。必要に応じて日付・項目を調整してください。）
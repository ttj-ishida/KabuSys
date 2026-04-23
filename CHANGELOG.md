# CHANGELOG

すべての注目に値する変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠しています。

全般的な注意:
- このログは与えられたソースコードの内容から推測して作成しています。実装の意図や将来の変更は実際のリポジトリ履歴と異なる場合があります。

## [Unreleased]

- なし（現時点のスナップショットは v0.1.0 に相当する機能群を包含しています）。

## [0.1.0] - 2026-04-23

Added
- 初期リリース相当の機能を追加。
  - パッケージメタ情報
    - バージョン: `__version__ = "0.1.0"`
  - 環境設定・読み込み
    - `.env` ファイルと OS 環境変数を統合して読み込む `kabusys.config` モジュールを追加。
    - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）。
    - `.env` 自動ロード（優先順位: OS 環境変数 > .env.local > .env）を実装。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` の行パーサーは以下に対応:
      - コメント・空行の無視、`export KEY=val` 形式、
      - シングル/ダブルクォートされた値のエスケープ処理、
      - 非クォート値内のインラインコメント判定（直前が空白/タブの場合のみ）。
    - Settings クラスで個別プロパティ（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、paper_trading 用設定、Kill Switch 関連、閾値等）を提供。値チェックで不正な設定は ValueError を発生させる。
  - 設定ウィザード CLI
    - `kabusys.config_setup` に対話式ウィザードを追加。`.env` の作成・更新を支援。
    - シークレット項目は出力時にマスク表示、選択肢/デフォルト表示、キャンセル/中断処理あり。
    - `.env` 書き出しテンプレートを定義（Git にコミットしないよう注意書き含む）。
  - 設定検証 CLI
    - `kabusys.validate_config` で起動前に `.env` と `config/*.yaml`（存在チェック・YAML パース）を検証する CLI を追加。
    - チェック対象の環境変数一覧（必須・任意）と有効値（KABUSYS_ENV, LOG_LEVEL 等）を実装。
    - `--strict` オプション: 警告を FAIL と扱い exit(1) で終了。
    - PyYAML 非インストール時は YAML 内容検証をスキップして警告を表示。
    - プレースホルダ値（例: 値が "your_value" や "_here" で終わる）を検出して警告を出す。
  - 実行系ランチャー
    - `run_execution.py`:
      - ExecutionEngine 起動スクリプトを追加。paper_trading 時に専用 SQLite（`data/paper_trading.db`）を使用して本番 DB と分離。
      - プロセス優先度設定（High）や PID ファイル、停止フラグ（data/stop_requested.flag）による外部停止制御を実装。
    - `run_monitoring.py`:
      - SystemMonitor のポーリングループ起動用スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV にかかわらず「本番 sqlite_path」を使用する設計。
  - 実行エンジンと発注ロジック
    - ExecutionEngine:
      - Signal Queue ベースの発注エンジン実装。セッションの時間管理（発注時間帯、マーケットクローズ）と WebSocket push ドレインを含む。
      - シグナル処理フロー: size_multiplier 適用、Gate 1（シグナルレベル検査）、Gate 2（エグゼキューションレベル検査・レート制限とサーキットブレーカー）、発注、position_entries の更新、監視 DB ログ記録。
      - WebSocket スレッド（broker が stream_push をサポートする場合）で push を受け取り内部キューへ登録。
      - push ハンドリング: broker_order_id をキーに同期処理(sync_order) を行い、Gate 3（ドローダウン監視）で kill_switch を発動可能。
      - kill_switch 実装: 全 active 注文をキャンセルしエンジン停止。
      - PID ファイル書き込みと既存 kill.flag の扱い（KILL_FLAG_CLEAR_ON_START による自動クリアオプション）。
    - OrderRecord:
      - 注文状態を表す OrderState enum と状態遷移検査ロジックを実装（InvalidStateTransitionError を定義）。
      - updated_at の自動更新、broker_order_id / filled_qty / avg_fill_price / error_message の更新をサポート。
    - OrderManager:
      - OrderRecord（状態機械）と OrderRepository（SQLite）を組み合わせた外向き API を提供。
      - create_order: 同一 signal_id の active 注文重複検出（DuplicateOrderError）と DB 制約例外の扱い。
      - send_order: クラッシュ耐性を考慮した 2 段階永続化パターンを採用（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）。OrderRejectedError / OrderSentPendingError の取り扱い。
      - sync_order: broker の状態を取得して DB と同期。部分約定の進展は差分更新。
      - cancel_order: cancel 可能性の判定（特定終端状態では不可）と broker API 呼び出し。
  - ブローカークライアント
    - KabuStationClient:
      - kabuステーション REST API クライアント実装（同期 httpx を使用）。
      - トークン取得の遅延初期化と 401 時の自動再取得（1 回リトライ）を実装。
      - レスポンスコードに基づくエラー変換（429 → RateLimitError, 5xx → BrokerAPIError 等）。
      - WebSocket push 受信（websocket を利用）や stream_push 用フック（broker 側に依存）に対応する余地あり。
  - DB/監視
    - DuckDB（分析用）と SQLite（監視用/履歴用）を併用する設計。監視用 DB の初期化ユーティリティを用意（init_monitoring_db）。
    - Execution/Monitoring 起動スクリプトは接続オブジェクトの生成とクローズを適切に行う。
  - リスク管理・Reconciliation の統合ポイント
    - RiskManager / Reconciler 用のフックが ExecutionEngine に組み込まれており、レート制御、サーキットブレーカー、メトリクスベースのドローダウン検査、起動時リコンシリエーションが動作する設計。

Changed
- （なし：初期機能群としてまとめて追加）

Fixed
- （なし：初期機能群としてまとめて追加）

Deprecated
- （なし）

Removed
- （なし）

Security
- 環境変数の取り扱いに注意する旨を README/.env テンプレートで明示（.env を Git にコミットしない注意書き）。

Notes / 想定される既知の挙動
- validate_config は PyYAML が未インストールの場合 YAML の中身検証をスキップする（警告を出力）。CI で厳密に検証したい場合は PyYAML をインストールしてください。
- .env パースは一般的な形式に対応しているが、非常に複雑なシェル展開等には対応しない（シンプルな key=value / quoted value を想定）。
- ExecutionEngine の時間依存ロジックはシステム時刻に依存するため、テストでは直接メソッドを呼び出して時刻依存性を避けることが想定されている。
- paper_trading モードは本番 DB と完全分離するよう設計されている（専用 SQLite を使用）。

---

この CHANGELOG はソースコードから推測して作成しています。必要であれば、各機能ごとにより詳細な変更点（実装ファイル名・関数名・例外処理の細部など）を追加できます。どの程度詳細に記載するか指定してください。
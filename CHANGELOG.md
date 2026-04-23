# CHANGELOG

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。

注: この CHANGELOG はコードベース（src/kabusys/ 以下）から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-23

Added
- 初期リリースを追加。
- 環境・設定管理
  - Settings クラスを導入し、環境変数からアプリケーション設定を一元管理（J-Quants トークン、kabu API、DB パス、LINE トークン等）。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。環境変数は OS 環境 > .env.local > .env の優先度で読み込まれ、OS 環境変数は保護。
  - .env ファイルのパースを強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
  - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）と関連プロパティ（is_live, is_paper, is_dev）を実装。
  - Settings インスタンス（settings）をモジュールレベルで提供。

- 設定ウィザード CLI
  - config_setup モジュールを追加。.env の対話的作成・更新を実装。
  - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE トークン等）と説明文、選択肢、シークレット入力の扱いを提供。
  - 既存 .env の読み込み・再利用、確認画面、保存処理を実装。
  - .env ファイルのテンプレート出力ロジックを実装（コメント付き）。

- 設定検証ツール
  - validate_config CLI を追加。.env と config/*.yaml の事前検証を行う。
  - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パス親ディレクトリ存在チェック、config/*.yaml の存在と PyYAML によるパース検証（PyYAML 未インストール時は警告でスキップ）を実装。
  - --strict オプションで警告も失敗扱いにできる exit コード制御。

- 実行用スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - paper_trading 環境時は paper 用 SQLite を使用して本番 DB と分離。
    - プロセス優先度設定、PID/停止フラグ処理、DB 初期化（監視テーブル）、duckdb 接続などを統合。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き、停止フラグ検出、監視 DB 初期化、DuckDB 接続を実装。

- 発注エンジンと実装
  - ExecutionEngine を追加（シグナル読み込み → Gate1/2 リスクチェック → 発注 → push ドレインループ）。
    - セッション時間管理（signal_send_start / signal_send_end / market_close）。
    - WebSocket push の受信・ドレイン処理、push による sync と Gate3（ドローダウン）チェック。
    - kill.flag 検査、KILL_FLAG_CLEAR_ON_START の挙動（存在時のクリア許可）対応。
    - PID ファイル管理、スレッド管理、監視 DB へのイベント記録フックを実装。
  - OrderRecord（状態遷移モデル）を追加
    - 状態列挙 OrderState と許容遷移の定義、遷移検証（InvalidStateTransitionError）、タイムスタンプ自動更新、オプションフィールド更新を実装。
  - OrderManager（外向き API）を追加
    - create_order: signal_id の重複防止、DB 保存、UUID 発番、DB 制約違反の DuplicateOrderError 変換を実装。
    - send_order: 送り出しの2相永続化パターン（OrderSent を先に永続化→ broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）、OrderRejectedError / OrderSentPendingError の扱いとクラッシュ耐性設計。
    - sync_order: broker API の状態照合と同期待ちロジック（部分約定の差分更新、OrderSent→Filled などの直接遷移を OrderAccepted を経由して扱う）。
    - cancel_order: 終端状態のキャンセル不可チェック、broker.cancel_order 呼び出し、Cancelled への遷移。
    - DuplicateOrderError, InvalidStateTransitionError などの明確なエラー型を提供。
  - risk_manager（インターフェイス利用）と ExecutionEngine の連携（Gate1/2/3、rate limit、circuit breaker、API 成功/失敗記録）を実装。
  - position_entries の書き込みロジックを実装（buy/sell の違い、pending の扱い、fill_date 計算に next_trading_day を使用）。

- ブローカークライアント（kabu）
  - KabuStationClient を追加（httpx 同期クライアントベース）。
    - トークン取得の遅延初期化、401 時のトークン再取得とリトライ、HTTP タイムアウト/ネットワークエラーを BrokerAPIError に変換。
    - レスポンス JSON パース時のエラーハンドリング、429 (Rate Limit) の専用例外化（RateLimitError）。
    - kabu ステーションの状態コードマップを実装。
    - 将来的な WebSocket/ストリーミング対応（stream_push を想定）に対応する構造。

- モニタリング
  - monitoring_db 初期化関数を各スクリプトで使用（init_monitoring_db）。
  - run_monitoring/run_execution から監視 DB と DuckDB を開いて使用する設計。

- ユーティリティ
  - process_priority 設定ユーティリティ（高優先度設定）を起動シーケンスの最初に呼ぶ。
  - logging_setup によるログ初期化フック（app_name 毎の設定）。

Changed
- パッケージメタ情報
  - パッケージ版番号を __version__ = "0.1.0" として設定。

- .env の読み込みポリシー説明を明確化
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。

Notes / Design decisions
- 発注フローはクラッシュ時の整合性を重視:
  - OrderSent の先行永続化、broker_order_id の永続化、Reconciliation による回復を想定。
  - OrderSentPendingError を使って「注文番号は発行されたが約定しない」ケースを上流に伝播させる。
- config/*.yaml の検証は PyYAML が存在する場合のみ実行。未インストール時は警告によりスキップ。
- run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する（設計上の仕様）。
- ExecutionEngine はテスト時に _process_signals と _drain_push_queue を直接呼べるように設計。

Deprecated
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- シークレット（J-Quants / Kabu / LINE トークン）は .env に保存することを推奨するが、.env は絶対に Git にコミットしない旨を README ヘッダに明記して出力するウィザードを実装。

---

開発者メモ:
- 本 CHANGELOG はコードから推測して作成しています。実際のリリースノートとして公開する場合は必要に応じて補正・追記してください。
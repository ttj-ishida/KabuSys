# CHANGELOG

すべての重要な変更点を記録します — Keep a Changelog 準拠。  
このファイルは、コードベースから推測したリリース／機能追加の要約です。

## [Unreleased]
- （未リリースの変更はここに記載）

## [0.1.0] - 2026-04-23
初回公開リリース。システムの起動・設定・発注・監視に関する基盤機能を提供します。

### Added
- 全体
  - パッケージの初期バージョンを定義（kabusys __version__ = "0.1.0"）。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を探索してルートを特定）。
  - 環境変数自動読み込み機能を追加（.env / .env.local の順で読み込み、OS 環境変数を保護）。
  - .env ファイルの対話式作成・更新ウィザードを追加（kabusys.config_setup: python -m kabusys.config_setup）。
  - .env のテンプレート出力を追加（重要な設定や注意書きを含むヘッダを出力）。
  - .env の行解析を強化（export 構文対応、引用符付き値のエスケープ処理、インラインコメント処理）。

- 設定管理
  - Settings クラスを追加（kabusys.config）し、環境変数をプロパティで安全に取得。
  - 必須設定取得時のチェック機構（_require）を実装し、未設定時に ValueError を送出。
  - env/log_level/paper_fill_mode などの値検証（有効値チェック）を実装。
  - パス系設定は Path オブジェクトで返却（expanduser 対応）。

- 設定検証 CLI
  - 設定検証用 CLI を追加（kabusys.validate_config: python -m kabusys.validate_config）。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス存在チェック、config/*.yaml の存在・パース検証を実装。
  - PyYAML 未インストール時は YAML 検証をスキップして警告を表示。
  - --strict フラグを追加（警告を FAIL 扱いにできる）。

- 実行スクリプト
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution: python -m kabusys.run_execution）。
    - paper_trading 環境では paper_trading 用 SQLite を使用して本番 DB から分離。
    - プロセス優先度設定（High）と PID ファイル管理を実装。
    - stop フラグ検知（data/stop_requested.flag）で安全にシャットダウン。
  - 監視ループ起動スクリプトを追加（kabusys.run_monitoring: python -m kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。

- 実行コンポーネント（Execution）
  - ExecutionEngine 実装（kabusys.execution.execution_engine）：
    - シグナル処理（8:50-9:10）と push ドレインループ（9:10-15:30）を管理するセッション実行。
    - kill.flag の扱いや起動時の kill_flag_clear_on_start オプション対応。
    - WebSocket push を受けて同期処理を行うワーカースレッド（stream_push がある broker のみ）。
    - position_entries への書き込み（発注の約定予測日を次営業日にするロジック）。
    - 監視 DB へのトレードイベント記録フック対応。

  - OrderRecord（状態遷移ロジック）を追加（kabusys.execution.order_record）：
    - 明示的な OrderState 列挙と許可される遷移テーブルを定義。
    - transition_to による遷移検証と更新（更新時に UTC タイムスタンプ自動更新）。
    - 不正遷移時は InvalidStateTransitionError を送出。

  - OrderManager を追加（kabusys.execution.order_manager）：
    - create_order / send_order / sync_order / cancel_order の外向き API を提供。
    - create_order は signal_id の重複チェック（部分一意性）と UUID の client_order_id 付与。
    - send_order はクラッシュ耐性を考慮した 2 相永続化戦略を実装:
      - 事前に OrderSent を DB にコミット → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移
      - OrderRejectedError / OrderSentPendingError の扱いを明確化
    - sync_order は broker API の状態を照合し、部分約定の進行を検出して更新。
    - cancel_order はキャンセル不可状態のチェックおよび broker cancel 呼出しを実装。

  - Reconciler / RiskManager 等との連携ポイントを確立（ExecutionEngine からの利用を想定）。

- ブローカークライアント
  - KabuStationClient （kabu ステーション向け REST client）を追加（kabusys.execution.kabu_client）：
    - httpx を用いた同期クライアント実装。
    - トークン取得の遅延初期化と 401 時の自動再取得・リトライ。
    - レスポンスパース失敗、ネットワーク/タイムアウト、429 レート制限、5xx サーバーエラーを専用例外に変換。
    - websocket（push）受信のための stream_push 想定（別途実装しているブローカークライアントで使用）。

- 監視
  - monitoring 初期化関数（init_monitoring_db）呼び出し位置を統一（execution/monitoring スクリプト）。
  - 監視ループと ExecutionEngine から監視 DB へイベント記録を行うフックを提供。

### Changed
- .env 読み込み優先順位を明確化: OS 環境 > .env.local > .env。OS 環境は保護（上書きされない）。
- .env parsing の振る舞いを詳細化（引用符内のエスケープ処理、コメントの扱いなど）して堅牢化。
- ExecutionEngine のデータベース取り扱い:
  - paper_trading 環境は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使うことで本番監視 DB と分離。
  - 監視プロセスは常に本番 sqlite_path を使用する設計（監視と実行の分離を明確化）。

### Fixed / Reliability
- send_order のクラッシュケースを考慮した永続化順序を明記／実装（broker_order_id を先に永続化して reconcilation を容易に）。
- sync_order が同一状態でも filled_qty / avg_fill_price の更新を反映するよう改善（部分約定の進行を検出）。
- ExecutionEngine のリコンシリエーション実行で例外が発生してもセッション継続するよう保護（例外はログ出力のみ）。
- モニタリングや position_entries への書き込み失敗時に発注フローを停止しないフォールバックを実装（ログ出力のみ）。

### Security / Notes
- .env ファイルは絶対に Git にコミットしないよう .env 書き込みテンプレートに明記。
- 本番環境（KABUSYS_ENV=live）での追加警告やチェックを実装（LINE 通知設定未登録、KILL_FLAG_CLEAR_ON_START=1 の危険性など）。
- validate_config による起動前チェックで設定ミスを検出しやすくする仕組みを提供（--strict による厳格モード）。

---

注記:
- 上記はソースコードの内容から推測した変更・機能一覧です。実際のコミット履歴やドキュメントがある場合はそれに従って調整してください。
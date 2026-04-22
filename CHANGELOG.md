CHANGELOG
=========

すべてのリリースノートは Keep a Changelog のフォーマットに準拠しています。
このファイルは主にコードベースから推定して記載しています（自動生成ではありません）。

## [Unreleased]

## [0.1.0] - 2026-04-22

初回リリース。以下の主要機能・改良・安全対策を含みます。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 環境設定・読み込み
  - Settings クラス（kabusys.config）を導入し、環境変数から設定値を型付きプロパティで取得可能に。
  - .env ファイル自動ロード機能（OS 環境変数 > .env.local > .env の優先順）。テスト用途に `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env パーサーが export プレフィックス、クォート付き値（エスケープ対応）、インラインコメント（条件付き）等に対応。

- 環境設定ウィザード CLI
  - `python -m kabusys.config_setup` による対話式ウィザードを提供。
  - .env の読み書き機能、既存値の再利用、シークレット値のマスク表示、デフォルト/選択肢サポート。
  - 生成される .env テンプレートにコメントと注意書きを含む。

- 設定検証ツール CLI
  - `python -m kabusys.validate_config` で .env や config/*.yaml の事前検証を実行可能。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）、KABUSYS_ENV・LOG_LEVEL の検証、DB パス親ディレクトリの存在チェック、config/*.yaml の存在と PyYAML によるパース検証（PyYAML 未導入時は警告）。
  - `--strict` オプションで警告も失敗として扱い exit code 1 を返す。

- 実行 / 監視ランナー
  - run_execution: ExecutionEngine の起動スクリプト（`python -m kabusys.run_execution` 相当を想定）。
    - paper_trading 環境では paper 用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ（data/stop_requested.flag）検出対応。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用。

- 発注基盤（Execution）
  - ExecutionEngine（kabusys.execution.execution_engine）
    - シグナル処理（デイリー: 8:50-9:10）と push ドレインループ（9:10-15:30）をサポート。
    - WebSocket push を別スレッドで受け取り、_push_queue 経由で処理。
    - PID ファイル書き込み、kill.flag の存在確認と KILL_FLAG_CLEAR_ON_START 取り扱い。
    - シグナル読み込みは DuckDB から行い、position_entries の自動更新（entry/sell 日付の記録）。
    - 組み込みの Gate 検査:
      - Gate1: シグナルレベル検査（信号ごとの許可）
      - Gate2: エグゼキューションレベル検査（レート制限、CIRCUIT_BREAKER 検出）
      - Gate3: ポートフォリオ指標（ドローダウン等）による kill_switch 発動
    - kill_switch() により全 active 注文をキャンセルしループ停止する安全機能。

  - OrderRecord（状態遷移モデル）
    - OrderState 列挙と許容遷移テーブルを定義。InvalidStateTransitionError を導入。
    - transition_to() による遷移検証とタイムスタンプ更新。

  - OrderManager（外向き API）
    - create_order(), send_order(), sync_order(), cancel_order() を提供。
    - create_order は signal_id と active 注文重複チェックを行い、DuplicateOrderError を返す。
    - send_order はクラッシュ安全性を考慮した 2 相永続化（OrderSent を先に commit、broker_order_id を先に保存、その後 OrderAccepted に遷移）を実装。OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order は broker の状態を取得して OrderRecord を同期。状態マッピング `_STATUS_TO_STATE` を使用。
    - cancel_order はキャンセル不可能な状態をチェックし（_CANCEL_INELIGIBLE_STATES）、broker API 呼び出し後に Cancelled に遷移。

  - Risk Manager / Reconciler の利用を想定した設計（ExecutionEngine は RiskManager, Reconciler を受け取る）。

- ブローカークライアント（kabu station）
  - KabuStationClient（kabusys.execution.kabu_client）
    - httpx を用いた同期 REST クライアント実装。
    - トークン取得（/token）を内部で遅延初期化し、401 時に再取得して 1 回リトライするロジックを実装。
    - レスポンス JSON パース失敗やタイムアウト・ネットワークエラーを BrokerAPIError 等に変換。
    - kabu station のステータスコードを内部状態（open/partial/filled/cancelled/rejected）へマップ。
    - 429 に対して RateLimitError を送出。

- 監視データベース初期化ユーティリティ
  - init_monitoring_db などにより監視用 SQLite テーブルを起動時に保証する処理を統合（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 発注処理のクラッシュ後復旧対策を設計として導入（OrderSent の永続化順序、broker_order_id の事前コミット、sync/reconciler による回復を想定）。
- ExecutionEngine の kill.flag と KILL_FLAG_CLEAR_ON_START の扱いを明確化し、誤起動や残留フラグによる事故を低減。

### Security
- .env ファイルについて "決して Git にコミットしないこと" を明示したテンプレートを出力。
- シークレット値は config_setup の表示でマスク表示。

### Known limitations / Notes
- config/*.yaml のパース検証は PyYAML（yaml パッケージ）への依存がある。未インストール時は検証をスキップして警告を出す実装。
- KabuStationClient は同期実装（httpx.Client）。将来的に async 対応へ移行可能な設計だが、現状は同期 API を想定。
- 一部の例外ハンドリングや外部依存（実ブローカー、kabu station の挙動）により挙動が環境依存となる箇所があるため、運用前に validate_config とローカルでの検証を推奨。
- 本リリースは初期バージョンであり、追加のエラーハンドリング・テスト・ドキュメント整備が今後の課題。

---

注: 本 CHANGELOG は提示されたコードベースからの推定に基づき作成しています。実際の変更履歴（コミットログ等）を反映したものではありません。
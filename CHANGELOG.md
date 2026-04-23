# Changelog

すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠します。

なお、この CHANGELOG はコード内容から推測して作成しています（実装に基づく初期リリース相当の記録）。

## [Unreleased]

- （今後の変更を記載）

## [0.1.0] - 2026-04-23

### Added
- 基本機能の初期実装（初回リリース）。
- 環境設定 / 設定ファイル関連
  - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護する仕組み）。
  - .env のパースはシングル/ダブルクォート、エクスポート（export KEY=val）、行内コメントなどに対応。
  - .env を対話的に作成・更新する設定ウィザード CLI を追加（python -m kabusys.config_setup）。複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン等）をサポート。
  - .env ファイルには自動生成ヘッダを付与し、Git へのコミット不可であることを明示。

- 設定検証ツール
  - 起動前に環境変数や config/*.yaml の不備を検出する CLI を追加（python -m kabusys.validate_config）。
  - 必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）未設定時はエラー、プレースホルダ値（"_here" や "your_value"）は警告。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証を実施。
  - --strict オプションで警告を FAIL（exit 1）扱いにできる。

- 設定オブジェクト
  - Settings クラスを提供し、環境変数から型付き設定を取得する API を実装。
  - 必須取得時は _require により未設定で ValueError を送出する。
  - Paper Trading 用の分離された SQLite パス（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE のバリデーションなどを実装。
  - KILL_FLAG 関連や監視閾値（CPU/MEM/DISK）などの設定プロパティを用意。

- 実行 / 監視ランナー
  - Execution エントリポイント（python -m kabusys.run_execution）を実装。
    - KABUSYS_ENV に応じて paper_trading の場合は専用 DB を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ（data/stop_requested.flag, kill.flag）の取り扱いを実装。
  - Monitoring エントリポイント（python -m kabusys.run_monitoring）を実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 発注 / 実行エンジン
  - ExecutionEngine を実装（シグナル処理ループ + WebSocket push ドレインループ）。
    - シグナル読み込みは DuckDB から行い、size_multiplier の適用、発注時間帯（8:50–9:10）と取引セッション（〜15:30）を管理。
    - kill.flag の発見時に kill_switch を発動して全 active 注文をキャンセルする仕組みを提供。
    - WebSocket（push）を受けて同期処理（sync_order）を行うスレッドを実装（broker が stream_push を持つ場合）。
    - 発注後の position_entries への書き込み（次営業日を fill_date にする処理）と、監視 DB へのイベントログ出力を実装。
  - 2 相永続化を意識した send_order フローを OrderManager に実装:
    - OrderCreated → OrderSent を先に永続化してから broker へ送信（クラッシュ安全性確保）。
    - broker_order_id を先に DB に保存し、その後 OrderAccepted に遷移して保存（クラッシュ後の Reconciliation を考慮）。
    - OrderRejectedError / OrderSentPendingError の扱いを実装。

- 注文状態管理
  - OrderRecord と OrderState（状態遷移テーブル）を実装。
    - 許可される状態遷移を明示し、不正遷移は InvalidStateTransitionError を raise。
    - transition_to により状態遷移と補助フィールド（broker_order_id / filled_qty / avg_fill_price / error_message）の更新を行う。

- Broker クライアント（kabu ステーション）
  - KabuStationClient を実装（同期 httpx クライアント）。
    - トークン取得の遅延初期化、自動リトライ（401 時にトークン再取得してリトライ）を実装。
    - HTTP エラー（401, 429, 5xx 等）を適切な例外（BrokerAPIError, RateLimitError 等）に変換。
    - kabu station の注文状態コードから内部ステータスへのマッピングを定義。

- Reconciliation / Monitoring
  - init_monitoring_db や MonitoringDB との連携ポイントを用意（監視用テーブル初期化 / イベントログ）。
  - Execution 起動時に Reconciler を呼ぶフローを組み込める設計（起動時リコンシリエーションのサポート）。

- その他ユーティリティ
  - .env パーサーの堅牢化（エスケープ・クォート処理、インラインコメント扱い）。
  - ログ設定セットアップ、プロセス優先度変更ユーティリティへのフック箇所を追加。

### Changed
- 初回リリースのため変更履歴なし。

### Fixed
- 初回リリースのため修正履歴なし。

### Security
- .env ファイルは生成時に Git にコミットしないよう注意喚起を明記。
- 自動ロード機能は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト・セキュリティ用途）。

### Notes / Implementation details
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を起点に探索するため、カレントワーキングディレクトリに依存しない。
- Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（意図的）。
- ExecutionEngine は kill.flag の存在を起動前にチェックし、KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動クリアできる（注意して設定すること）。
- OrderManager の DuplicateOrder 判定は DB の部分ユニークインデックスと照合する実装を持ち、IntegrityError の内容に応じて DuplicateOrderError に変換する。

---
この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートやユーザ向けドキュメント作成時は、実際の変更差分・コミットログを参照して更新してください。
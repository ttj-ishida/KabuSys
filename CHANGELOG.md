# CHANGELOG

すべての注目すべき変更点を記録します。
このファイルは "Keep a Changelog" の形式に準拠します。

## [0.1.0] - 2026-04-22

### Added
- 初回リリース: KabuSys 日本株自動売買システムの基礎機能を実装。
- 環境・設定管理
  - .env ファイルの自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
  - .env のパースロジックを強化（export 形式対応、シングル/ダブルクォート内のエスケープ対応、コメント処理の改善）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の読み込み順序: OS環境変数 > .env.local > .env（.env.local は上書き）。
  - OS 側の環境変数を保護する protected オプションを実装（上書き防止）。
  - Settings クラスを実装し、各種設定値（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、PID/KILL フラグパス、閾値、環境判定など）をプロパティ経由で取得可能に。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL などの値検証を実装（無効値時は例外を送出）。

- 設定ウィザード CLI
  - python -m kabusys.config_setup により対話式で .env を作成/更新するウィザードを追加。
  - シークレット入力はマスク、デフォルトや選択肢の提示、保存前の確認を実装。
  - .env を安全に書き出すテンプレートを提供。

- 設定検証 CLI
  - python -m kabusys.validate_config による起動前チェックを実装。
  - 必須環境変数の存在チェック、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DBパス親ディレクトリ確認、config/*.yaml ファイル存在と YAML パース（PyYAML があれば検証）などを実施。
  - --strict オプションで警告を FAIL（exit code 1）として扱う。

- 実行エントリ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。paper_trading モード時は paper_trading 用 SQLite を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用。

- 注文関連コア
  - OrderRecord: 注文の状態機械（OrderState）と状態遷移ロジックを実装。InvalidStateTransitionError を定義。
  - OrderManager: DB（OrderRepository）と OrderRecord を使った外向き API を実装（create/send/sync/cancel）。重複注文回避、例外ハンドリング、キャンセルロジックを実装。
  - ExecutionEngine: Signal の読み込み・Gate1/Gate2（リスクチェック）・発注処理・push ドレインループ・Gate3（ドローダウン検査）・kill_switch を備えたセッション実行エンジンを実装。
    - シグナルループ（デフォルト 8:50 - 9:10）、push ドレイン（9:10 - 15:30）をサポート。
    - 発注時の二相永続化パターン（OrderSent を DB にコミット → broker 呼び出し → broker_order_id を DB に保存 → OrderAccepted に遷移）でクラッシュ耐性を強化。
    - pending（OrderSentPendingError）扱い、リコンシリエーションでの回復設計を導入。
    - position_entries への書き込み（発注成功時）で保有日数/再エントリー制御に対応（DuckDB を使用）。
    - WebSocket push を受けて同期（sync_order）するワーカをサポート（broker が stream_push を持つ場合のみ）。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（httpx 同期クライアント）。
  - トークン取得の遅延初期化、401 発生時のトークン再取得とリトライ処理。
  - HTTP 429 を RateLimitError として扱う。HTTP 5xx/ネットワーク/タイムアウトは BrokerAPIError として扱う。
  - REST API 結果の JSON パースエラーハンドリング。
  - WebSocket 導線（websocket を利用）を想定し、stream_push 用のフックを呼び出す設計。

- 監視系
  - monitoring DB 初期化処理（init_monitoring_db）を利用して起動時にテーブル作成を保証。
  - 監視ループ実行中の例外は次ポーリングまで待機する設計。

- ユーティリティ
  - process_priority を High に設定するユーティリティ呼び出しを実行起動時に実行（monitoring/execution）。
  - ロギング設定ユーティリティ（setup_logging）を起動時に利用。

### Changed
- 設計上の注意点を明確化
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を利用するという振る舞いを明記。
  - run_execution は paper_trading モード時に paper_sqlite_path を使用して本番と記録を完全分離するよう実装。
  - validate_config と Settings の値検証の扱い: validate_config は警告/エラーを出力して終了コードで判定（--strict オプションあり）、Settings プロパティは無効値に対して ValueError を送出することで呼び出し元に明示的エラーを伝える。

### Fixed
- .env パーサの抜け/誤判定を改善
  - クォート内のエスケープやインラインコメントの誤処理を修正、より実環境の .env フォーマットに耐えるように。

### Known issues / Notes
- config/*.yaml の内容検証は PyYAML がインストールされていない環境ではスキップされる（validate_config はその場合に警告を出力）。
- validate_config における LOG_LEVEL の取り扱いは CLI では警告にとどめるが、Settings.log_level の参照時には無効値で例外を投げる点に注意。
- KILL_FLAG_CLEAR_ON_START=1 は本番環境では危険（validate_config と run_session 内で警告を出す/挙動を制御）。
- WebSocket の受信・broker.stream_push の実装は broker 側実装に依存するため、利用時は broker クライアントが stream_push を提供しているか確認が必要。

---

今後のリリースでは、テストカバレッジの追加（特にクラッシュ/リコンシリエーション経路）、詳細な監視メトリクスの拡充、非同期対応（httpx.AsyncClient への移行）、および broker 抽象の拡張を予定しています。
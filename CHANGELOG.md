# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して作成した変更履歴です。

なおバージョン表記はパッケージの __version__ に基づいています。

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-23

### Added
- 基本リリース: KabuSys 日本株自動売買システムの初期実装。
- 設定 / 環境変数管理
  - Settings クラスを追加。環境変数から各種設定を取得する集中管理モジュールを提供（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、LINE 通知設定など）。
  - .env ファイル自動読み込み機能を実装。自動読み込みの優先順位は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサを強化（export 形式対応、シングル/ダブルクォート内でのエスケープ処理、インラインコメント解析）。
  - PAPER_FILL_MODE、paper_trading 用 DB パス、PID / kill flag のパス、リソース閾値（CPU/Memory/Disk）など各種設定プロパティを追加。

- 設定ウィザード / CLI
  - python -m kabusys.config_setup: 対話式ウィザードで .env の初期作成・更新を行うスクリプトを追加。
  - .env を読み込み既存値を再利用、シークレット項目はマスク表示。生成時にテンプレートヘッダを付与して書き出す。

- 設定検証 CLI
  - python -m kabusys.validate_config: .env と config/*.yaml の検証を行う CLI を追加。
  - 必須環境変数未設定の検出、プレースホルダ値の検出（末尾に "_here" や "your_value"）、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認および PyYAML によるパース検証（PyYAML 未インストール時は警告スキップ）。
  - --strict オプションで警告を FAIL（exit code 1）として扱う。

- 実行スクリプト
  - python -m kabusys.run_execution: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と完全分離。
  - python -m kabusys.run_monitoring: SystemMonitor のポーリングループを起動するエントリポイントを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用。

- 発注 / 実行エンジン
  - ExecutionEngine を追加。シグナル処理（8:50–9:10）と WebSocket push ドレイン（9:10–15:30）を含むセッション実行フローを実装。
  - EngineConfig によりターゲット日と時間帯を設定可能。
  - シグナル読み取りは DuckDB 経由。position_entries への書き込み（entry/sell 日付処理）を行う。
  - WebSocket スレッドを用意し、broker の stream_push を受け取って内部キューに投入する仕組みを実装。

- 注文管理
  - OrderRecord（状態マシン）を実装。OrderState 列挙（created → sent → accepted → partial → filled → closed / cancelled / rejected）と遷移許可定義を持つ。状態遷移検証と updated_at 自動更新をサポート。
  - OrderManager を実装。create/send/sync/cancel の外向き API を提供。
    - create_order: signal_id による重複チェック（DB とインメモリの両方）を行い、DuplicateOrderError を提供。
    - send_order: 2相永続化戦略（OrderSent に遷移してコミット → broker 呼び出し → broker_order_id を先にコミット → OrderAccepted に遷移してコミット）によりクラッシュ後の復旧を容易にする実装。
    - broker 側で注文が保留（OrderSentPendingError）となるケースを扱い、broker_order_id を保存して OrderSent のままにする（Reconciliation の対象にする）。
    - sync_order: broker からの状態を取得してローカル状態へ反映。部分約定の進展は状態遷移無しで filled_qty / avg_fill_price を更新。
    - cancel_order: 終端状態ではキャンセル不可とし InvalidStateTransitionError を返す。それ以外は broker API を呼び Cancelled に遷移。

- ブローカークライアント（kabu）
  - KabuStationClient を実装（httpx 同期 client を使用）。トークン取得（遅延初期化・再取得）と認証付きリクエストの自動再試行をサポート（401 リトライ）。429 を RateLimitError、HTTP 5xx を BrokerAPIError として扱う。JSON パース失敗を BrokerAPIError に変換。

- リスク管理 / リコンシリエーション / 監視
  - ExecutionEngine と連携する RiskManager（Gate 1/2/3 の設計に対応）を組み込む想定のフローを実装。Gate 1＝シグナルレベル検査、Gate 2＝実行レベル（レート制限・サーキットブレーカー等）、Gate 3＝ポートフォリオ指標によるドローダウン監視（NG の場合は kill_switch を発動）。
  - kill_switch 実装: 全ループ停止と全 active 注文のキャンセル。KILL_FLAG_CLEAR_ON_START による起動時 kill.flag 自動クリアの判定も実装。
  - MonitoringDB 経由で発注イベント（Sent 等）の監視ログを記録するポイントを追加（監視 DB 書き込み失敗でも発注フローは継続）。

- 汎用ユーティリティ
  - プロセス優先度を設定するユーティリティ（set_process_priority）呼び出しを起動シーケンスの最初に行う。
  - logging 設定ユーティリティ（setup_logging）を起動時に使用。

### Changed
- N/A（初期リリースのため破壊的変更はなし）

### Fixed
- N/A（初期リリースのため修正履歴なし）

### Notes / Implementation details
- validate_config: PyYAML がインストールされていない場合は YAML の内容検証をスキップし、警告を出す。
- validate_config はプレースホルダ（"_here" や "your_value"）が残る環境変数を警告する。
- Settings の env / log_level / PAPER_FILL_MODE 等は許容値外の場合 ValueError を投げるため、起動時の早期検出が可能。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数の不正値を検出しデフォルトにフォールバックする（0以下や非整数はデフォルト使用）。
- 実行時 DB 接続: Monitoring は常に本番 sqlite_path を使用。Execution は paper_trading の場合 paper_sqlite_path を使用して本番と分離。
- ExecutionEngine のセッション開始前にリコンシリエーションを試み、例外が発生してもセッションは継続する。

### Known issues / TODO（推測）
- config/*.yaml の詳細なスキーマバリデーションは実装されておらず、PyYAML によるパース検証のみ（存在と基本的なパースの確認）に留まる。
- KabuStationClient の WebSocket 部分は websocket ライブラリ利用のため環境依存があり、エラーハンドリングや再接続ロジックの拡張余地がある。
- 一部の外部コンポーネント（Reconciler、RiskManager の詳細実装、MonitoringDB 実装など）は統合を前提としているため、実環境での運用に合わせた追加検証が必要。

---

作成者注: この CHANGELOG は提供いただいたソースコードから機能や挙動を推測して作成したものです。実際のリリースノートと差異がある場合は、必要に応じて調整してください。
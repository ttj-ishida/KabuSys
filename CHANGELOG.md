CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-22
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- 環境設定 / 設定管理
  - Settings クラスを導入（kabusys.config）。環境変数からアプリケーション設定を取得する統一 API を提供。
  - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local をロード）。OS 環境変数を保護する仕組みと、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env の行パーサを実装（export 形式対応、シングル／ダブルクォートとバックスラッシュエスケープ対応、インラインコメントルール適用）。
  - 設定値のバリデーションを一部プロパティで実施（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - production / paper_trading 間で DB を分離（paper_trading 時は paper_trading 用 SQLite を使用）。

- 対話式環境セットアップ
  - config_setup CLI（kabusys.config_setup）を追加。対話式ウィザードで .env を初期作成 / 更新し、テンプレートに沿って .env を保存可能。
  - 保存時の説明・注意喚起メッセージ（.env を Git にコミットしない旨など）を含む。

- 設定検証ツール
  - validate_config CLI（kabusys.validate_config）を追加。.env と config/*.yaml の不備を起動前に検出するツールを提供。
  - 必須環境変数チェック、プレースホルダ値検知、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML がある場合は config/*.yaml のパース検証を実施。
  - --strict オプションで警告を失敗扱いにできる。

- 実行スクリプト
  - run_execution（kabusys.run_execution）: ExecutionEngine を起動するエントリポイント。プロセス優先度設定、PID/stop フラグ管理、paper_trading 用 DB 切り替え、監視 DB 初期化を行う。
  - run_monitoring（kabusys.run_monitoring）: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応。Monitoring は常に本番 sqlite_path を使用。

- 発注エンジン / 注文管理
  - ExecutionEngine（kabusys.execution.execution_engine）を実装。シグナル読み込み、Gate1/2（シグナル／エグゼキューション検査）、発注（send）、push ドレインループ（WebSocket 経由の通知処理）を含むセッション制御（開始・締切・終了時刻管理）。
  - OrderRecord（kabusys.execution.order_record）: 注文状態を表す状態遷移モデルを実装（OrderState 列挙、許可遷移マップ、transition_to による遷移検証）。不正遷移時は InvalidStateTransitionError を送出。
  - OrderManager（kabusys.execution.order_manager）: OrderRecord（ビジネスロジック）と OrderRepository（SQLite）を組み合わせた外向き API を提供。create/send/sync/cancel の各ワークフローを実装。
    - create_order で signal_id の重複防止（部分ユニークインデックスとアプリレベルチェック）。DuplicateOrderError を導入。
    - send_order はクラッシュ安全性を考慮した 2 段階永続化（OrderSent を先にコミット → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）。OrderSentPendingError（ブローカーが注文番号を返すが約定しないケース）を適切に扱う。
    - sync_order は broker のステータスに基づき状態同期。部分約定の進行はフィールド差分のみ更新する最適化あり。
    - cancel_order はキャンセル不可能な状態を判定し、不可能なら InvalidStateTransitionError を送出。broker_order_id があればブローカーに cancel を投げる。

- ブローカークライアント
  - KabuStationClient（kabusys.execution.kabu_client）を実装（httpx 同期クライアント）。トークン取得の遅延初期化、自動再取得（401 発生時の再試行）、HTTP エラー分類（429 を RateLimitError として扱う等）、JSON パース失敗の変換を実装。
  - kabu ステータスコード → 内部ステータスマッピングを定義。

- リスク管理 / Reconciler 等の統合点を実装
  - ExecutionEngine 側で RiskManager, Reconciler, OrderRepository, OrderManager, MonitoringDB 等を組み合わせるフローを用意。発注成功/失敗時にレート制限や監視 DB へのログを記録するフックを含む。

- 監視・ポーリング
  - run_monitoring で Monitoring DB 初期化と SystemMonitor の check_once を定期実行するループを提供。例外発生時にログを残して次ポーリングへ継続。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- 設定ファイル（.env）に関する注意書きを config_setup の出力に明示（.env を Git にコミットしないよう注意喚起）。

Notes / 実装上の重要ポイント
- .env の自動ロードはプロジェクトルート検出に .git または pyproject.toml を利用するため、パッケージ配布後の挙動も想定した実装となっている。ルートが特定できない場合は自動ロードをスキップする。
- PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等は Settings 側でも厳密に検証し、無効値で ValueError を送出する（起動時の早期検出を容易にする）。
- ExecutionEngine は kill.flag を用いた kill switch を備え、起動時に kill_flag_clear_on_start に応じて既存の kill.flag をクリアするか起動拒否する。
- 発注のクラッシュシナリオ（OrderSent のまま残る等）に対して Reconciler による復旧を想定した設計（OrderSent の broker_order_id 永続化や sync_order による状態回復をサポート）。
- config/*.yaml の内容検証は PyYAML の有無で挙動が変わる（未インストール時はパース検証をスキップして警告を出す）。

今後の予定（例）
- async 対応の検討（httpx.AsyncClient への移行）
- 監視・メトリクス出力の強化（Prometheus 等との連携）
- より細かなテストカバレッジ拡充（リコネシリエーションや障害時の動作など）

-----------

この CHANGELOG はコードベースから機能・挙動を推測して作成しています。実際のリリースノートとして使用する場合は差分やコミット履歴を参照のうえ、必要に応じて修正してください。
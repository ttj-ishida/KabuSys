CHANGELOG
=========

すべての重要な変更点を記録します。形式は「Keep a Changelog」に準拠しています。
（注: 以下はリポジトリ内のソースコードから推測して整理した初期リリース向けの変更履歴です）

Unreleased
----------

- なし（次回のリリースに向けた追記をここに記載してください）

0.1.0 - YYYY-MM-DD
------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基本機能を追加。
- パッケージ全体
  - パッケージバージョンを設定: __version__ = "0.1.0"。
  - モジュール群: data, strategy, execution, monitoring などの骨格を提供。

- 設定管理
  - 環境変数・設定読み込みモジュールを追加（src/kabusys/config.py）。
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パースは export プレフィックス、クォート、エスケープ、インラインコメント（条件付き）に対応する堅牢な実装。
    - Settings クラスを提供して型付きプロパティ経由で各設定値へアクセス可能（J-Quants トークン、kabu API パスワード、DBパス、ログレベル、env 判定など）。
    - PAPER_FILL_MODE の値チェック、有効値は instant/partial/never/reject。
    - 環境名（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証ロジックを実装。

- .env ウィザード CLI
  - 対話式ウィザードとして config_setup を追加（src/kabusys/config_setup.py）。
    - .env 作成・更新を支援する対話形式。
    - 項目定義によりデフォルト値、選択肢、シークレット（表示マスク）をサポート。
    - 書き込みテンプレートは安全上の注意（.env を Git にコミットしないこと）を含むヘッダを出力。
    - 実行例: python -m kabusys.config_setup、--env-file で保存先指定可能。

- 設定検証 CLI
  - validate_config を追加（src/kabusys/validate_config.py）。
    - .env と config/*.yaml の事前チェックを提供。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検査、LIVE 環境での追加警告。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML がインストールされていれば）パース検証。PyYAML 未インストール時はパース検証をスキップして警告を出力。
    - --strict オプション: 警告も FAIL として exit(1) を返す。

- 実行スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine 起動のためのエントリポイント。
    - paper_trading 環境では専用の paper_trading DB を使用して本番 DB と分離。
    - PID ファイル書き込み、停止フラグ(stop_requested.flag)検知、プロセス優先度設定 (set_process_priority) を実行。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを起動。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する（意図的分離の方針）。

- 実行エンジン本体
  - ExecutionEngine を追加（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（指定時間帯に実行）と WebSocket push のドレインループを管理。
    - kill.flag による起動拒否/自動クリア（KILL_FLAG_CLEAR_ON_START の設定で変更）を実装。
    - PID ファイルの書き出し・削除を実装。
    - WebSocket スレッド（broker が stream_push をサポートする場合）で push を受け取り _push_queue に投入。
    - シグナル処理フロー:
      - size_multiplier の適用（BUY のみ）。
      - Gate1: シグナルレベル検査（RiskManager）。
      - Gate2: 実行レベル（レート制限・サーキットブレーカー）検査（3回リトライ, CIRCUIT_BREAKER の場合はループ停止）。
      - 発注後に position_entries へ約定予定日を記録。
      - 監視DB（MonitoringDB）への発注イベントログ出力（設定されている場合）。
    - push 処理:
      - broker_order_id から client_order_id を特定し sync_order を実行。
      - Gate3: ポートフォリオメトリクス（ドローダウン等）チェック。NG の場合は kill_switch 発動。
    - kill_switch: 全 active 注文のキャンセル処理。

- 注文関連
  - OrderRecord（状態マシン用データモデル）を追加（src/kabusys/execution/order_record.py）。
    - 明示的な OrderState 列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可される遷移を定義。InvalidStateTransitionError を導入。
    - transition_to() により状態遷移とメタ情報（broker_order_id, filled_qty, avg_fill_price, error_message）を安全に更新、updated_at を自動更新。

  - OrderManager を追加（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id 重複チェック（DB とメモリ）を行い、UUID を client_order_id として採番。
    - send_order: 2相永続化とクラッシュ耐性を考慮した発注フロー実装。
      - Step1: OrderCreated -> OrderSent を DB に永続化（broker 呼出し前）。
      - Step2: broker.send_order 呼び出し。
      - Step3a: broker_order_id を先に DB に保存（state は Sent のまま）。
      - Step3b: OrderAccepted に遷移して DB 更新。
      - 失敗時の扱い: OrderRejectedError は Rejected に遷移、OrderSentPendingError は broker_order_id を保存した上で OrderSent のまま残す（呼び出し元へ伝播）。
      - その他例外は捕捉せず OrderSent のまま残り、後で list_uncertain() 等で検出する想定。
    - sync_order: broker.get_order_status を呼び、status をローカル状態に同期。部分約定の進行は直接フィールド更新して反映。
    - cancel_order: 終端状態はキャンセル不可（InvalidStateTransitionError を投げる）、それ以外は broker.cancel_order を呼び Cancelled に遷移。

  - オーダー状態とキャンセルポリシー:
    - キャンセル不適格状態を定義（Closed, Cancelled, Rejected, Filled）。
    - DB 側の一意制約違反は DuplicateOrderError に変換して扱う。

- ブローカー API クライアント
  - KabuStationClient を追加（src/kabusys/execution/kabu_client.py）。
    - httpx（同期）による REST クライアント実装。
    - トークン取得の遅延初期化と自動再取得（401 時のリトライ）。
    - レスポンス JSON パース失敗、ネットワークエラー、タイムアウトを BrokerAPIError に変換して扱う。
    - 429 ステータス時は RateLimitError を送出。
    - kabu station の注文状態コードを内部ステータス ("open","partial","filled","cancelled","rejected") にマッピング。

- リスク制御・再整合（骨格）
  - RiskManager / Reconciler / OrderRepository 等の使用箇所を組み合わせて実行フローを実現（詳細な実装は別モジュールに依存）。
  - ExecutionEngine は Reconciler を起動時に呼び出し、結果概要をログ出力する。

- DB 周り
  - DuckDB は分析用、SQLite は監視・注文履歴用として使い分け（paper_trading では paper_trading 用 SQLite を使用して本番から分離）。
  - Monitoring の初期化関数 init_monitoring_db を使用して必要テーブルを冪等に作成。

- ユーティリティ
  - プロセス優先度の設定ユーティリティ (set_process_priority) の呼び出しを起動時に行う。
  - ロギング初期化関数 setup_logging を利用してモジュール毎にログを整備。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Notes / マイグレーション / 運用メモ
- .env 管理
  - .env は絶対にリポジトリにコミットしないこと。config_setup にて .env を作成する際にもヘッダで注意喚起を行う。
  - OS 環境変数は自動読み込み時に保護される（.env の値で上書きされない）。ただし .env.local は override=True のため .env の値を上書きする点に注意。

- 設定検証
  - validate_config は PyYAML が無い環境では YAML 内容検証をスキップします。CI 等で YAML のパース検証を必須とする場合は PyYAML をインストールしてください。

- 本番起動ガード
  - KABUSYS_ENV=live の場合、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）の未設定は警告となる。また KILL_FLAG_CLEAR_ON_START=1 は本番で危険（自動クリア）なので警告する。
  - ExecutionEngine は kill.flag が存在する場合、設定によっては起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動）。

- DB 分離
  - paper_trading 環境では paper_trading 用 SQLite を使用するため、本番データと完全に分離できます。運用時は PAPER_TRADING_SQLITE_PATH を適切に設定してください。

- 例外とクラッシュ耐性
  - send_order のフローはクラッシュ時の整合性を考慮して複数段階で永続化する設計（OrderSent レコードの残存、broker_order_id の先コミット等）。Reconciliation によりクラッシュ後の復旧が可能になるよう設計されています。

Known issues / TODO（コードから推測）
- 一部のコンポーネント（BrokerClientFactory, Reconciler, RiskManager の詳細実装等）は別モジュールに依存するため、それらの実装状況に応じて動作が異なります。
- KabuStationClient の WebSocket 実装は外部ライブラリ（websocket）を使用しており、接続管理や再接続ロジックの強化が今後の改善ポイント。
- 単体テスト/統合テストのカバレッジは明記されていないため、実運用前に主要パスのテスト整備を推奨。

Contact / Contributing
- バグ報告・機能要望はリポジトリの Issue を利用してください。
- 初期リリースのためドキュメント・README・運用手順の追加が望まれます（特に本番稼働手順と安全対策）。

--- 

（上記はソースコードの実装から推定して作成した CHANGELOG です。日付（YYYY-MM-DD）は実際のリリース日で置き換えてください。）
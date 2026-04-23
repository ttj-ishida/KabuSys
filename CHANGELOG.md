CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。
<!-- 翻訳注: 日付はコードベースから推測して付与しています。 -->

Unreleased
----------

（なし）


0.1.0 - 2026-04-23
------------------

Added
- 初期リリース: KabuSys の基本コンポーネントを追加。
- 環境設定・検証 CLI を追加:
  - python -m kabusys.config_setup: 対話式ウィザードで .env を作成 / 更新する機能を提供。
    - 複数の設定項目（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DB パス / LINE 等）をサポート。
    - シークレット項目はマスク表示、選択肢・デフォルト値対応。
    - .env のテンプレート生成と保存機能を提供（.env を絶対に Git にコミットしない注意書きを追加）。
  - python -m kabusys.validate_config: 起動前の設定検証ツールを提供。
    - 必須 / 任意環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の値検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース確認（PyYAML 未インストール時はスキップ）。
    - --strict オプションで警告も失敗（exit 1）として扱う。
    - INFO/WARNING/ERROR メッセージを集計し適切な終了コードを返す。

- 設定読み込みと管理:
  - kabusys.config.Settings クラスを導入。環境変数から型変換済みの設定値を提供（パスは Path、閾値は float 等）。
  - 自動 .env 読み込み機能:
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサー強化:
    - export prefix を扱う、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い（クォート有無に応じた適切な処理）に対応。

- 実行コンポーネント（Execution / Broker / Order 周り）:
  - ExecutionEngine: シグナル読み込み・発注・WebSocket push ドレイン・セッション管理（signal_send_start/ signal_send_end / market_close の時間制御）を実装。
    - セッション起動時のリコンシリエーション呼び出し、PID ファイル管理、kill.flag の検査と起動時動作（KILL_FLAG_CLEAR_ON_START による自動クリア対応）。
    - シグナル処理フロー: Gate1（シグナルレベル）/ Gate2（実行レベル・レート制御）/ Gate3（ドローダウン監視）を実装。Gate2 は最大リトライ、Circuit Breaker 判定でループ停止。
    - 発注成功／保留（pending）／失敗それぞれのハンドリングと監視DBへのイベントロギングフック。
    - WebSocket ワーカーで push を受け _push_queue に投入、drain して sync_order と Gate3 を実行。
    - kill_switch により全 active 注文をキャンセルするロジックを提供（外部 stop との連携）。
  - OrderRecord: 注文状態遷移を管理する純粋ドメインモデルを実装。許可遷移テーブルを持ち、不正遷移で InvalidStateTransitionError を投げる。transition_to はメタ情報（broker_order_id / filled_qty / avg_fill_price / error_message）を更新し updated_at を UTC で更新。
  - OrderManager: OrderRecord と OrderRepository（SQLite）を組み合わせた外向き API を実装。
    - create_order: signal_id ごとの重複チェック（部分ユニークインデックス違反を DuplicateOrderError に変換）。
    - send_order: クラッシュ安全性を考慮した二相的永続化フロー（OrderSent を先に永続化 → broker 呼び出し → broker_order_id のコミット → OrderAccepted へ遷移等）。OrderRejectedError, OrderSentPendingError の扱いを明確化。
    - sync_order: broker からの状態取得による同期処理。部分約定の進展はフィールド差分だけを更新する挙動。
    - cancel_order: キャンセル不可能な状態の判定と broker へのキャンセル呼び出し、状態遷移の管理。
  - BrokerClient 関連:
    - KabuStationClient: kabu station REST API クライアントを httpx（同期）で実装。トークンの遅延取得と自動再取得、401 リトライ、429 (RateLimit) と 5xx を BrokerAPIError / RateLimitError 等にマッピング。
    - WebSocket push（stream_push）インターフェースをサポートし、ExecutionEngine 側で利用。

- 監視（Monitoring）:
  - run_monitoring スクリプトを追加:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、負値等はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（monitoring DB の初期化 / duckdb 接続）。
    - stop_requested.flag による外部停止フラグの検知。

- Paper trading / 環境分離:
  - Settings に paper_sqlite_path / paper_fill_mode を追加。paper_trading 環境時は専用 SQLite DB を使用して本番 DB と分離。
  - Execution 起動時に KABUSYS_ENV=paper_trading を検出して BrokerFactory で MockBroker を選択する設計を想定（コード内で参照）。

- 監視・ログ・プロセス管理ユーティリティ参照:
  - setup_logging, set_process_priority 等ユーティリティを利用して起動時のログ設定とプロセス優先度設定を行う。

Changed
- 初期リリースのため、API 設計とファイル構成を確定。モジュール間の責務を明確化（OrderRecord は DB を持たず純粋ロジックに限定、OrderManager が永続化を扱う等）。

Fixed
- .env のパースに関する細かな扱い（export プレフィックス、クォート内のエスケープ、インラインコメント判定）を実装して汎用性を向上。
- validate_config による設定チェックで、YAML パーサー未インストール時にスキップして警告を出すようにして起動時の致命的エラーを回避。

Security
- config_setup で生成する .env に「.env は絶対に Git にコミットしないこと」という注意を明記。
- シークレット値は対話表示時にマスクして表示。

Notes / ユーザーへの補足
- .env の自動読み込みはプロジェクトルート検出に依存します。配布後や異なる配備形態で必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自前で環境変数を注入してください。
- validate_config で config/*.yaml の中身の検証を行うには PyYAML が必要です（未インストール時は検証をスキップして警告のみ）。
- ExecutionEngine の kill.flag / KILL_FLAG_CLEAR_ON_START の取り扱いは本番での誤稼働防止に重要です。KILL_FLAG_CLEAR_ON_START=1 は開発用のみにしてください。

Acknowledgements
- この CHANGELOG は提示されたコードベースの内容に基づいて推測して作成しています。実際のリリースノートとして利用する場合は、リリース履歴・コミットログなどで内容を確認・補完してください。
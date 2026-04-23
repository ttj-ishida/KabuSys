# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  

注: このバージョンはパッケージ内の __version__ に合わせて 0.1.0 としてリリースされています。

## [0.1.0] - 2026-04-23

### Added
- 基本パッケージの初期機能を追加（KabuSys 日本株自動売買システム初版）。
  - パッケージメタ情報: __version__ = "0.1.0"、公開モジュール群を __all__ で定義。

- 設定関連ツール
  - 対話式設定ウィザード CLI（kabusys.config_setup）
    - .env ファイルの初期作成・更新を対話式に支援するウィザードを実装。
    - 各項目に説明、選択肢、シークレット入力、デフォルト値をサポート。
    - .env の読み込み/書き込み処理を実装（既存値の再利用、シークレットは表示をマスク）。
    - .env ファイルのテンプレートヘッダを出力し、".env を絶対に Git にコミットしないこと" を注意喚起。
  - 起動前設定検証 CLI（kabusys.validate_config）
    - .env と config/*.yaml の設定不備を起動前に検出する CLI を提供。
    - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - 環境変数のプレースホルダ検出（末尾が "_here"、または "your_value" の場合は警告）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（有効値を検証、live は警告）。
    - DUCKDB/SQLite パスの親ディレクトリ存在確認（存在しない場合は警告）。
    - config/*.yaml の存在確認と（PyYAML インストール時は）パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の危険値検出等）。
    - --strict オプションによる警告を失敗（exit(1)）扱いにするモード。

- 環境変数・設定読み込み（kabusys.config）
  - プロジェクトルート自動検出: .git または pyproject.toml を起点に親ディレクトリ探索（配布後も CWD に依存しない）。
  - .env 読み込みロジック
    - export プレフィックス対応、クォート（' "）内のバックスラッシュエスケープ対応、インラインコメントの取り扱いなどを考慮した行パーサを実装。
    - 読み込み優先順位: OS 環境 > .env > .env.local（.env.local は上書き、ただし OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - Settings クラス（設定プロパティの集約）
    - 必須変数取得時の検証（未設定時に ValueError を送出）。
    - 各種設定プロパティを提供（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、PID/KILL フラグパス、閾値、env/log_level 等）。
    - PAPER_FILL_MODE の妥当性チェックや、paper_trading 用の専用 SQLite パスを提供。
    - env / log_level の妥当性チェックで不正値は ValueError。

- 実行スクリプト
  - run_execution（kabusys.run_execution）
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出（stop_requested.flag）およびクリーンなシャットダウン。
  - run_monitoring（kabusys.run_monitoring）
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。

- 発注関連コア（execution サブパッケージ）
  - OrderRecord（kabusys.execution.order_record）
    - 注文状態を列挙した状態マシン（OrderState）と、状態遷移の検証ロジックを持つデータクラスを実装。
    - 許可遷移テーブルと、不正遷移時に raise される InvalidStateTransitionError を実装。
    - 状態遷移時に updated_at を UTC で自動更新、broker_order_id / filled_qty / avg_fill_price / error_message の適切な更新をサポート。
  - OrderManager（kabusys.execution.order_manager）
    - DB（OrderRepository）と OrderRecord を組み合わせ、外向きに発注フローを提供。
    - create_order: signal_id 単位の重複検出（DB のユニーク制約違反を DuplicateOrderError に変換）。
    - send_order: 送信のクラッシュ耐性を考慮した 2 相永続化パターンを実装（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted へ遷移）。OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order: broker 側の状態照合で状態・約定情報を同期（未設定の broker_order_id や broker が見つからない場合を考慮）。OrderSent→Filled の直遷移が不許可なため OrderAccepted を経由する処理を実装。
    - cancel_order: キャンセル不可能な状態チェックおよび broker.cancel_order 呼び出し、状態遷移の適用。
    - キャンセル不可能な状態集合の明示（Filled をキャンセル不可と扱う点に注意）。
  - ExecutionEngine（kabusys.execution.execution_engine）
    - シグナルの読み込み（DuckDB）→ Gate1/Gate2 を経ての発注ループ、WebSocket push のドレインループを実装。
    - リスク管理（RiskManager）との統合: check_signal / check_execution / check_metrics を利用し、Circuit Breaker やレート制限をハンドリング。
    - 発注成功/失敗/保留（pending）時の処理と監視DBへのイベント記録（MonitoringDB が与えられた場合）。
    - position_entries テーブルへ約定日の追記（next_trading_day を利用） — BUY は entry、SELL は sell_date 更新（pending の扱い考慮）。
    - WebSocket スレッド（broker.stream_push が存在する場合）を別スレッドで起動し、受信 payload を _push_queue に投入。
    - push 処理で broker からの OrderID を基に同期を行い（client_order_id マッピング）、Gate3（ドローダウン）を評価して必要なら kill_switch を発動。
    - kill_switch は全 active 注文をキャンセルし、ループ停止を行う公開 API として提供。
    - PID ファイルの書き込みと起動時 kill.flag の扱い（KILL_FLAG_CLEAR_ON_START による自動クリアオプション）を実装。
    - テスト用に _process_signals / _drain_push_queue を直接呼べる設計。

- Broker クライアント（kabusys.execution.kabu_client）
  - KabuStation REST API クライアントを実装（同期 httpx.Client 使用、将来の async 置換を想定）。
  - トークン管理: _get_token による遅延初期化と早朝失効時の自動再取得。
  - 認証付きリクエストで 401 を検知した場合はトークン再取得 → 1 回リトライを実行。
  - レスポンス JSON パースエラーやタイムアウト・ネットワークエラーを BrokerAPIError に変換。
  - 429 レスポンスは RateLimitError を送出。
  - kabu の注文状態コードを内部ステータス文字列にマッピング（open/partial/filled/cancelled/rejected）。
  - WebSocket 受信用の stream_push インターフェースを想定している点を明記。

- モニタリング / データベース
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を用いた監視 DB の確保。
  - run_monitoring / run_execution での sqlite3 / duckdb 接続確立とクローズ処理を追加。

- ユーティリティ
  - ロギングセットアップ、プロセス優先度設定ユーティリティ呼び出しを実行スクリプトから利用。
  - stop_requested.flag / execution.pid などの運用用フラグ/ファイルの取り扱いを実装。

### Changed
- 初回リリースのため変更履歴なし（このバージョンが初出）。

### Fixed
- 初回リリースのため修正履歴なし（後続リリースで細かい不具合修正予定）。

### Notes / 致命的な運用上の注意
- .env は絶対にソース管理にコミットしないこと（config_setup の出力にも明記）。
- KABUSYS_ENV=live を設定する際は LINE 通知や KILL_FLAG_CLEAR_ON_START など本番用のガードを十分に設定してください（validate_config に警告/エラーを出力する機能あり）。
- PAPER_TRADING モードでは本番の monitoring DB とは別に paper_trading 用 SQLite が使用されます（データ分離に注意）。

---

今後のリリースでは以下を予定しています（例）:
- Broker API 抽象層の拡張とテストカバレッジ強化
- 非同期 I/O（httpx.AsyncClient）対応
- config/ YAML の詳細スキーマ検証（現在は PyYAML の有無に応じてパースのみ）
- 監視 / リコンシリエーション関連の堅牢化と運用向けメトリクス強化

（以上）
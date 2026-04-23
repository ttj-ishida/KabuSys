Keep a Changelog
=================

すべての重要な変更をこのファイルで記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

フォーマット:
- バージョン番号（年月日）
- カテゴリ: Added, Changed, Deprecated, Removed, Fixed, Security

0.1.0 - 2026-04-23
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコアコンポーネントを追加。
- 環境設定/読み込み
  - .env 自動ロード機構を実装（プロジェクトルートの .env / .env.local を自動読み込み。OS 環境変数は保護され上書きされない）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを実装: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理等の挙動を明示的に扱う。
  - Settings クラスを提供し、環境変数を型付きプロパティとして取得（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path 等）。
  - 一部の設定値にバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。無効な場合は ValueError を送出。

- 設定ウィザード CLI
  - python -m kabusys.config_setup による対話式ウィザードを追加。
  - シークレット項目のマスク表示、選択肢・デフォルトの提示、既存 .env の読み込み・再利用、.env 書き込みテンプレートを提供。
  - .env 作成後の次ステップ案内（validate_config の実行推奨）を表示。

- 設定検証 CLI
  - python -m kabusys.validate_config による起動前検証ツールを追加。
  - 必須/任意環境変数の存在確認、プレースホルダの検出（末尾が "_here" や "your_value" の警告）、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック等を実施。
  - config/*.yaml（system_config.yaml 等）の存在確認と、PyYAML が利用可能な場合は YAML パース検証を実行。PyYAML 未導入時は警告でスキップ。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険設定の警告）。
  - --strict フラグで警告も失敗扱い（exit code 1）にできる。

- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - プロセス優先度設定（high）、PID ファイル書き出し、停止フラグ（data/stop_requested.flag）検出処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 発注関連コンポーネント（execution パッケージ）
  - ExecutionEngine: Signal Queue Pull 型発注エンジンを実装。
    - 8:50 にシグナル処理開始、9:10 に発注締切、15:30 にセッション終了の時間管理を実装。
    - WebSocket push のドレインループ、push 受信時の同期処理、Gate3（ドローダウン監視）判定での kill_switch 発動等を実装。
    - ポジション登録用に DuckDB へ position_entries を書き込む処理（next_trading_day を使用）。
    - 発注レイテンシや監視ログを監視DBへ送るフックを用意（MonitoringDB 経由）。
  - OrderRecord: 注文状態マシン（OrderState enum）と遷移ロジックを純粋モデルとして実装。
    - 許可済み状態遷移表を定義し、不正遷移時は InvalidStateTransitionError を送出。
    - transition_to で updated_at を UTC で更新し、broker_order_id, filled_qty, avg_fill_price, error_message をキーワードで安全に更新。
  - OrderManager: OrderRecord と OrderRepository（SQLite 接続）を組み合わせた外向け API を実装。
    - create_order: signal_id 単位で active 注文の重複を防止（DuplicateOrderError）。
    - send_order: 2 相永続化戦略を採用（OrderSent を DB に先に保存 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移等）し、クラッシュ時の整合性回復を考慮。
      - OrderRejectedError / OrderSentPendingError の扱いを明確化。OrderSentPendingError は broker_order_id を保存して再スロー。
    - sync_order: broker の get_order_status を用いた状態同期処理（部分約定の進行は状態を変更せずフィールドのみ更新するケースを含む）。
    - cancel_order: キャンセル不可状態のチェック、broker API 呼び出し、Cancelled への遷移を実装。
  - Reconciler / RiskManager 等との連携ポイントを確立（起動時のリコンシリエーション呼び出し、Gate チェックやレート制限/Circuit Breaker 判定の扱い）。

- ブローカークライアント
  - KabuStationClient: kabu ステーション REST API 向け同期クライアントを実装（httpx 利用）。
    - トークン取得の遅延初期化と 401 時の自動再取得・リトライ実装。
    - レスポンス JSON パース失敗、タイムアウト、ネットワークエラー、429 Rate Limit、5xx サーバーエラー等を BrokerAPIError / RateLimitError として扱う。
    - kabu ステーションのステータスコード → 内部ステータス文字列のマッピングを定義。
    - 将来の async 対応のため構造を整備（httpx.AsyncClient へ移行可能な設計）。

- その他ユーティリティ/運用
  - monitoring/monitoring_db の初期化フック（init_monitoring_db）を用いて監視テーブルを保証。
  - utils: logging_setup, process_priority などの運用ユーティリティを使用してログとプロセス優先度を管理。
  - 停止/kill フラグ（data/stop_requested.flag / kill.flag）による挙動制御を実装。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

Security
- .env は絶対に Git にコミットしない旨を .env テンプレートに明記（config_setup の出力）。

Notes / 注意点
- validate_config は PyYAML 未導入時に YAML 内容検証をスキップして警告を出します。YAML 内容の検証を行うには PyYAML をインストールしてください。
- Settings は env/log level 等の不正値で ValueError を投げます。起動前に validate_config の実行を推奨します。
- Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番パス）を使用します。monitoring の DB を分離したい場合は適切に設定を上書きしてください。
- paper_trading モードでは execution は paper 用 SQLite を使用して本番 DB と分離します。
- kill_flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 によって許可できますが、本番では 0 を推奨します。

Deprecated
- なし

Removed
- なし

Fixed
- なし

-- End of changelog --
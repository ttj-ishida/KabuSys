CHANGELOG
=========

全般
----
この CHANGELOG は "Keep a Changelog" の慣例に従っています。  
各リリースには主な追加機能（Added）、変更（Changed）、修正（Fixed）を日本語で記載しています。  
記述はソースコードの内容から推測して作成しています。

Unreleased
----------
- （なし）

[0.1.0] - 2026-04-22
--------------------
Added
- 基本機能の初期実装を追加。
  - Execution（発注）エンジン（kabusys.execution.execution_engine）
    - Signal Queue による発注フロー（シグナル読み込み → Gate1/Gate2 チェック → 発注 → position_entries 更新）。
    - WebSocket プッシュのドレイン処理と Gate3（ドローダウン監視）による kill switch 発動。
    - run_session により 8:50〜9:10 のシグナル処理、9:10〜15:30 の push ドレインを実行。
    - PID ファイル書き出し、kill.flag の起動時/ループ内チェック、KILL_FLAG_CLEAR_ON_START の扱いを実装。
  - OrderRecord（状態遷移モデル）（kabusys.execution.order_record）
    - 注文状態の列挙 OrderState と遷移許可テーブルを実装。
    - transition_to による遷移検証と updated_at 自動更新。
    - 不正遷移時に InvalidStateTransitionError を発生。
  - OrderManager（外向き API）（kabusys.execution.order_manager）
    - create_order / send_order / sync_order / cancel_order を実装。
    - DuplicateOrderError の検出（DB 部分ユニークインデックス違反の変換対応）。
    - send_order における「2 相永続化」パターン（OrderSent の永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted）でクラッシュ耐性を確保。
    - OrderSentPendingError（注文番号は得られたが約定しない/保留）を特別扱い。
    - sync_order による broker 側のステータスとの同期と部分約定の更新。
    - cancel_order でキャンセル不可能な状態のチェック（Closed/Cancelled/Rejected/Filled をキャンセル不可に指定）。
  - Broker API 周りの抽象（kabusys.execution.broker_api を参照する設計）。
  - KabuStationClient（kabu ステーション REST クライアント）（kabusys.execution.kabu_client）
    - httpx を用いた同期クライアント実装。
    - トークン取得の遅延初期化、401 時のトークン再取得＆一回リトライを実装。
    - HTTP 429 を RateLimitError にマッピング、タイムアウト/ネットワーク例外を BrokerAPIError に変換。
    - WebSocket push 受信用の stream_push を想定した設計（存在しない場合はスキップ）。
  - Execution 起動スクリプト（python -m kabusys.run_execution）
    - paper_trading 環境のための専用 SQLite（paper_trading.db）使用ロジック。
    - プロセス優先度設定（high）を起動時に適用。
    - stop flag による安全な起動／停止処理。
  - Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
    - SystemMonitor ポーリングループを実装。MONITOR_POLL_INTERVAL で間隔指定可（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用するよう設計。
  - 設定管理（kabusys.config）
    - .env 自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順と override / protected（OS 環境変数保護）による上書き制御。
    - _parse_env_line により export プレフィックス、クォート付き値、エスケープ、インラインコメントの取り扱いをサポート。
    - Settings クラスを提供し、環境変数から型付きプロパティを取得。値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）で不正値は ValueError を送出。
  - 設定ウィザード CLI（python -m kabusys.config_setup）
    - 対話式に .env を生成/更新するウィザードを追加。
    - シークレット値のマスク表示、選択肢・デフォルト値の提示、変更の保存確認を実装。
  - 設定検証ツール（python -m kabusys.validate_config）
    - .env と config/*.yaml の存在・妥当性検査を行う CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML が無ければ警告してスキップ）。
    - --strict オプションで警告も失敗扱い（exit code 1）にできる。
  - 監視 DB 周りの初期化ユーティリティ（kabusys.monitoring.monitoring_db を使用する設計）と発注時の監視記録（latency 等）を埋め込み可能な設計。
  - ロギング・プロセス優先度設定ユーティリティの利用（kabusys.utils.logging_setup / process_priority を各 run スクリプトで適用）。

Changed
- アーキテクチャ上の設計に関する改善点（初期実装段階の設計方針を明示）。
  - 発注フローでクラッシュ耐性を高めるため、OrderSent の事前永続化 → broker_order_id の永続化 → OrderAccepted という段階的コミットを採用。
  - paper_trading 環境では SQLite を本番 DB と分離（paper_trading.db）してテスト／検証が本番データに影響しないように設計。
  - Monitoring は環境に依らず本番の sqlite_path を参照する方針を採用（運用上の監視は一元化するため）。
  - ExecutionEngine 内での kill_switch の適用範囲を明確化（全 active 注文のキャンセル、スレッド停止制御）。
  - .env 読み込みは環境変数保護（protected set）を導入して OS 環境の上書きに注意。

Fixed
- 例外・エラー処理の堅牢化。
  - KabuStationClient のレスポンス JSON パース失敗やタイムアウト・ネットワークエラーを明示的な BrokerAPIError に変換。
  - Token 取得・認証周りで 401 発生時に再取得してリトライすることで早朝のトークン失効に対処。
  - MONITOR_POLL_INTERVAL の不正値に対してデフォルトにフォールバックする処理を追加（値が 1 未満や非整数のケースへの対応）。
  - config/*.yaml のパースで PyYAML が未インストールの場合は警告してスキップするフォールバックを追加。
  - OrderManager.create_order が sqlite の部分ユニーク制約違反を検出して DuplicateOrderError に変換（原因の隠蔽を最小化するため、CHECK など他の制約違反は再スロー）。

Notes / 実装上の注意
- settings（kabusys.config.settings）はプロパティ取得時に値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行い、不正値だと ValueError を投げます。実行前に validate_config を使って検証することを推奨します。
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- config_setup によって生成される .env はセキュリティ上 Git にコミットしないでください（ヘッダーにも注意書きを出力）。
- send_order の設計はクラッシュ後の再照合（Reconciliation）を前提としており、OrderSent レコードや broker_order_id の永続化の有無に応じて sync_order / reconciler が状態回復を行います。
- KABUSYS_ENV=live の場合は追加のガード（LINE トークン設定確認、KILL_FLAG_CLEAR_ON_START の危険性通知）があるため注意してください。

今後の予定（推測）
- BrokerAPI の抽象に対する他ブローカー（MockBrokerClient など）の実装追加（paper_trading 用）。
- テストカバレッジの拡充（状態遷移・リコンシリエーション・エラーパス）。
- 非同期対応（httpx.AsyncClient への移行）や WebSocket 処理の改善。
- config/*.yaml のスキーマ検証（PyYAML + jsonschema 等）導入。

---
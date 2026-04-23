# Changelog

すべての注目すべき変更を記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-23

### Added
- 全体
  - 初版リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 設定管理 / CLI
  - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサーは以下をサポート:
    - コメント行、`export KEY=val` 形式、シングル/ダブルクォート付き値（エスケープ処理含む）、インラインコメントの扱い（クォート無しで # の直前が空白/タブの場合コメント扱い）。
  - 設定ウィザード CLI を追加（`python -m kabusys.config_setup`）。
    - 対話式に .env を作成/更新可能。
    - J-Quants / kabu ステーション / DB パス / LINE トークン等の主要設定項目を用意。
    - 生成される .env に注意書きを付与（Git にコミットしないよう推奨）。
  - 設定検証 CLI を追加（`python -m kabusys.validate_config`）。
    - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の未設定検出。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証と警告。
    - DUCKDB/SQLite のパス親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と PyYAML によるパース検証（PyYAML 未導入時はスキップ）。
    - `--strict` オプションで警告も FAIL として扱い exit(1) にする。

- 設定オブジェクト
  - `kabusys.config.Settings` クラスを実装。
    - 環境変数からプロパティを参照する統一インターフェースを提供（例: `settings.jquants_refresh_token`）。
    - 一部設定値は厳密チェックを行い、不正値で ValueError を送出（例: `KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE`）。
    - DB パス（DuckDB / SQLite）、pid/kill flag パス、監視閾値などを提供。
    - paper_trading 用に専用 SQLite パス (`PAPER_TRADING_SQLITE_PATH`) をサポートし、本番 DB と分離。

- 実行 / 監視ランナー
  - `run_execution` スクリプトを追加（`python -m kabusys.run_execution` 想定）。
    - プロセス優先度設定、PID 管理、stop flag / kill flag による起動/停止制御。
    - paper_trading 時は MockBroker と専用 SQLite を使用。
    - DuckDB と SQLite を同時に使用してデータ処理・監視を行う。
  - `run_monitoring` スクリプトを追加（`python -m kabusys.run_monitoring` 想定）。
    - `MONITOR_POLL_INTERVAL` でポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。

- 実行エンジン / 発注ロジック
  - `ExecutionEngine` を実装（signal queue ベースの発注フロー）。
    - シグナル処理フェーズ（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）を分離。
    - kill.flag の検出や起動時の kill_flag_clear_on_start による挙動を実装。
    - PID ファイル作成/削除を実装。
    - WebSocket push を別スレッドで処理し、受信 payload を queue 経由で同期処理へ渡す。
    - 発注後、position_entries テーブルにエントリを付与して最短保有日数等の制御に利用。
    - 発注失敗時や監視DB 書き込み失敗時はログ出力して発注フローは継続。

  - Order Manager / State Machine
    - `OrderRecord`（状態遷移ロジック）を純粋ロジックとして実装:
      - 状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
      - 許可遷移（_ALLOWED_TRANSITIONS）に基づく検証。違反時は `InvalidStateTransitionError` を raise。
      - updated_at は UTC の現在時刻で自動更新。broker_order_id / filled_qty 等のオプション更新をサポート。
    - `OrderManager` を実装:
      - create_order: signal_id の重複チェック（部分ユニーク制約・DB 制約に基づく DuplicateOrderError ハンドリング）。
      - send_order: 2 相永続化を採用してクラッシュ安全性を向上。
        - Step1: OrderSent に遷移して永続化（broker 呼び出し前）。
        - Step2: broker.send_order を呼ぶ。
        - Step3a: broker_order_id を先に DB に保存（state は Sent のまま）。
        - Step3b: OrderAccepted に遷移して保存。
        - OrderRejectedError は Rejected に遷移して保存。
        - OrderSentPendingError は broker_order_id を永続化して再送出（Reconciliation の対象）。
      - sync_order: broker 側の状態を取得してローカル状態を同期。部分約定の進行は差分更新を行う。
      - cancel_order: 取消可能判定（終端状態は不可）後 broker.cancel を呼び Cancelled に遷移。

  - Reconciliation / リスク管理連携（エンジンに組み込み）
    - 起動時に reconciler を呼んで既存注文の同期を行い、問題をログ化（例: synced / no_status / position_discrepancies）。
    - 発注前に Gate1（シグナルレベル）/ Gate2（実行レベル、レート制限）/ Gate3（ドローダウン監視）を実行。
    - Gate2 のレート制限は最大 3 回リトライ。Circuit Breaker オープン時はシグナルループを停止。
    - Gate3 NG（ドローダウン等）で kill_switch を発動し、全 active 注文をキャンセル。

- ブローカー API クライアント
  - `KabuStationClient` を実装（同期 httpx クライアント）。
    - トークン取得の遅延初期化と自動再取得（401 リトライ）。
    - レスポンス JSON パース失敗やネットワークエラーを `BrokerAPIError` に変換。
    - 429 は `RateLimitError` を送出。
    - WebSocket push（stream_push）実装がある場合、ExecutionEngine の websocket ワーカーで利用。

- 監視 DB 初期化
  - `init_monitoring_db` を呼んで監視用 SQLite のテーブル存在を保証（冪等）。

- ユーティリティ
  - ロギング設定、プロセス優先度設定ユーティリティを利用して起動時に適用。

### Changed
- （初版のため変更履歴なし）

### Fixed
- （初版のため修正履歴なし）

### Security
- .env の扱いに関して明示的に「絶対に Git にコミットしないこと」を .env ヘッダに記載。

---

注:
- 本 CHANGELOG はソースコードの内容から機能・挙動を推測して作成しています。実際のリリースノートやドキュメントとは差分がある可能性があります。コードの動作や仕様変更があった場合は適宜更新してください。
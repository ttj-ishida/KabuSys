# Changelog

すべての変更は Keep a Changelog 準拠で記載します。  
フォーマット: https://keepachangelog.com/（日本語）

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定 / 環境変数管理
  - Settings クラスを追加し、環境変数から各種設定値を取得できるように実装。
    - J-Quants, kabuステーション API, LINE, データベース、監視、システム設定をプロパティとして提供。
    - env 値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の妥当性チェック）を実装。
    - Paper Trading 用の分離された SQLite パス（PAPER_TRADING_SQLITE_PATH）をサポート。
    - デフォルト値や Path への変換（expanduser）を自動で適用。
    - kill_flag の自動クリアフラグ（KILL_FLAG_CLEAR_ON_START）をサポート。

  - .env の自動読み込み機能を追加（デフォルトで自動ロード）。
    - プロジェクトルート検出: .git または pyproject.toml を基準に決定（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - .env の読み込みは OS 環境変数を保護するため protected set を利用し上書きを制御。
    - _parse_env_line により以下をサポート:
      - export KEY=val 形式
      - シングル/ダブルクォートされた値（バックスラッシュエスケープを処理）
      - クォート無しの場合のインラインコメント処理（# の前が空白の場合のみコメントと解釈）

- .env 対話式ウィザード
  - `kabusys.config_setup` による CLI ウィザードを追加。
    - 主要な設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を対話式に作成/更新できる。
    - シークレット項目は表示をマスク。
    - 選択肢検証やデフォルト値表示をサポート。
    - 作成される .env はテンプレート形式で安全に書き込まれる（※ .env を Git にコミットしない旨の注意を出力）。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。
    - 必須環境変数の存在チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - プレースホルダ（*_here / your_value）に対する警告。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（有効値を定義）。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml（system_config.yaml など）の存在チェック。PyYAML があればパース検証を実行。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の安全性チェック）。
    - `--strict` オプションで警告も失敗扱い（exit 1）にできる。
    - INFO/WARNING/ERROR を出力して適切な終了コードを返す。

- 実行系スクリプト
  - run_execution:
    - ExecutionEngine の起動スクリプトを追加。
    - プロセス優先度を high に設定する仕組みを呼び出す。
    - paper_trading 環境では paper_trading 用 SQLite を使用し本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）を監視してセッションの停止を行う。
  - run_monitoring:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、非正の値はデフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了し DB 接続をクローズする。

- 発注 / 注文管理コンポーネント
  - OrderRecord:
    - オーダー状態を表す OrderState 列挙と状態遷移ルールを実装。
    - transition_to() による遷移検証（不正遷移は InvalidStateTransitionError を送出）。
    - 作成時の created_at/updated_at 更新、broker_order_id / filled_qty / avg_fill_price / error_message のオプション更新に対応。
  - OrderManager:
    - DB（OrderRepository）と OrderRecord を組み合わせた外向き API を実装:
      - create_order: signal_id 単位で重複発注を防止（部分的に DB の unique 制約違反を DuplicateOrderError に変換）。
      - send_order: 「OrderCreated → OrderSent を永続化」してから broker API 呼び出しを行う二相永続化を実施（クラッシュ安全性を考慮）。
        - 成功時は broker_order_id を先に保存し、その後 OrderAccepted へ遷移して保存。
        - OrderRejectedError を受けた場合は Rejected に遷移。
        - OrderSentPendingError（注文番号発行だが約定しないケース）では broker_order_id を保存したまま例外を再送出（Reconciliation 対象）。
      - sync_order: broker の状態照会結果に基づき状態・部分約定情報を同期。OrderSent→(partial/filled) の場合は OrderAccepted を経由して遷移。
      - cancel_order: キャンセル不可状態のチェックを行い、broker API を呼び出して Cancelled に遷移。
    - send_order の設計は Reconciliation を考慮しており、クラッシュ後でも状態復旧が可能となる永続化順序を採用。

  - ExecutionEngine:
    - Signal Queue Pull 型発注エンジンを実装。
    - セッションタイミング:
      - シグナル処理: 08:50 - 09:10（signal_send_start / signal_send_end）
      - Push ドレイン: 09:10 - 15:30（market_close）
    - _process_signals(): シグナル読み込み → Gate 1（シグナルレベル）/ Gate 2（エグゼキューションレベル、レート制限）を通じて発注。
      - size_multiplier 適用（BUY のみ、最小単位を 100 株で切り捨て）。
      - Gate 2 は最大3回リトライ、サーキットブレーカーではシグナルループを停止。
      - 発注後に position_entries テーブルへ約定予定日（翌営業日）を記録（BUY pending も記録、SELL pending は記録しない）。
      - 監視用 DB（MonitoringDB）がある場合、発注イベントをログに書き込む。
    - _websocket_worker(): broker が WebSocket push をサポートする場合に push を受け取り _push_queue に投入。
    - _drain_push_queue()/_handle_push(): push を処理して sync_order を呼び出し、Gate 3（ドローダウン監視）によって必要なら kill_switch を発動。
    - kill_switch(): 全 active 注文をキャンセルし、ループ停止を行う。外部から stop() を呼ぶことで同様の振る舞いを可能にしている。
    - 起動時に PID ファイルを書き込み、終了時に削除する。起動時 kill.flag の取り扱いは KILL_FLAG_CLEAR_ON_START に依存。

  - Broker / KabuStation クライアント
    - KabuStationClient を実装（httpx 同期クライアント）。
      - API トークンの遅延取得（_get_token）と 401 時のリトライ処理を自動化。
      - レスポンス JSON パース失敗やタイムアウト／ネットワークエラーを BrokerAPIError に変換。
      - 429 を RateLimitError にマッピング。
      - 内部での注文状態マップ（kabu station の数値コード → 内部文字列）を定義。

- 監視関連
  - Monitoring の初期化（init_monitoring_db）呼び出しが各起動スクリプトで行われ、監視用テーブルを冪等的に保証。
  - run_monitoring はデフォルトで MONITOR_POLL_INTERVAL=60 秒（設定経由で上書き可能）。0以下や不正値はデフォルトにフォールバックし、警告を出力。

### Notes / 実装上の注意
- プロジェクトルート検出を行うため、パッケージ配布後も .env 自動ロードが動作するよう設計されている（CWD 非依存）。
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時の干渉回避用）。
- 多くの設計上のトレードオフはクラッシュ安全性と Reconciliation（注文状態の照合）を重視している（OrderSent の永続化順序や broker_order_id の先保存など）。
- Monitoring は環境にかかわらず本番 sqlite_path を使用するため、監視が本番データにアクセスする点に注意。
- 一部のバリデーション／パース（YAML の検証など）は optional（PyYAML が未インストールの場合はスキップされ警告）になっている。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

---

（補足）本 CHANGELOG はコードベースの実装から推測して作成しています。実際のユーザー向けリリースノートでは追加の文言（既知の制限、互換性、マイグレーション手順等）を追記することを推奨します。
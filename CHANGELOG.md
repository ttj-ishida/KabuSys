# Changelog

すべての重要な変更は「Keep a Changelog」の慣習に従って記載しています。  
このファイルはコードベースの現在の状態から推測して作成した初期リリース向けの変更履歴です。

最新版: [0.1.0] — 2026-04-23

## [Unreleased]
（現時点のスナップショットがそのまま 0.1.0 の初回リリース相当のため空）

## [0.1.0] - 2026-04-23

### Added
- パッケージ基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理
  - 環境変数/`.env` 管理モジュールを追加（kabusys.config）。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出して `.env` / `.env.local` を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - `.env` の行パーサを実装。`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。
    - 読み込み時の上書き挙動: OS 環境変数を保護する protected 機能を持つ。
    - 必須環境変数取得用の `_require()` 実装（未設定時は ValueError を送出）。
    - Settings クラスを実装し、プロパティ経由で各種設定取得（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、KABUSYS_ENV / LOG_LEVEL 等）。値検証（有効な列挙値チェック）や変換（Path, float, bool）を行う。

- 設定ウィザード CLI
  - `kabusys.config_setup` を追加。対話式で `.env` を初期作成・更新するウィザード。
    - 各設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）に対するプロンプトを実装。
    - シークレット項目は出力時にマスク表示。
    - 既存の `.env` の読み込みと Enter による既存値の再利用をサポート。
    - 最終確認後に `.env` を安全に書き出す（注意書きヘッダ付き、Git へコミットしない旨を明示）。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。起動前に `.env` と config/*.yaml の設定不備を検出する CLI。
    - 必須 / 任意環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）。
    - KABUSYS_ENV の妥当性チェックおよび `live` の際の注意喚起。
    - LOG_LEVEL の妥当性チェック。
    - DUCKDB / SQLITE のパスの親ディレクトリ存在確認（存在しない場合は警告。起動時に作成される可能性あり）。
    - config/*.yaml の存在確認と、PyYAML がインストールされている場合は YAML のパース検証（PyYAML 未インストール時はスキップして警告）。
    - KABUSYS_ENV=live のときの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START が 1 の危険性など）。
    - 出力: INFO / WARNING / ERROR を表示し、`--strict` オプションで警告も失敗（exit code 1）として扱う。

- 実行エントリスクリプト
  - 実行エンジン起動スクリプト `kabusys.run_execution` を追加。
    - 起動時にプロセス優先度を "high" に設定（ユーティリティ経由）。
    - paper_trading 環境では paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ / PID ファイルの扱い、停止フラグ検知で起動拒否や自動クリアの挙動を実装。
    - 各種依存コンポーネント（BrokerClientFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler など）を組み合わせてセッション実行。
  - 監視ループ起動スクリプト `kabusys.run_monitoring` を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告）。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用する。停止フラグ検知でループ終了。

- Execution サブシステム（発注ロジック）
  - OrderRecord（状態マシン）を追加（kabusys.execution.order_record）。
    - 注文状態列挙 OrderState と許可遷移マップを定義。
    - transition_to() による厳格な遷移検証とメタデータ更新（broker_order_id, filled_qty, avg_fill_price, error_message）。
    - 不正遷移時には InvalidStateTransitionError を送出。
  - OrderManager を追加（kabusys.execution.order_manager）。
    - DB 上の重複 signal チェック（DuplicateOrderError の送出）。
    - create_order(), send_order(), sync_order(), cancel_order() の外向け API を実装。
    - send_order() はクラッシュ耐性を考慮した「2相永続化」戦略を採用:
      1) OrderCreated → OrderSent を先に永続化
      2) broker API 呼び出し
      3a) 成功時に broker_order_id を先に保存（state は Sent のまま）
      3b) OrderAccepted に遷移して保存
      - OrderRejectedError / OrderSentPendingError（注文番号は取得したが約定しないケース）等に対応。
    - sync_order() で broker 側の最新ステータスと同期（部分約定の進行更新も考慮）。OrderSent→Filled/Partial の場合は OrderAccepted を中継して遷移。
    - cancel_order() は端状態判定を行い、可能なら broker API にキャンセル要求を送り Cancelled に遷移。
  - ExecutionEngine を追加（kabusys.execution.execution_engine）。
    - シグナルの読み込み（DuckDB）、Gate1/2（シグナル・実行レベルのリスクチェック）、発注、ポッシュ（kabu push）ドレイン、Gate3（ポートフォリオメトリクスドローダウン監視）を実装。
    - size_multiplier 適用、発注遅延（latency）測定、監視 DB への発行イベント記録、例外時のフォールトトレランスなどを実装。
    - WebSocket スレッドによる push 受信と同期処理をサポート（stream_push を持たない broker はスキップ）。
    - kill_switch() により全 active 注文のキャンセルを実行し、ループを停止する機能を提供。
    - セッションの時間帯（8:50〜9:10 シグナル処理、9:10〜15:30 push ドレイン）をデフォルトで設定。
    - 起動時に Reconciler によるリコンシリエーションを試行（例外が出ても継続）。
    - PID ファイル管理（書き込み・削除）を実装。

- kabu station クライアント
  - KabuStationClient を追加（kabusys.execution.kabu_client）。
    - httpx.Client を使った同期 REST クライアント実装（将来的な async 対応を想定）。
    - トークン取得の遅延初期化と 401 発生時の自動再取得リトライを実装。
    - HTTP タイムアウト・ネットワーク例外は BrokerAPIError にラップして送出。
    - レスポンスの JSON パース不正は BrokerAPIError に変換。
    - HTTP 429 は RateLimitError にマッピング。
    - kabu ステーションのステータスコードを内部ステータス（open/partial/filled/cancelled/rejected）へマップする表を実装。

- その他ユーティリティ参照
  - logging_setup, process_priority, monitoring_db, Reconciler 等のユーティリティ／モジュールを統合して起動フローを構成。

### Changed
- （初回リリースのため特記すべき「変更」はなし。すべて新規実装として記載）

### Fixed
- （初回リリースのため特記すべき「修正」はなし）

### Notes / Usage
- .env の自動読み込みは OS 環境変数を保護しているため、OS 環境変数を優先して使用します。.env.local は .env より優先して上書きされます。
- validate_config にて PyYAML 未インストール時は YAML の内容検証をスキップします（警告が出ます）。PyYAML を導入すると config/*.yaml のパース検証が行われます。
- run_execution は paper_trading 環境時に paper_trading 用の SQLite を使用し、本番 DB とデータを分離します。
- Execution の send_order はクラッシュ時に DB 上に OrderSent レコードや broker_order_id が残る可能性を考慮した設計になっており、Reconciler による回復を想定しています。
- KABUSYS_ENV=live の際は本番用の注意喚起や追加チェックが行われます。特に Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険な設定です。

---

「初期リリース相当」の内容をコードベースから推測してまとめました。必要であれば各機能ごとにより細かい変更点や既知の制限事項（既知の例外/エラーハンドリング、想定される運用手順など）を追記します。どの程度詳細に記載したいか指示をください。
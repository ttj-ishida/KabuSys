# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成しました。

※ バージョン番号はパッケージ初期リリースの __version__ = "0.1.0" に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-22

### Added
- 基本パッケージ情報
  - パッケージのエントリポイントとバージョンを追加（__version__ = "0.1.0"）。

- 環境変数 / 設定管理
  - Settings クラス（kabusys.config）を追加。環境変数から各種設定を取得するプロパティ群を提供。
    - J-Quants / kabu API / LINE / DB パス / pid/kill flag / リソース閾値等を扱うプロパティを実装。
    - env/log level 等の値検証（不正値で ValueError を送出）。
    - PAPER_FILL_MODE の妥当性チェックを実装（有効値: instant, partial, never, reject）。
  - .env ファイルの自動読み込み機能を追加
    - プロジェクトルート（.git または pyproject.toml を基準）を自動検出し、.env / .env.local を読み込む（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーを実装（_parse_env_line）
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、行内コメントの扱いなどを考慮した堅牢なパース。

- 対話式設定ウィザード CLI
  - kabusys.config_setup により .env の初期作成・更新を支援するウィザードを追加。
    - シークレット項目はマスク表示。
    - 選択肢・デフォルト・説明を表示して対話的に入力。
    - _write_env で .env のテンプレート的な書き出しを行う。
    - 利用方法: python -m kabusys.config_setup

- 設定検証 CLI
  - kabusys.validate_config を追加。起動前に環境変数と config/*.yaml の存在や基本的整合性をチェック。
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD を検査。
    - KABUSYS_ENV, LOG_LEVEL の妥当性チェック。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml の存在確認と、PyYAML がインストールされている場合はパース検証（PyYAML 未導入時はパーススキップして警告）。
    - KABUSYS_ENV=live のときは追加のガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告も失敗扱い（exit code 1）。
    - 利用方法: python -m kabusys.validate_config

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用し本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、stop フラグ検出ロジックを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバック。

- Execution / 発注基盤
  - ExecutionEngine（kabusys.execution.execution_engine）を追加
    - シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）のセッション制御。
    - kill.flag の検査と起動時の KILL_FLAG_CLEAR_ON_START 動作（クリア or 起動拒否）。
    - PID ファイル書き込みと終了時のクリーンアップ。
    - WebSocket スレッド（broker が stream_push を提供する場合）で push を受けて内部キューへ投入。
    - シグナル処理フロー: size_multiplier 適用、Gate1（シグナルレベル）、Gate2（実行レベル・レート制限）、発注、position_entries への書き込み、監視DBへのイベントロギング。
    - Gate3（ドローダウン監視）で NG の場合は kill_switch を発動。
    - 発注フローのタイムアウトやエラーに対するログ・リトライ・保護処理を含む。
  - OrderRecord モデル（kabusys.execution.order_record）
    - 状態列挙 OrderState と許可遷移マップを定義。
    - transition_to メソッドで遷移検証・updated_at 更新・オプションフィールド更新を実装。
    - InvalidStateTransitionError を導入。
  - OrderManager（kabusys.execution.order_manager）
    - create_order: signal_id ベースの重複検出（DB の partial unique による二重防止を含む）と OrderRecord の生成/永続化。
    - send_order: クラッシュ耐性を意識した二相永続化戦略を実装
      - Step1: OrderSent へ遷移して永続化（broker 呼び出し前）
      - Step2: broker.send_order 呼び出し
      - Step3a: broker_order_id を先に永続化（state は Sent のまま）
      - Step3b: OrderAccepted に遷移して永続化
      - 失敗 (OrderRejectedError) のハンドリング、OrderSentPendingError による pending 扱い（broker_order_id 永続化の上で例外伝播）
    - sync_order: broker の状態を取得して DB と同期。部分約定（filled_qty / avg_fill_price）の同一状態内更新も考慮。
    - cancel_order: 終端状態ではキャンセル不可のチェックと broker 側 cancel 呼出し、Cancelled への遷移。
    - DuplicateOrderError を導入。
  - Reconciler / RiskManager 等との連携点を用意（ExecutionEngine での起動時リコンシリエーション呼び出し、RiskManager による Gate チェック）。

- ブローカークライアント（kabu station）
  - KabuStationClient（kabusys.execution.kabu_client）を追加
    - httpx を用いた同期 REST クライアント実装。
    - トークン取得の遅延初期化と 401 時の自動再取得（1 回リトライ）。
    - レスポンス JSON パース失敗やタイムアウト/ネットワーク例外を BrokerAPIError に変換。
    - 429 を RateLimitError にマップ、5xx をサーバーエラーとして扱う。
    - kabu station の状態コードを内部状態（open/partial/filled/cancelled/rejected）へマップする辞書を追加。
    - WebSocket push（stream_push）を使った受信を想定した設計（存在しない場合は警告してスキップ）。

- 監視関連
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）との連携を追加（run_monitoring / run_execution で利用）。
  - 発注時に監視DBへ Sent イベントを記録する処理を追加（latency_ms などを含む）。監視DB 書き込み失敗は警告にとどめる。

- ユーティリティ
  - プロセス優先度設定ユーティリティ（set_process_priority）とログ設定セットアップ（setup_logging）を起動時に利用する設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （特別なセキュリティ修正は明示されていないが、.env を Git にコミットしない旨の注意を .env 生成時に明記）

---

備考:
- 本 CHANGELOG はコード内容から推測して作成されており、実際のコミット履歴をそのまま反映したものではありません。細かな実装意図や追加の変更点がある場合は、実際の Git 履歴／開発ノートを参照してください。
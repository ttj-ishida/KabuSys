CHANGELOG
=========

すべての注目すべき変更はここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

注意: 以下はコードベース（src/ 以下）の内容から推測して作成した変更履歴です。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-23
-------------------

Added
- 基本アプリケーション情報
  - パッケージメタ情報を追加: kabusys.__version__ = "0.1.0"（src/kabusys/__init__.py）。

- 環境設定読み込み/管理
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートの .env / .env.local）。
    - OS 環境変数を保護するための上書き制御（protected set）あり（src/kabusys/config.py）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
    - .git または pyproject.toml を基準にプロジェクトルートを検出する実装を追加。
  - .env 行パーサを実装: export プレフィックス、引用符（シングル/ダブル）、バックスラッシュエスケープ、行内コメント処理に対応（src/kabusys/config.py）。
  - Settings クラスを追加し、環境変数経由でアプリ設定を参照可能に（各種プロパティ: トークン、DB パス、PID/KILL フラグ、閾値、env/log_level 判定など）。

- 設定ウィザード CLI
  - 対話式ウィザードで .env を作成/更新する CLI を追加（python -m kabusys.config_setup）。
    - シークレット項目は表示時にマスク。
    - デフォルト値、選択肢、任意項目の取り扱い、既存 .env 読み込みをサポート。
    - .env の書き出しテンプレートを整備（src/kabusys/config_setup.py）。

- 設定検証 CLI
  - 起動前に環境変数と config/*.yaml の存在・基本妥当性をチェックする CLI を追加（python -m kabusys.validate_config）。
    - 必須/任意の環境変数チェック、プレースホルダ検知（"_here" / "your_value"）を実装。
    - KABUSYS_ENV / LOG_LEVEL の許容値検証、KABUSYS_ENV=live 時の追加警告（LINE 通知設定、KILL_FLAG_CLEAR_ON_START）など。
    - config/*.yaml の存在確認と（PyYAML がインストールされている場合）パース検証を実施。
    - --strict オプションで警告を失敗扱いにできる（exit code=1）。

- 実行/監視用起動スクリプト
  - Execution 用起動スクリプトを追加（python -m kabusys.run_execution）。
    - Paper trading 時は専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
    - プロセス優先度の設定・PID ファイル管理・停止フラグ検知をサポート（src/kabusys/run_execution.py）。
  - Monitoring 用起動スクリプトを追加（python -m kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は常に本番 sqlite_path を使用する（環境にかかわらず）。
    - stop_requested.flag による停止、SQLite / DuckDB 接続管理（src/kabusys/run_monitoring.py）。

- 注文処理コア
  - OrderRecord: 注文状態遷移モデルと検証ロジックを追加（src/kabusys/execution/order_record.py）。
    - Enum で状態を定義し、許可遷移テーブルを実装。
    - transition_to() による遷移とタイムスタンプ更新、オプションフィールド更新。
    - 不正遷移時は InvalidStateTransitionError を送出。
  - OrderRepository（注: 実装ファイルは参照先に存在）と組み合わせる OrderManager を追加（src/kabusys/execution/order_manager.py）。
    - create_order(): signal_id に対する重複（active 注文）を検出して DuplicateOrderError を返す。
    - send_order(): 2フェーズ永続化（OrderSent の永続化 → broker 呼び出し → broker_order_id を先にコミット → OrderAccepted へ遷移）によりクラッシュ耐性を向上。OrderRejected/OrderSentPending の扱いを明確化。
    - sync_order(): broker 側の状態を照合して DB を更新（部分約定の進行はフィールド更新のみ等の最適化）。
    - cancel_order(): キャンセル不可能状態の検出と broker API 呼び出し、Cancelled への遷移。
  - ExecutionEngine を追加（src/kabusys/execution/execution_engine.py）。
    - シグナル読み込み（DuckDB）→ Gate1/2（リスクチェック）→ 発注ループ（8:50-9:10）→ push ドレイン（9:10-15:30）のフローを実装。
    - Gate1/2/3 による多段リスク制御と kill_switch の発動ロジックを実装（Gate2 のサーキットブレーカ時の挙動含む）。
    - kill_switch(): 全 active 注文のキャンセル、停止イベントセット。
    - WebSocket スレッド（broker が stream_push を持つ場合に有効）で push を受け取り同期処理を行う。
    - 発注後の position_entries 追記処理、監視 DB への trade event ログ（MonitoringDB が渡された場合）に対応。
    - PID ファイル書き込み・kill.flag の扱い（KILL_FLAG_CLEAR_ON_START）を反映。

- Broker/Kabu クライアント
  - KabuStationClient を追加（httpx を使用した同期 REST クライアント、src/kabusys/execution/kabu_client.py）。
    - API トークンの遅延取得と 401 に対する自動再取得・1回リトライを実装。
    - HTTP タイムアウト / ネットワークエラーを BrokerAPIError に変換。
    - 429 レスポンスは RateLimitError を送出。
    - WebSocket push（stream_push）を想定した stream_push/on_message の連携を考慮。
    - kabu ステータスコードを内部ステータス文字列にマッピング。

- 監視関連
  - monitoring_db の初期化ユーティリティを提供し、監視起動時と実行起動時に DB 初期化（冪等）を行う（src/kabusys/monitoring/* 参照）。
  - Monitoring のポーリング間隔や監視ログの書き込みポイントを追加。

- ユーティリティ
  - .env の読み込み失敗時に warnings.warn を出すなど、IO エラー考慮の実装。
  - プロセス優先度設定ユーティリティ呼び出し（set_process_priority）。
  - ロギング初期化ヘルパー（setup_logging）を利用。

Changed
- 設定読み込みの仕様
  - .env の読み込み順序を明確化: OS 環境変数 > .env.local > .env（.env.local が .env をオーバーライドする）。
  - .env の上書き動作は override 引数で制御（.env.local は override=True）。

Fixed
- クラッシュ耐性の強化
  - send_order の永続化手順を 2 段階にして、ネットワーク障害やクラッシュ発生時の再同期（Reconciliation）で状態復元可能に。
  - ExecutionEngine の起動時/ループ内での kill.flag 検査・PID ファイル管理を改善し、残留状態での誤起動を防止。

Security
- .env の取り扱いに関する注意を .env 書き出しテンプレートに明記（.env を Git にコミットしない旨）。

Notes / TODO（コードから推測）
- YAML パース検証は PyYAML がインストールされている場合のみ実行されるため、配布パッケージでは依存関係に注意が必要。
- 実際の broker 実装（BrokerAPIProtocol の具体実装）や OrderRepository の SQLite 実装は別モジュールに依存しており、本 CHANGELOG にはそれらの詳細変更は含まれていません。
- 将来的な改善候補: KabuStationClient の非同期対応（httpx.AsyncClient）や詳細な監視メトリクス拡張など。

参考: 主要ファイル一覧
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/execution/*.py（execution_engine, order_manager, order_record, kabu_client, ...）
- src/kabusys/monitoring/*
- src/kabusys/utils/*

--- 

この CHANGELOG はコードからの推測に基づいて作成しています。差分やリリース履歴の正確な履歴が存在する場合は、その情報を提供いただければさらに正確な変更履歴を作成します。
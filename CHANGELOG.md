# Changelog

すべての重要な変更をこのファイルに記載します。

フォーマットは Keep a Changelog に準拠しています。Version 番号は package の __version__ に合わせています。

## [0.1.0] - 2026-04-22

### Added
- プロジェクト初期リリース。
- 環境設定・読み込み
  - .env ファイルおよび OS 環境変数を自動読み込みする仕組みを実装（src/kabusys/config.py）。
    - プロジェクトルートは .git または pyproject.toml を探索して特定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env のパースは引用符、エスケープ、インラインコメント等に対応する堅牢な実装。
  - Settings クラスを提供し、アプリケーション設定（トークン、パス、閾値、環境、ログレベル等）に型付きアクセスを可能に。
    - 必須環境変数取得時の例外制御（_require）を実装。
    - PAPER_FILL_MODE 等の値検証ロジックを含む。

- 対話式設定ウィザード（.env 作成/更新）
  - src/kabusys/config_setup.py にウィザードを実装。
  - 必須/任意/シークレット項目の対話的入力、既存 .env の読み込み、保存用フォーマット出力をサポート。
  - 生成される .env のテンプレートと注意書きを含む。

- 設定検証 CLI
  - src/kabusys/validate_config.py に起動前チェックツールを実装。
  - 必須環境変数の存在確認、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在確認と（PyYAML があれば）構文検証を行う。
  - --strict オプションで警告を FAIL 扱いにする挙動を提供。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険検出）を実装。

- エンジン起動スクリプト
  - 実行エンジン run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine の起動フローを実装。paper_trading モード時は専用 SQLite（paper_trading.db）を使用して本番 DB と分離。
    - 高優先度のプロセス設定、PID ファイル管理、停止フラグ（data/stop_requested.flag）に基づく安全な停止処理を実装。
  - 監視プロセス run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor ポーリングループ実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔の上書きが可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する挙動を明示。

- 実行ロジックと発注フロー
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - シグナル読み込み（DuckDB）→ Gate1/Gate2 のリスクチェック→ 発注 → push ドレイン（Gate3）の一連フローを実装。
    - シグナル処理は発注時間帯（デフォルト 8:50–9:10）、push ドレインはマーケットクローズまで（デフォルト 9:10–15:30）。
    - kill.flag の検出と起動時の KILL_FLAG_CLEAR_ON_START 扱いに対応。
    - WebSocket push を受け取る別スレッドをサポート（broker に stream_push が存在する場合）。
    - position_entries への書き込み（約定日を翌営業日にするロジック）を含む。
    - 発注に関する監視DB へのイベント記録（latency 等）を行うフックを追加。

  - OrderManager（src/kabusys/execution/order_manager.py）
    - signal_id の重複防止（DuplicateOrderError）や DB 制約違反の変換ロジックを実装。
    - send_order ではクラッシュ耐性を考慮した 2 段階永続化パターンを採用:
      1. OrderCreated → OrderSent を永続化してから broker 呼び出し
      2. broker_order_id を先に永続化（state は Sent のまま）
      3. OrderAccepted へ遷移して永続化
    - OrderSentPendingError（注文番号は発行されたが約定が保留）を呼び元に伝播しつつ DB 保存を行う挙動をサポート。
    - sync_order では broker からの状態取得を DB に反映し、部分約定の進捗更新や状態遷移補正（OrderSent→Filled 等のケースで OrderAccepted を経由）を行う。
    - cancel_order は終端状態ではキャンセル不可にして例外を投げる安全設計。

  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態列挙 OrderState と許可遷移テーブルを定義。
    - transition_to による遷移検証、タイムスタンプ更新、オプションフィールド更新、InvalidStateTransitionError を実装。

  - ExecutionEngine 内でのリスク管理連携
    - RiskManager を用いた Gate 1（シグナルレベル）、Gate 2（エグゼキューションレベル、レート制限と回復）、Gate 3（ポートフォリオ指標に基づくドローダウンでの kill_switch 発動）を実装。
    - API 呼び出し成功/失敗メトリクスの記録フックを実装。

- ブローカークライアント（kabu station）
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx を使用した同期 HTTP クライアントを実装。
    - トークン取得を内部で遅延初期化し、401 で自動再取得して 1 回リトライするロジックを実装。
    - レスポンス JSON パースエラー、タイムアウト、ネットワークエラー、429 レート制限、5xx サーバーエラー等を BrokerAPIError / RateLimitError として扱う。
    - 将来の async 対応を見越した設計（httpx.AsyncClient への置換が容易）。

- データベース周り
  - DuckDB（分析用）および SQLite（監視/履歴用）との接続を統合。
  - init_monitoring_db を用いて監視用テーブルの冪等初期化を実行。

- ユーティリティ
  - .env ファイルの読み書き、既存値の読み取り・マスキング表示、対話入力の再試行等を含むツール群を実装。
  - プロセス優先度設定やロギングセットアップの呼び出し箇所を追加。

### Notes
- 本リリースは初期実装であり多くのコンポーネント（BrokerAPI の実装、RiskManager の具体的ルール、SystemMonitor 実装、監視DB スキーマ等）は別モジュールに分かれている（src/kabusys 以下）。
- YAML 構文チェックは PyYAML がインストールされている場合にのみ有効。未インストール時は警告を出してスキップする挙動。
- paper_trading モードは本番 DB と分離されるよう設計されているが、運用時は .env の設定と validate_config による事前検証を推奨。

---

（今後のリリースでは Changed / Fixed / Security 等のセクションを使用して差分を明確に記載します。）
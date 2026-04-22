# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。

全般的な注意:
- .env ファイルや環境変数を基に動作するため、リポジトリ配布時は .env を含めないでください（config_setup にも注意書きあり）。
- 自動環境読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

## [0.1.0] - 2026-04-22

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン `0.1.0` を定義。
- 環境/設定管理
  - Settings クラスを追加し、環境変数から各種設定（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、PID/Kill flag 等）を取得可能に。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。優先順位は OS 環境変数 > .env.local > .env。
  - .env の自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パース機能を強化（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント扱いの改善）。
- 対話式設定ウィザード
  - python -m kabusys.config_setup により .env の初期作成・更新を対話的に支援する CLI を追加。
  - 各設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を定義し、シークレット入力や選択肢をサポート。
  - 生成される .env のテンプレート出力機能を追加（.env のヘッダ・セクション付き）。
- 設定検証ツール
  - python -m kabusys.validate_config を追加。.env と config/*.yaml の基本的な検証を起動前に実行。
  - --strict モードを追加（警告も失敗扱いで exit(1)）。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）およびプレースホルダ値検出。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認。
  - config/*.yaml の存在確認と（PyYAML がインストールされていれば）パース検証。PyYAML 未インストール時は警告でスキップ。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の必須チェック、KILL_FLAG_CLEAR_ON_START の警告など）。
- 実行スクリプト
  - run_execution（python -m kabusys.run_execution）: ExecutionEngine の起動スクリプトを追加。
    - paper_trading 環境では paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - プロセス優先度設定（高）と PID 管理、停止フラグ検出 (data/stop_requested.flag) を備える。
  - run_monitoring（python -m kabusys.run_monitoring）: SystemMonitor をポーリングで実行する監視プロセス起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番 sqlite_path を利用する設計。
- 発注関連コア
  - OrderRecord: 注文状態遷移を表す状態マシンとデータモデルを追加（DB 非依存の純粋ロジック）。
    - 状態列挙 OrderState（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許容される遷移テーブルと transition_to() による更新（InvalidStateTransitionError を送出）。
  - OrderRepository / OrderManager / ExecutionEngine 等の発注ワークフロー基盤を追加（OrderRecord と SQLite リポジトリを組み合わせ）。
    - OrderManager: create/send/sync/cancel の高レベル API を提供。送信時に二相的永続化を行いクラッシュ耐性を高める（OrderSent を永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）。
    - OrderSentPendingError を扱い、broker_order_id を保持したまま保留扱いにできる設計。
    - DuplicateOrderError: 同一 signal_id のアクティブ注文重複を検出して制御（DB のユニーク制約違反も変換）。
    - cancel_order はキャンセル不可能な状態をチェックし、可能なら broker API で取消を実施して Cancelled に遷移。
  - ExecutionEngine: シグナル処理ループ（8:50–9:10）と push ドレインループ（9:10–15:30）を実装。
    - Gate 1/2/3 のリスクチェックフローを組み込み（シグナル単位の検査、実行レート制限、ドローダウン監視での kill_switch 発動）。
    - kill_switch() により全アクティブ注文をキャンセルしループを停止する仕組みを提供。
    - WebSocket push（kabu push）を別スレッドで受け取り _push_queue を経由して同期処理を行う。
    - position_entries への約定記録（BUY は次営業日を fill_date として登録）を追加（duckdb 経由）。
    - 発注失敗/保留時のリスク監視（API 成功/失敗記録）と監視 DB（MonitoringDB）へのイベントログ機能のフックを追加。
- ブローカークライアント（kabu）
  - KabuStationClient を実装（同期 httpx ベース、将来 AsyncClient に置き換え可能）。
    - トークン取得の遅延初期化と 401 に対する再取得リトライ。
    - レスポンス JSON パース例外を BrokerAPIError に変換。
    - HTTP 429 に対して RateLimitError を返すなどステータスコード毎のエラーハンドリング。
    - stream_push を通じた WebSocket push（websocket ライブラリ利用）をサポートするインターフェース設計（ExecutionEngine から利用）。
- 監視周り
  - monitoring 用 DB 初期化ユーティリティを追加（init_monitoring_db）。
  - run_monitoring は stop_requested.flag の検出で安全に終了する。

### 変更 (Changed)
- 設定読み込みの挙動
  - .env の読み込みロジックは既存の OS 環境変数を保護するため protected セットを利用して .env.local からの上書きを制御するようにした。
- 発注の堅牢性向上
  - send_order の実装を二相永続化（OrderSent を DB に残した後 API 呼び出し、broker_order_id を先にコミット、続けて OrderAccepted へ遷移）にしてクラッシュ時の再同期性を改善。
  - sync_order のロジックで、同一状態でも filled_qty / avg_fill_price の変化を検知して更新する処理を追加。
- ExecutionEngine の起動制御
  - 起動時に kill.flag が存在する場合は KILL_FLAG_CLEAR_ON_START の値に応じて自動クリア or 起動拒否を行うようにした（settings.kill_flag_clear_on_start）。
  - PID ファイルの作成/削除を明示的に行うようにした。
- 設定検証ツールの出力整理
  - validate_config の出力で INFO/WARNING/ERROR を整形して表示。警告を --strict で失敗扱いにできる仕様を追加。

### 修正 (Fixed)
- .env パースのいくつかの境界ケースに対応（クォート内のバックスラッシュエスケープ、行内コメントの扱い）。
- 複数の潜在的クラッシュシナリオに対する回復性を強化（OrderSent → broker 呼び出し間のクラッシュでも broker_order_id が DB に残ることでリコンシリエーション可能）。
- run_monitoring/run_execution 両スクリプトで DB 接続後のクリーンアップ（finally 部分での接続クローズ）を確実化。

### 既知の制限 / 注意点 (Known issues / Notes)
- config/*.yaml の内容検証は PyYAML が必要。未インストール時は検証をスキップして警告のみを表示します。
- KabuStationClient は現在同期 httpx.Client 実装。将来的に非同期化を検討。
- ExecutionEngine の時間依存ロジック（ローカル時間ベース）や PID/kill フラグの動作は運用環境のファイル権限や時計設定に依存します。
- run_monitoring は常に本番用 sqlite_path を使う設計のため、監視プロセスの動作前に sqlite_path のバックアップ/分離が必要な場合があります。

（初回リリースのため、バグ報告・改善提案は issue を通じてお願いします。）
# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このファイルはコードベースから推測して作成した変更履歴です（自動生成ではなく手動推測です）。

## [Unreleased]

## [0.1.0] - 2026-04-23
最初の公開リリース相当。KabuSys の基盤となる設定管理、監視・発注エンジン、ブローカークライアント、状態管理などの主要コンポーネントを実装。

### Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
- 環境設定 / 設定読み込み
  - Settings クラスを追加し、環境変数からアプリケーション設定を取得可能に。
  - .env の自動ロード機能を実装（優先順位: OS 環境 > .env.local > .env）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env ファイルを安全にパースするロジックを実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いに対応。
  - _require() ユーティリティで必須環境変数未設定時に明確なエラーを返す。
- 環境設定ウィザード
  - 対話式の config_setup CLI を追加（python -m kabusys.config_setup）。
  - 項目定義（KABUSYS_ENV/JQUANTS_REFRESH_TOKEN/KABU_API_PASSWORD/DUCKDB_PATH/SQLITE_PATH/LINE* 等）と既存 .env の読み込み/上書き、.env の書き出し機能を実装。
  - シークレット値のマスク表示、選択肢チェック、Enter による既存値利用などユーザーフレンドリな対話ループを実装。
  - .env テンプレート出力で「.env を絶対に Git にコミットしない」旨の注意を追加。
- 設定検証ツール
  - validate_config CLI を追加（python -m kabusys.validate_config）。
  - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース検査を実装。
  - --strict オプションで警告を FAIL（exit(1)）扱いにできる機能を追加。
  - YAML パーサ未インストール時は YAML 検証をスキップして警告を出す実装。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の警告）を追加。
- 実行 / 監視スクリプト
  - run_execution（ExecutionEngine 起動スクリプト）を追加（python -m kabusys.run_execution 相当）。
    - paper_trading 環境時は paper_trading 用 SQLite を使用し、本番 DB と分離する挙動を実装。
    - プロセス優先度設定、PID 書き出し、停止フラグ検知（data/stop_requested.flag）、kill.flag の扱い（KILL_FLAG_CLEAR_ON_START による自動クリアオプション）を実装。
  - run_monitoring（SystemMonitor ポーリング起動スクリプト）を追加（python -m kabusys.run_monitoring 相当）。
    - 環境にかかわらず監視は本番 sqlite_path を使用する方針を採用。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能。値検証と不正値時のフォールバックを実装。
- 実行エンジンと発注ワークフロー
  - ExecutionEngine を実装（シグナル処理 + WebSocket push ドレインループ、セッションタイムレンジの管理）。
    - signal_send_start / signal_send_end / market_close を設定可能（EngineConfig）。
    - WebSocket 経由 push を受け取り同期処理（sync_order）を行うワーカースレッドを含む。
    - シグナル読み込みは DuckDB から行い、portfolio_targets と結合して発注数量/価格を決定。
    - kill_switch 実装により全 active 注文のキャンセルを行い、ループ終了を促す。
    - 発注成功/失敗/保留の分岐処理、レイテンシ測定、監視 DB へのイベント記録を組み込み。
  - ExecutionEngine のログ記録・PID 管理・再コンシリエーション呼び出し（Reconciler）を実装。
- 注文状態管理と永続化
  - OrderRecord（状態モデル）を追加。状態遷移ロジックと検証（InvalidStateTransitionError）を実装。
  - OrderManager を追加し、OrderRecord と OrderRepository（SQLite）を組み合わせて外向け API（create/send/sync/cancel）を提供。
    - create_order は signal_id の重複チェックを行い、DB の部分ユニーク制約違反を DuplicateOrderError に変換する。
    - send_order は 2 相永続化パターンを採用（OrderSent を先にコミット → ブローカー呼び出し → broker_order_id をコミット → OrderAccepted に遷移）。OrderSentPendingError の扱いも実装。
    - sync_order は broker 側ステータス照合による状態同期や部分約定の進行反映を行う。
    - cancel_order はキャンセル不可能な状態の判定とブローカー API 呼び出しを行い、Cancelled に遷移する。
  - OrderState 列挙型と許容遷移マップを定義（created/sent/accepted/partial/filled/closed/cancelled/rejected）。
- ブローカー関連
  - KabuStationClient を実装（httpx を用いた同期 REST クライアント）。
    - トークン取得・再取得の遅延初期化、401 時のリトライ処理、429（Rate Limit）・5xx のエラー変換を実装。
    - レスポンス JSON パース失敗時に明確な BrokerAPIError を投げる。
    - WebSocket push 用の stream_push インターフェース（存在する場合に ExecutionEngine が利用）を想定。
- 監視
  - monitoring DB 初期化ユーティリティと SystemMonitor を参照する起動フローを追加（run_monitoring に組み込み）。
- ユーティリティ
  - process_priority および logging_setup 経由で起動時にプロセス優先度やログ設定を整える仕組みを利用。
  - DuckDB / SQLite の接続確立処理を組み込み。

### Changed
- （初版のため履歴的変更なし）

### Fixed
- .env パーサでの引用符内のバックスラッシュエスケープや行内コメント処理を考慮するよう改善（より現実的な .env フォーマットに耐性あり）。
- validate_config において PyYAML が未インストールの場合に優雅にスキップして警告を出すように実装（環境に依存した障害を回避）。

### Security
- .env の書き出しテンプレートで「.env は絶対に Git にコミットしないこと」を明示。シークレットはウィザードでマスク表示。
- Settings._require により必須シークレットが未設定の場合に早期に失敗することで誤起動を防止。

### Notes / Known behaviors
- validate_config の --strict モードは警告も FAIL（exit code 1）とするため CI 等での厳格チェックに利用できる。
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データは本番 DB に記録する方針）。
- run_execution は paper_trading 環境時に paper_trading 用 SQLite を使用し、本番データと分離する。
- ExecutionEngine の再コンシリエーションはオプション（Reconciler を渡すことで有効）。
- OrderManager.send_order はクラッシュ耐性（途中クラッシュで OrderSent が残るなど）を考慮した永続化戦略を採用している（Reconciliation により復旧を想定）。

もしこの CHANGELOG に加えるべき追加情報（リリース日、詳細な既知の問題、リリースノートの形式変更など）があれば教えてください。
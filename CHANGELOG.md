# CHANGELOG

すべての顕著な変更は Keep a Changelog の形式に従って記録します。  
このファイルはコードベース（初期リリース相当）から推測して作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-23

Added
- 初期リリースとして以下の主要機能を追加。
  - アプリケーション設定管理
    - Settings クラスを提供し、環境変数から各種設定を取得する API を実装。
    - env 値の自動ロード機能: プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - .env 読み込みでの挙動:
      - "export KEY=val" 形式の対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを考慮したパーサを実装。
  - 設定ウィザード CLI
    - `kabusys.config_setup` に対話式ウィザードを追加し、.env の生成・更新を支援。
    - 秘密値のマスク表示、選択肢・デフォルト提示、既存 .env の読み込み、保存前の確認を実装。
    - 出力フォーマットを統一した .env ファイル書き込みを行う `_write_env` を提供。
  - 設定検証 CLI
    - `kabusys.validate_config` により起動前に .env および config/*.yaml の基本的な不備を検出。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パス親ディレクトリの存在チェック等を実装。
    - PyYAML が未導入の場合は YAML 内容検証をスキップして警告を出す挙動。
    - `--strict` オプションで警告を FAIL 扱い（exit code 1）にする。
  - 実行系スクリプト
    - `run_execution.py`
      - ExecutionEngine 起動用スクリプト。
      - KABUSYS_ENV=paper_trading 時の DB 分離（paper_trading 用 SQLite を使用）。
      - PID / 停止フラグ（stop_requested.flag）検査、プロセス優先度設定、DB 初期化処理を実装。
    - `run_monitoring.py`
      - SystemMonitor のポーリングループを起動するスクリプト。
      - MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）により間隔を変更可能。
      - 監視は環境にかかわらず本番 sqlite_path を使用する旨を保証。
  - 発注エンジンと関連コンポーネント（サーバーサイドのビジネスロジック）
    - OrderRecord
      - 注文の状態遷移を表す OrderState 列挙と、遷移検証を行う OrderRecord 型を実装。
      - 許可される状態遷移マップを定義し、不正遷移時に InvalidStateTransitionError を発生させる。
    - OrderManager
      - signal_id ベースでの重複注文防止（DuplicateOrderError）。
      - create → send のフローでクラッシュ安全性を意識した 2 相永続化パターンを実装（OrderSent を先に永続化し、broker_order_id を先にコミットする等）。
      - send_order における OrderRejectedError, OrderSentPendingError の扱い（pending の永続化と呼び元への伝播）を実装。
      - sync_order による broker 側状態照合と部分約定更新、cancel_order によるキャンセルフローを実装。
    - ExecutionEngine
      - Signal Queue Pull 型の発注エンジンを実装。シグナル処理時間帯（デフォルト 8:50–9:10）と市場クローズ（15:30）をベースにセッション運用。
      - Gate1/2/3 のリスクチェック連携（リスクマネージャとの統合、レート制限に対するリトライやサーキットブレーカーの扱い）。
      - push ドレインループ（WebSocket 経由の push 処理）、_push_queue を使った非同期処理。
      - kill_switch 機構（全ループ停止＋全 active 注文のキャンセル）を提供。
      - position_entries 追加ロジック（buy/sell によるエントリ/クローズ記録）を DuckDB に書き込む処理を実装。
      - 監視用 DB へのトレードイベントログ書き込み（MonitoringDB 経由）のフックを持つ。
  - ブローカークライアント（kabu station）
    - KabuStationClient を実装（httpx 同期クライアントベース）。
    - トークン取得（/token）・X-API-KEY ヘッダの付与・401 時のトークン再取得とリトライ、タイムアウト／ネットワーク例外の BrokerAPIError 変換を実装。
    - kabu station の注文状態コードと内部ステータスのマッピングを定義。
    - 429 に対して RateLimitError を発生させる等、HTTP ステータスに応じた例外変換を実装。
  - 設定項目とデフォルト
    - DUCKDB_PATH、SQLITE_PATH、KABU_API_BASE_URL、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START などのデフォルト値と説明を提供。
    - Settings に paper_fill_mode（instant|partial|never|reject）などの検証済みプロパティを実装。
  - 監視周り
    - monitoring_db 初期化呼び出しを各スクリプトに追加（init_monitoring_db）。

Changed
- 初期リリースにおける設計上の注意点や挙動を明確化。
  - 設定自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - .env の上書きは protected（OS 環境変数一覧）を保護して行う仕様。
  - run_monitoring は KABUSYS_ENV に依存せず常に本番用 sqlite を使う旨を明記。

Fixed
- N/A（初期公開相当）。ただしコード中にクラッシュ時や外部 API エラーに対する適切な例外変換・回復ロジック（OrderSentPendingError の扱いや JSON パースエラー変換など）を実装しているため、堅牢性を改善済み。

Security
- .env を決して Git にコミットしない旨の注意書きを設定ウィザードで出力。

Notes / Implementation details（実装から推測した重要ポイント）
- .env パーサは引用符内のエスケープ処理をサポートしており、単純な split("=") より堅牢。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告するため、依存パッケージがない環境でも基本的な検証は可能。
- ExecutionEngine はシグナル処理と push ドレインを明確に分離しており、本番の push 処理がないブローカーでも安全に動作する（stream_push がなければ WebSocket スレッドはスキップ）。
- OrderManager の設計はクラッシュ安全性（永続化順序）や Reconciliation を考慮している。

開発者向け確認事項
- settings.* のプロパティは ValueError を投げる実装があるため、テスト時は必要な環境変数をセットするか KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して自動ロードを抑制してください。
- .env のアップデートは config_setup のウィザード経由で行うと注意書きやフォーマットが統一されます。
- run_execution/run_monitoring は data ディレクトリに PID/flag/DB ファイルを書き込むため、適切なファイルパスの権限管理を行ってください。

---

（この CHANGELOG はコードの構造・コメント・関数名からの推測に基づいて作成しています。実際のリリースノートとして使用する場合は、コミット履歴やリリース担当者による確認を行ってください。）
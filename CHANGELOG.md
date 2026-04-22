# Changelog

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
このファイルはプロジェクトのリリース履歴を記録します。

フォーマットの解説: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-22

初回リリース。KabuSys の基本的な設定管理、起動スクリプト、発注エンジン、監視機能および kabuステーション向けクライアントを含みます。

### Added
- パッケージ基盤
  - パッケージ情報: バージョン 0.1.0 を追加（src/kabusys/__init__.py）。

- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。環境変数から各種設定を取得するための集中管理を提供。
    - J-Quants / kabu API / LINE / DB パス / PID / Kill Switch / モニタリングしきい値 等のプロパティを定義。
    - env 値や log level のバリデーションを実装（有効な値集合をチェックし、不正値で ValueError を送出）。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - OS 環境変数保護（既存キーは上書きしない / .env.local でのみ上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装（_parse_env_line）。
    - export KEY=val 形式、クォートされた値（エスケープ対応）、インラインコメントの扱い（非クォートでは '#' の前がスペース/タブならコメントとみなす）に対応。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py を追加。
    - 対話式に .env を作成/更新するウィザード（秘密値はマスクして表示）。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。
    - 既存 .env の読み込み・再利用、最終確認、保存機能を提供。
    - .env ファイルを書き出す際のテンプレートと注意書きを出力。

- 設定検証 CLI
  - src/kabusys/validate_config.py を追加。
    - .env および config/*.yaml の設定不備を起動前に検出する CLI。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、プレースホルダ検出（値が your_value や _here で終わる場合は警告）。
    - KABUSYS_ENV, LOG_LEVEL の妥当性チェック（有効値集合）。
    - DB パスの親ディレクトリ存在確認（存在しない場合は警告。起動時に自動作成される場合がある旨を表示）。
    - config/*.yaml の存在確認と（PyYAML が存在する場合は）YAML のパース検証。PyYAML 未インストール時は検証スキップと警告。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険値を警告）。
    - --strict オプションで警告も失敗扱い（exit 1）にできる。

- 実行（Execution）および監視（Monitoring）エントリポイント
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - PID ファイル、停止フラグ（data/stop_requested.flag）による起動/停止制御。
    - プロセス優先度設定と DB 初期化（init_monitoring_db）。
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを実行するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。

- 発注エンジン本体
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - シグナル読み込み（DuckDB）、Gate1/2 リスクチェック、発注処理ループ、WebSocket push ドレイン処理（Gate3）、kill switch 等を実装。
    - PID 書き込み、kill.flag に対する起動拒否 / KILL_FLAG_CLEAR_ON_START による自動クリア動作。
    - push 通知処理では broker.get_positions() を参照してポートフォリオ評価を行い、Gate3 NG で kill_switch を発動。
    - WebSocket スレッドは broker が stream_push をサポートしない場合にスキップして警告出力。
    - position_entries（DuckDB）への書き込み（発注後の約定日登録）を行い、失敗時は警告のみとする。
    - monitoring_db が渡された場合、発注イベントの監視 DB へのログ記録を試みる（失敗しても発注フローは継続）。
  - 停止／kill 処理
    - kill_switch(): 全 active 注文をキャンセルし停止する（外部停止フラグ検知等で呼び出し）。
    - stop(): kill_switch() の公開エイリアス。

- 注文管理
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態列挙 OrderState と許容遷移テーブルを実装（状態遷移検証を行い、不正遷移で InvalidStateTransitionError を送出）。
    - UTC タイムスタンプの自動更新、オプションフィールド（broker_order_id, filled_qty, avg_fill_price, error_message）の更新処理を提供。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - create_order: signal_id ベースの重複検出（DB の部分ユニークインデックス違反を DuplicateOrderError に変換）。
    - send_order: クラッシュ安全性を考慮した 2 相永続化フローを実装（OrderSent を永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted へ遷移）。
      - OrderRejectedError は Rejected に遷移して永続化。
      - OrderSentPendingError は broker_order_id を永続化した上で例外を伝播（Reconciliation 対象）。
    - sync_order: broker 側のステータス取得とローカル状態の同期（部分約定の進行に対するフィールド更新含む）。
    - cancel_order: 終端状態の判定と、必要なら broker.cancel_order 呼び出しのうえ Cancelled に遷移。
    - duplicate / invalid transition / not found に対して適切な例外を送出。

- Broker / KabuStation クライアント
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx 同期クライアントで kabu station REST API を実装。
    - API トークン取得を遅延初期化し、401 の場合は再取得して 1 回リトライするロジックを実装。
    - JSON パース失敗 / ネットワークエラー / タイムアウトを BrokerAPIError に変換。
    - 429 を RateLimitError にマッピング。
    - kabu station の状態コードを内部ステータス（open/partial/filled/cancelled/rejected）にマッピング。
    - 将来の async 対応を考慮した設計（httpx.AsyncClient へ差し替え可能）。

- データベース関連
  - DuckDB と SQLite の併用を前提とした接続および初期化処理（monitoring DB 初期化を init_monitoring_db で実行）。
  - ExecutionEngine では paper_trading 用 DB と本番 DB の分離をサポート。

- ユーティリティ
  - 簡易ログ設定、プロセス優先度設定ユーティリティ（参照されているが詳細は別モジュール）。
  - Monitoring 用 SystemMonitor の起動スクリプト。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- .env の取り扱いに関して注意書きを .env 生成ヘッダに明示（.env を Git にコミットしない旨）。

### Notes / 注意点（マイグレーション／運用）
- validate_config により起動前に設定検証を行うことを推奨。特に本番環境（KABUSYS_ENV=live）では LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を必ず確認してください。
- KILL_FLAG_CLEAR_ON_START=1 は本番環境で危険（kill.flag が自動クリアされ、誤って起動する恐れがある）ためデフォルトは 0。本番は 0 を推奨。
- ExecutionEngine は発注フロー中のクラッシュ耐性を考慮しており、OrderSent のような不確実状態は Reconciliation によって回復可能な設計です。Reconciler を実行して DB とブローカ状態の整合性を保つ運用を推奨します。
- PyYAML がインストールされていない場合、validate_config は YAML 内容の検証をスキップします。config/*.yaml のパース検証を行いたい場合は PyYAML をインストールしてください。
- Monitoring は環境にかかわらず本番 sqlite_path を使用するため、監視データの分離が必要な場合は設定を確認してください。
- PAPER_FILL_MODE は有効な値を持つ必要があり、不正値の場合 Settings が ValueError を投げます。

--- 

今後のリリースでは以下の点を予定／検討中:
- 非同期 (async) 対応のための httpx.AsyncClient への切替（KabuStationClient の async 版）。
- その他コンポーネント（Reconciler, Broker 実装, Monitoring の詳細）の安定化とテスト強化。
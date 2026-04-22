# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、この CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴とは一致しない場合があります。

## [Unreleased]

## [0.1.0] - 2026-04-22

初回リリース。

### Added
- プロジェクト初期実装を追加。
  - パッケージのバージョン定義: kabusys __version__ = "0.1.0"。
- 設定 / 環境変数関連
  - Settings クラスを実装（kabusys.config）。
    - J-Quants / kabuステーション / LINE / データベース / 監視 / システム設定を環境変数から取得するプロパティ群を提供。
    - env（KABUSYS_ENV）や LOG_LEVEL、PAPER_FILL_MODE 等の値検証を実施し、不正値で例外を投げる挙動を実装。
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH などのパスを Path 型で返す。
    - kill_flag_clear_on_start の bool 判定や閾値（CPU/MEM/DISK/MEMORY）の float 取得をサポート。
  - .env ファイル自動読み込み機能を実装（kabusys.config）。
    - プロジェクトルートを .git または pyproject.toml で探索して特定。
    - 読み込み順: OS 環境変数 > .env.local > .env（既存の OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート無し時の処理）を考慮。
- 環境設定ウィザード CLI（kabusys.config_setup）
  - 対話式ウィザードで .env を初期作成・更新する機能を提供。
  - 項目ごとに説明・選択肢・デフォルト・シークレット表示（マスク）をサポート。
  - .env の読み書き（テンプレート出力）を実装。ファイル上部に注意書きを追加（.env を Git にコミットしない旨）。
- 設定検証 CLI（kabusys.validate_config）
  - .env および config/*.yaml の起動前チェックを行う CLI を実装。
  - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、プレースホルダ値検出（末尾が "_here" または "your_value"）、DB パスの親ディレクトリ存在確認などをサポート。
  - PyYAML 非インストール時は YAML の内容検証をスキップし、インストール済みならパースを試行してエラーを報告。
  - --strict オプションにより警告も失敗扱いにできる。
  - exit コードと出力メッセージ（INFO/WARNING/ERROR）を整備。
- 実行スクリプト
  - run_execution（kabusys.run_execution）
    - ExecutionEngine を起動するエントリポイントを提供。
    - paper_trading 環境時は paper_trading 用の SQLite DB を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル書き込み、stop フラグ検出により安全に起動/停止。
  - run_monitoring（kabusys.run_monitoring）
    - SystemMonitor ポーリングループを実行するエントリポイントを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用。
    - stop フラグ検出でループを終了。
- Execution エンジン本体（kabusys.execution.execution_engine）
  - ExecutionEngine と EngineConfig を実装。
  - シグナルの読み取り（DuckDB）、Gate1/2（シグナル/実行レベル）によるリスクチェック、発注フロー、WebSocket push のドレインループを実装。
  - 発注時の処理: create / send / position_entries への書き込み、監視 DB への trade event ログ（任意）をサポート。
  - kill_switch 実装: 全 active 注文のキャンセルとループ停止を実行。
  - セッション管理（発注時間帯、push ドレイン、PID ファイル管理、リコンシリエーション起動）を実装。
- 注文管理コンポーネント
  - OrderRecord（kabusys.execution.order_record）
    - 状態列挙 OrderState（created, sent, accepted, partial, filled, closed, cancelled, rejected）と状態遷移の許可テーブルを定義。
    - transition_to による遷移検証とタイムスタンプ更新を実装。InvalidStateTransitionError を定義。
  - OrderManager（kabusys.execution.order_manager）
    - create_order: signal_id 重複検出（DB 部分ユニーク制約を考慮）と OrderRecord 生成/保存の実装。
    - send_order: 2 相永続化パターン（OrderSent の永続化 → broker 呼び出し → broker_order_id の永続化 → OrderAccepted 遷移）を実装。OrderRejectedError、OrderSentPendingError の扱いを実装。
    - sync_order: broker 側の状態を取得してローカル状態に同期、部分約定の更新処理を最適化（同一状態でも filled_qty/avg_fill_price を更新）。
    - cancel_order: キャンセル不可状態の判定と broker 取消 API 呼び出しを実装。
  - OrderRepository / DB 連携（存在を前提に使用）との統合ポイントを実装。
- Broker / kabu クライアント（kabusys.execution.kabu_client）
  - KabuStationClient を実装（httpx を利用した同期クライアント）。
    - トークン管理（遅延取得・401 時の再取得）、_request の 401 リトライ、429（RateLimitError）や 5xx のエラー変換を実装。
    - kabu station の状態コード → 内部ステータスへのマッピングを定義。
    - WebSocket 経由の push を取り扱うための stream_push 想定（存在チェックしてワーカースレッドで利用）。
- 監視関連
  - monitoring_db の初期化呼び出し（init_monitoring_db を run_execution/run_monitoring で呼ぶ）を追加。
  - ExecutionEngine 内で監視 DB が与えられた場合にトレードイベントを書き込む処理を実装。
- その他ユーティリティ
  - process_priority 設定、logging 設定（setup_logging）呼び出しを実行スクリプトで使用。

### Changed
- 初版のため特定の「変更」はなし（新規導入）。

### Fixed
- 初版のため特定の「修正」はなし。

### Security
- .env を生成するテンプレートに「.env を絶対に Git にコミットしないこと」の注意を明示。
- config_setup にてシークレット入力は表示をマスクして確認できる UI を提供。

### Notes / Caveats
- validate_config は PyYAML の有無によって YAML 内容検証の有無が変わります（未インストール時は検証をスキップして警告）。
- KabuStationClient の一部の実装は REST/WS の詳細実装に依存します（HTTP クライアントは httpx、WebSocket は websocket モジュールを想定）。
- .env のパース挙動は一般的な shell 形式を意識しているが、すべての corner case を網羅しているわけではありません。必要に応じて追加テストを推奨します。

---- 

今後のリリースでは、テストカバレッジの拡充、Broker API のモック実装、監視・アラートの強化、Reconciliation ロジックの詳細追加などを想定しています。
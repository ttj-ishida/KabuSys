# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-23
初回リリース — KabuSys のコア設定・実行・監視・発注エンジンの基盤機能を実装。

### Added
- 全体
  - パッケージの初期バージョンを `__version__ = "0.1.0"` として追加。
  - CLI / スクリプト群を提供:
    - 設定ウィザード: python -m kabusys.config_setup
    - 設定検証ツール: python -m kabusys.validate_config
    - 監視プロセス起動: python -m kabusys.run_monitoring
    - 発注エンジン起動: python -m kabusys.run_execution

- 環境設定管理 (`src/kabusys/config.py`)
  - .env の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env/.env.local の読み込み順序（OS環境 > .env.local > .env）を定義し、OS の既存環境変数を保護する仕組みを追加。
  - _parse_env_line: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを含む堅牢な .env パーサを実装。
  - Settings クラスを導入し、環境変数をプロパティ経由で取得:
    - J-Quants / kabu API / LINE / DB パス / PID/kill flag / しきい値 / env/log_level 等のプロパティを提供。
    - paper_trading 向けの paper_sqlite_path と paper_fill_mode をサポート（有効値検証あり）。
    - env / log_level の値検証により不正値で ValueError を送出する。

- 設定ウィザード (`src/kabusys/config_setup.py`)
  - 対話式ウィザードで .env を生成・更新する機能を実装。
  - J-Quants / kabu API / DB パス / LINE / ログレベル / Kill Switch など主要項目を定義。
  - 既存の .env を読み込んで Enter で既存値を再利用可能。
  - シークレット項目は表示をマスクし、最終確認の後に .env を書き出す。

- 設定検証 CLI (`src/kabusys/validate_config.py`)
  - 必須/任意環境変数の存在チェック、プレースホルダ検出（例: 値が "_here" で終わる等）を実装。
  - KABUSYS_ENV / LOG_LEVEL の有効値チェックと、本番環境 (live) 向け注意喚起（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の危険設定等）。
  - DUCKDB / SQLITE のパス親ディレクトリ存在チェック。
  - config/*.yaml の存在確認と PyYAML があれば YAML パース検証（PyYAML 未インストール時はスキップする挙動）。
  - --strict オプションで警告を FAIL（終了コード1）として扱う。

- 実行・監視起動スクリプト
  - run_execution (`src/kabusys/run_execution.py`)
    - ExecutionEngine の起動手順を実装（プロセス優先度設定、DB 接続、PID ファイル管理、停止フラグチェック、スレッドでのエンジン実行）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
  - run_monitoring (`src/kabusys/run_monitoring.py`)
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用する設計。
    - stop_requested.flag による優雅な停止処理を実装。

- 発注サブシステム（Execution）
  - OrderRecord / OrderState (`src/kabusys/execution/order_record.py`)
    - 注文状態列挙型と、許容される状態遷移テーブルを実装。
    - OrderRecord データクラス（純粋ビジネスロジック）と transition_to による遷移検証を実装。無効な遷移は InvalidStateTransitionError を送出。
  - OrderManager (`src/kabusys/execution/order_manager.py`)
    - signal_id の重複チェック（DuplicateOrderError を送出）。
    - create_order: DB 保存時に signal_id 部分ユニーク制約違反を DuplicateOrderError に変換。
    - send_order: クラッシュ耐性を考慮した 2 段階永続化（OrderSent へ先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新）。OrderRejected / OrderSentPending の扱いを実装。
    - sync_order: broker 側状態取得による同期ロジック。部分約定の進行時に filled_qty/avg_fill_price を更新。
    - cancel_order: 終端状態のキャンセル不許可判定、broker cancel 呼び出しと Cancelled 移行。
    - 内部で OrderRepository（SQLite）を利用する前提。

  - ExecutionEngine (`src/kabusys/execution/execution_engine.py`)
    - シグナル処理（8:50–9:10）と WebSocket push ドレイン（9:10–15:30）を想定したセッションループを実装。
    - Gate1: シグナルレベルのリスクチェック、Gate2: エグゼキューションレベル（レート制限・サーキットブレーカー）、Gate3: ドローダウン監視（kill switch 発動）などのリスクゲートを導入。
    - kill_switch(): 全 active 注文のキャンセル、ループ停止処理を実装。外部から stop() で呼べる。
    - WebSocket push を受け取り _push_queue へ投入、push を処理して sync_order と Gate3 判定を実行。
    - 発注後の position_entries への書き込み（買いはエントリを追加、売りは sell_date を更新）を実装（duckdb 使用）。
    - 監視用 DB への発注イベントログ出力フック（MonitoringDB）をサポート。
    - run_session は PID 書き込み・kill.flag チェック・リコンシリエーション実行の流れを適切に管理。

  - KabuStationClient (`src/kabusys/execution/kabu_client.py`)
    - kabuステーション REST API クライアント実装（httpx を使用）。
    - トークン取得の遅延初期化と 401 時の再取得リトライを実装。
    - レスポンス JSON パース失敗・ネットワークエラー・タイムアウトを BrokerAPIError に変換。
    - 429（レート制限）や 5xx を適切にエラーとして扱う。
    - websocket 経由の push 処理（stream_push を持つ broker の場合に使用）を想定。

- その他ユーティリティ
  - プロセス優先度設定・ロギングセットアップ等のユーティリティを利用する設計（setup_logging / set_process_priority を参照）。

### Changed
- 設計上の注意点を明示化:
  - ExecutionEngine は kill.flag の扱いに厳密（起動時の kill_flag_clear_on_start 設定に依存）。
  - Monitoring は常に本番 sqlite_path を使用する（環境に依存しない監視を保証）。

### Fixed
- .env パーサの細かな抜け（コメント処理やエスケープ）を改善し、実運用で想定されるフォーマットに対応。

### Security
- .env を Git にコミットしないよう .env 出力ヘッダーに注意喚起を追加。

### Known limitations / Notes
- 一部コンポーネント（OrderRepository, BrokerClientFactory, RiskManager, Reconciler, MonitoringDB など）は実装ファイル参照・インターフェースに依存しており、外部の実装により挙動が変わります。
- config/*.yaml の内容検証は PyYAML に依存。PyYAML 未インストール時は YAML 内容検証をスキップして警告する設計。
- Settings のプロパティは不正な env/log_level 値で ValueError を投げるため、呼び出し側は例外ハンドリングが必要です。
- ExecutionEngine の時間帯（signal_send_start/ end, market_close）はデフォルトを設定しているが、テスト環境では直接メソッドを呼ぶことを想定。

---

この CHANGELOG はコードの内容（ドキュメンテーション文字列、実装ロジック、関数/クラス名、コメント）から推測して作成しています。実際のリリースノート作成時は用途に応じて修正・追記してください。
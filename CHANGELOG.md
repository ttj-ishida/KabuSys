# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
安定したリリースはセマンティックバージョニングを使用します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。

### Added
- パッケージの初期公開
  - パッケージメタ情報: `__version__ = "0.1.0"`（src/kabusys/__init__.py）。

- 設定関連ツール
  - 対話式 .env 設定ウィザードを追加（python -m kabusys.config_setup）。
    - .env の読み込み・表示・編集・保存機能。
    - 各設定項目の定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）と説明、選択肢・デフォルト値の提供（src/kabusys/config_setup.py）。
    - .env ファイル生成時にテンプレートヘッダを自動出力。
  - 起動前設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DBパスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML があればパースを実行）。
    - --strict オプションで警告も失敗扱いにできる（exit code 1）。
    - 本番（KABUSYS_ENV=live）向けの追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の危険な値について警告）。
    - 実装ファイル: src/kabusys/validate_config.py

- 環境設定管理
  - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）を追加。読み込み順は OS 環境変数 > .env.local > .env（src/kabusys/config.py）。
  - .env パーサを強化:
    - コメント行・export プレフィックス対応。
    - シングル／ダブルクォート中のバックスラッシュエスケープ処理対応。
    - クォート無の場合はインラインコメント判定（直前が空白かタブの場合のみ）。
  - 自動読み込みを無効にする環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを導入（src/kabusys/config.py）:
    - 環境変数から各種設定を取得するプロパティ群（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_*, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/MEM/DISK 閾値, KABUSYS_ENV, LOG_LEVEL 等）。
    - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL の妥当性チェック（不正値は ValueError）。

- 実行スクリプト（運用用プロセス）
  - 監視プロセス起動スクリプト: python -m kabusys.run_monitoring（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - 監視は環境に関係なく本番 sqlite_path を使用する。
    - プロセス優先度設定、SQLite / DuckDB 接続、SystemMonitor のポーリングループ、停止フラグ検出、例外ハンドリングを実装。
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution（src/kabusys/run_execution.py）
    - paper_trading 環境では専用の paper_trading DB を使用して本番 DB と分離。
    - プロセス優先度設定、監視 DB 初期化、Engine のスレッド実行と停止フラグ検出を実装。

- 発注周りのコア実装（Execution）
  - OrderRecord: 注文状態マシンのデータモデルと状態遷移ロジックを実装（src/kabusys/execution/order_record.py）。
    - 定義済み状態（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可遷移テーブル、遷移時のタイムスタンプ更新、オプションフィールド更新。無効遷移は InvalidStateTransitionError を raise。
  - OrderRepository（SQLite）を使った OrderManager を実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id の重複検出（DB 部分ユニーク制約違反は DuplicateOrderError に変換）。
    - send_order: クラッシュ安全性を考慮した 2 相的永続化フローを実装（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted に遷移）。OrderRejectedError, OrderSentPendingError の取り扱いを実装。
    - sync_order: broker からのステータスを取得して同期。部分約定の進行のみ更新する最適化も実装。
    - cancel_order: 終端状態判定（キャンセル不可状態は InvalidStateTransitionError）と broker への cancel 呼び出しを実装。
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）:
    - Signal Queue からの発注フロー（シグナル処理時間帯: 8:50–9:10）と WebSocket push ドレインループ（9:10–15:30）を実装。
    - Gate1（シグナルレベル）、Gate2（エグゼキューションレベル/レート制限/サーキットブレーカー）、Gate3（ポートフォリオ指標/ドローダウン）による複数段階リスクチェックを実装し、NG 時に kill_switch を発動。
    - kill_switch は全 active 注文のキャンセルを試み、ループ停止を行う。
    - WebSocket push の受信を別スレッドで実行し、push を queue に入れてメインスレッドで処理する設計（stream_push がない broker は WS スレッドをスキップ）。
    - position_entries の書き込み（buy/sell の扱いを分ける）や監視 DB へのトレードイベント記録フックを追加。
    - PID ファイルの出力・削除、起動時の kill.flag の扱い（KILL_FLAG_CLEAR_ON_START による自動クリアオプション）を実装。

- Broker クライアント（kabu station）
  - KabuStationClient を追加（src/kabusys/execution/kabu_client.py）:
    - httpx.Client を用いた同期 REST 実装。
    - トークン取得の遅延初期化と 401 時の再取得・1 回リトライ実装。
    - レスポンス JSON パース失敗、タイムアウト、ネットワークエラー、429 (rate limit)、500 以上のサーバーエラーを専用例外に変換。
    - websocket 経由の push（websocket ライブラリ）を扱うためのインターフェースを想定。

- 監視関連
  - Monitoring DB 初期化関数と SystemMonitor との連携（run_monitoring/run_execution で使用）。
  - DuckDB と SQLite の両方を使用する設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env ファイル生成時に「絶対に Git にコミットしない」旨を明記（src/kabusys/config_setup.py）。

### Notes / Implementation details / 既知事項
- Settings のプロパティは不正値を検出して ValueError を投げるため、起動前に validate_config を実行することを推奨します。
- validate_config は PyYAML がインストールされている場合のみ config/*.yaml をパースして内容を検証します。未インストール時はパース検証をスキップして警告を出力します。
- ExecutionEngine のシグナル取得は DuckDB クエリに依存します。テスト時は _process_signals() と _drain_push_queue() を直接呼び出して挙動を確認可能です。
- paper_trading 環境では DB を完全に分離（paper_trading 用の SQLite）しているため本番データへの影響を避けられます。
- KabuStationClient は現在同期実装（httpx.Client）です。将来的に async 化するときは httpx.AsyncClient に切り替えやすい設計。

---

今後の予定（短期ロードマップの例）
- BrokerAPI のモック実装・テスト用フレームワークの追加
- 詳細な監視イベント（エラー種別・レイテンシ分布）の拡張
- YAML 設定ファイルのスキーマバリデーション導入（PyYAML + JSON Schema 等）
- 単体テスト・統合テストの充実（特にクラッシュシナリオや Reconciliation ロジック）

（問題やバグを見つけた場合は Issue を作成してください）
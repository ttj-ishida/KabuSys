# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

現行バージョン: 0.1.0

## [Unreleased]

（現時点では未リリースの変更はありません）

---

## [0.1.0] - 2026-04-22

初回公開リリース。主要な機能追加と基盤となるコンポーネントを実装しました。

### Added
- プロジェクトメタ情報
  - パッケージバージョンを src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。

- 環境設定・ロード関連
  - .env ファイルの自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して自動的に .env / .env.local を読み込む。
    - 読み込みの優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - `_parse_env_line` による柔軟かつ安全な .env パース（export 形式対応、クォートとエスケープ、行内コメント処理など）。
    - `_load_env_file` による既存環境変数保護（protected 引数）と上書き制御。

  - 設定ラッパー Settings クラスを実装（src/kabusys/config.py）。
    - 必須環境変数取得時の検証（_require）：未設定時に ValueError を投げる。
    - 各種プロパティを提供: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_*、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE（検証あり）、paper_sqlite_path、PID/KILL フラグパス、リソース閾値、env/log_level など。
    - KABUSYS_ENV / LOG_LEVEL の値検証。

  - 対話式設定ウィザード（.env 作成）を追加（src/kabusys/config_setup.py）。
    - 複数の設定項目定義を用意（環境、API トークン、DB パス、LINE トークン、ログレベル、Kill Flag 挙動など）。
    - 既存 .env の読み込みと再利用、入力時のデフォルト/マスク表示、保存確認、.env 生成ロジックを実装。
    - _read_env / _write_env によるファイル入出力。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - .env と config/*.yaml の基本的な検証を実行。
    - 必須環境変数未設定やプレースホルダ判定、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認および PyYAML によるパース検証（PyYAML 未導入時は警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告も失敗（exit(1)）扱いにできる。

- 実行・監視エントリポイント
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - process priority 設定、Settings を用いた DB 接続、paper_trading モード時の専用 SQLite 使用、ExecutionEngine の起動と停止フラグ管理を実装。
  - Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - stop_requested.flag による停止検知処理。

- 発注・実行コア
  - ExecutionEngine クラスを実装（src/kabusys/execution/execution_engine.py）。
    - シグナルの読み込み（DuckDB）、Gate ベースのリスク検査（Gate1/2/3）、発注フロー、push ドレイン、WebSocket push ディスパッチ、kill switch、PID ファイル管理などのセッション管理を実装。
    - 発注成功時の position_entries 更新（DuckDB）、監視 DB へのイベントログ記録機能を組み込み可能。
    - run_session / run_session の時間スロット（8:50〜9:10 発注ループ、9:10〜15:30 push ドレイン）をサポート。

  - OrderRecord（状態遷移モデル）を実装（src/kabusys/execution/order_record.py）。
    - OrderState Enum と許可遷移マップ、OrderRecord dataclass、transition_to による遷移検証と更新、InvalidStateTransitionError を提供。
    - DB に触れない純粋ビジネスロジックとして設計。

  - OrderManager を実装（src/kabusys/execution/order_manager.py）。
    - create_order（重複 signal の検出と DB 永続化）、send_order（2相永続化の説明付実装：OrderSent 保存 → broker 呼び出し → broker_order_id 保存 → OrderAccepted 更新、OrderRejected / OrderSentPending の取扱い）、sync_order（Broker 側状態照合と同期）、cancel_order（キャンセル不可能状態の検査と API 呼び出し）を提供。
    - DuplicateOrderError、OrderSentPendingError の取り扱いと再発生条件を明記。
    - DB 側の一意制約違反時に DuplicateOrderError へ変換する処理を実装。

  - ブローカー API クライアント（kabu station）を実装（src/kabusys/execution/kabu_client.py）。
    - KabuStationClient: httpx を用いた同期 REST クライアント実装。
    - トークン取得（/token）と自動再取得、認証ヘッダ付きリクエスト、401 リトライ、429 (Rate Limit) / 5xx のエラー変換処理を実装。
    - kabu station の状態コード → 内部ステータスマップを実装（open/partial/filled/...）。
    - 将来の async 対応を見据えた設計（現状は httpx.Client）。

- その他ライブラリ統合
  - duckdb を分析 DB として利用（duckdb 接続を利用する各処理での採用）。
  - sqlite3 を監視・注文履歴用 DB として使用。
  - ロギング初期化・プロセス優先度設定のユーティリティ（setup_logging, set_process_priority）を起動フローで使用（これらは既存ユーティリティモジュールを参照）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Known issues
- config/*.yaml の内容検証は PyYAML に依存する。PyYAML 未導入環境では検証をスキップし警告を出す設計になっています（validate_config）。
- KabuStationClient は httpx と websocket ライブラリを前提とします。実行環境に応じて必要パッケージをインストールしてください。
- ExecutionEngine・OrderManager 等は SQLite / DuckDB のスキーマ（テーブル定義）に依存します。運用前に初期化スクリプト（monitoring DB 等）を実行してください（init_monitoring_db が存在）。
- paper_trading モードでは paper_sqlite_path を使用して本番 DB と完全分離する設計です。設定の確認は validate_config と config_setup を併用してください。
- kill.flag 周りの動作はデフォルトで起動を拒否する設定です。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨します。

---

（以降のリリースでは追加・変更点を上記フォーマットで追記してください）
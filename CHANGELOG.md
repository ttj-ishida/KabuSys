CHANGELOG
=========

すべての注目すべき変更点を時系列で記録します。

フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

（現時点のコードは初回リリース相当の状態として記録しています。以降の変更はここに追加してください。）

[0.1.0] - 2026-04-23
-------------------

Added
- 初版リリース: KabuSys v0.1.0 を追加。
- 設定管理
  - Settings クラスを追加し、環境変数から各種設定値を提供（J-Quants / kabu API / LINE / DB パス / PID / Kill Switch /閾値等）。
  - 自動 .env 読み込み機能を追加（優先順位: OS 環境変数 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - PAPER_FILL_MODE の検証（有効値: instant, partial, never, reject）を実装。
  - log_level / env 等の値検証（不正値は ValueError）。
- .env ファイルの取り扱い
  - 高機能な .env パーサを実装（export プレフィックス対応、クォート & バックスラッシュエスケープ対応、インラインコメント処理）。
  - 対話式設定ウィザード CLI を追加（python -m kabusys.config_setup）。選択肢、シークレット表示、既存 .env の読み込み再利用、.env ファイル生成機能を提供。
  - .env の書き込みテンプレートに注意喚起（Git にコミットしない旨）を追加。
- 設定検証 CLI
  - validate_config CLI を追加（python -m kabusys.validate_config）。必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険値警告）等を実装。
  - --strict オプションで警告を FAIL として exit(1) を返すモードを追加。
  - PyYAML が未インストールの場合は YAML 内容検証をスキップし、警告を出力。
- 実行 & 監視スクリプト
  - run_execution（python -m kabusys.run_execution）を追加。ExecutionEngine を起動し、PID 管理、stop フラグ検知、paper_trading 環境時の専用 SQLite を使用する等の挙動を実装。
  - run_monitoring（python -m kabusys.run_monitoring）を追加。SystemMonitor のポーリングループ、MONITOR_POLL_INTERVAL によるポーリング間隔上書き、stop フラグ検知、監視 DB 初期化を実装。
  - 両スクリプトでプロセス優先度設定（set_process_priority("high")）とログ設定（setup_logging）を行う。
- Execution 系コア
  - ExecutionEngine を実装（シグナル取得 -> Gate1/2 を通した発注処理、WebSocket push ドレインループ、push による同期と Gate3 チェック、kill_switch の実装など）。
  - EngineConfig で target_date / signal 時刻等を構成可能にした。
  - OrderRecord（状態遷移モデル）を実装。状態列挙 OrderState と許可遷移マップ、transition_to による遷移検証（不正遷移は InvalidStateTransitionError）。
  - OrderManager を実装。create_order / send_order / sync_order / cancel_order のフローをサポート。send_order はクラッシュ耐性を考慮した 2 相永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）を実装。OrderSentPendingError の扱い、OrderRejectedError の扱いを実装。
  - DuplicateOrderError を導入し、同一 signal_id の active 注文重複を防止。
  - ExecutionEngine 内で position_entries への書き込み（DuckDB）や発注レイテンシ／監視 DB ログの記録を実装。
- ブローカークライアント
  - KabuStationClient を実装（httpx を使用した同期 REST クライアント、トークン管理、自動再取得、401 のリトライ、429 を RateLimitError として扱う等）。
  - kabu ステータスコードと内部ステータスのマッピング実装。
  - WebSocket push（stream_push）を持つ broker のための受信スレッドをサポート（on_message を受け取り内部キューへ投入）。
- リコンシリエーション & 監視
  - 起動時に Reconciler を任意で実行するフックを追加（reconciler.run() 実行とログ出力）。
  - monitoring DB 初期化関数 init_monitoring_db を run_* スクリプトで使用。
- リスク管理
  - RiskManager を用いた Gate1/2/3 のチェックを実装。Gate2 はレート制限リトライ / Circuit Breaker のハンドリング、Gate3 はドローダウン検知で kill_switch 発動。
- DB 接続
  - sqlite3 と duckdb を組み合わせた運用（duckdb は分析・signals 等、sqlite は監視/注文履歴）。paper_trading の分離 DB をサポート。
- ロギング / プロセス制御
  - setup_logging によるアプリ別ログ設定、プロセス優先度設定ユーティリティを呼び出して優先度を上げる実装。

Fixed
- .env パーサの不明点をかなり考慮（引用符内のバックスラッシュエスケープ、コメント扱いの条件など）して堅牢化。
- 設定検証でプレースホルダ値（例: endswith "_here" や "your_value"）を警告として検出。
- send_order の永続化戦略を明確化し、クラッシュ後の Reconciliation で状態回復可能な設計に修正。
- ExecutionEngine の kill.flag および KILL_FLAG_CLEAR_ON_START の扱いを明確化（起動時チェック・起動時自動クリアオプションの尊重）。

Security
- .env は決して Git にコミットしない旨を .env 生成テンプレートに明記。
- API トークン / パスワードは対話ウィザードでシークレット扱い（表示マスク）。

Notes / Dependencies
- PyYAML: config/*.yaml を検証するために任意で使用。未インストール時は内容検証をスキップして警告を出力。
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD。
- 主要依存: httpx, websocket-client, duckdb, sqlite3（標準ライブラリ）等。
- デフォルト値: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, KABUSYS_ENV=development, LOG_LEVEL=INFO, MONITOR_POLL_INTERVAL=60 秒 など。

その他
- パッケージバージョンは __version__ = "0.1.0" に設定。

今後の予定（示唆）
- async httpx クライアント対応（将来的な拡張としてコメントあり）。
- さらなる監視・テスト追加、CLI の改善、YAML 設定の詳細検証強化。
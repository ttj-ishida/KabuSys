# Changelog

すべての変更点は Keep a Changelog の形式で記録します。  
フォーマット: https://keepachangelog.com/（日本語説明）

※ 以下はソースコードの内容から推察して作成した初回リリース向けの変更履歴です。

## [0.1.0] - 2026-04-23

### Added
- パッケージ全体の初期実装を追加。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - 環境変数 / .env ファイルを扱う `kabusys.config` を実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により .env 自動読み込みを実施（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env のパース処理は export プレフィックス対応、シングル/ダブルクォート中のエスケープ処理、インラインコメント扱いの詳細を考慮。
    - .env 読み込みは OS 環境変数を保護（`.env.local` は override=True だが OS 環境変数に対しては上書きしない）。
    - 必須変数取得時に未設定なら例外を投げる `_require()` を提供。
  - Settings クラスを実装し、各種設定をプロパティ経由で取得可能:
    - J-Quants / kabu API 関連、LINE 通知設定、DuckDB/SQLite パス、paper trading 用 DB、kill flag 設定、しきい値（CPU/MEM/DISK）等。
    - `env` / `log_level` / `paper_fill_mode` の値検証（不正な値は ValueError）。
    - `is_live` / `is_paper` / `is_dev` の判定プロパティ。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装。
    - `.env` の初期作成・更新を支援。項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）。
    - 既存 .env を読み込み Enter で再利用、選択肢/デフォルトの提示、シークレット項目は表示をマスク。
    - 最終確認後に .env を指定パスへ書き込み（.env のテンプレートヘッダ付き）。
    - 使用例: python -m kabusys.config_setup

- 設定検証 CLI
  - `kabusys.validate_config` に設定検証ツールを実装。
    - 必須環境変数の存在チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml（存在確認と PyYAML によるパース検証）などを実行。
    - `--strict` オプションで警告を FAIL として扱い exit(1)。
    - PyYAML 未インストール時は YAML 内容検証をスキップして警告を出力。
    - config ファイルが足りない場合のヒント（python scripts/generate_config.py）表示。

- 実行・監視スクリプト
  - `kabusys.run_execution` : ExecutionEngine の起動スクリプトを追加。
    - プロセス優先度を上げる（utils.process_priority を利用）。
    - KABUSYS_ENV によって paper_trading 時は paper 用 SQLite を使うなど DB の切り替え。
    - stop フラグ検知（data/stop_requested.flag）、PID ファイル管理、スレッド実行と安全終了処理。
    - 使用例: python -m kabusys.run_execution
  - `kabusys.run_monitoring` : SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、0 以下は既定値にフォールバック）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - stop フラグ検知と適切なクローズ処理。
    - 使用例: python -m kabusys.run_monitoring

- Execution エンジン本体
  - `kabusys.execution.execution_engine.ExecutionEngine` を実装。
    - セッション制御（signal_send_start / signal_send_end / market_close）。
    - 起動時に Reconciler を実行し、kill.flag の存在確認・自動クリア（KILL_FLAG_CLEAR_ON_START）ロジック。
    - PID ファイル書き出しと削除。
    - WebSocket push スレッド（broker が stream_push を持つ場合）による push 処理キュー。
    - シグナル処理フロー:
      - シグナルの読み出し（DuckDB からのクエリ）→ Gate 1（信号レベル）→ Gate 2（エグゼキューションレート制御）→ 発注。
      - size_multiplier の適用（BUY のみ、100株単位）。
      - 発注結果に応じた position_entries の書き込み（duckdb）、監視 DB へのイベントログ出力（MonitoringDB が与えられている場合）。
    - push 処理では sync_order を呼び出し、Gate 3（ドローダウン）を評価して必要なら kill_switch を発動。
    - kill_switch は全 active 注文をキャンセルし、停止イベントをセット。

- 注文管理と永続化を分離した設計
  - `kabusys.execution.order_record`:
    - 注文状態を表す OrderState 列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と遷移ルール（_ALLOWED_TRANSITIONS）。
    - OrderRecord dataclass（純粋ビジネスロジック、DB 非依存）と状態遷移検証（InvalidStateTransitionError）。
  - `kabusys.execution.order_manager.OrderManager`:
    - create_order / send_order / sync_order / cancel_order の外向け API 実装。
    - send_order の 2 相永続化戦略（OrderSent を先に DB にコミット → broker 呼び出し → broker_order_id を先に永続化 → OrderAccepted に遷移）によりクラッシュ時の回復性を高める設計。
    - OrderSentPendingError（注文番号は得られたが未約定）を特別扱いして broker_order_id を保存したまま OrderSent を維持し、呼び出し元へ伝播。
    - DuplicateOrderError を導入（同一 signal_id の active 注文を重複させない）。
    - sync_order は broker の状態を DB と同期し、部分約定の進行に応じて filled_qty / avg_fill_price を更新。
    - cancel_order はキャンセル不可能な状態での呼び出しを拒否し、可能なら broker.cancel_order を呼んで Cancelled に遷移。

- kabu station API クライアント
  - `kabusys.execution.kabu_client.KabuStationClient` を追加。
    - 同期的な httpx クライアントを用いた実装。
    - トークン管理（遅延初期化、401 時の再取得＆1回リトライ）とエラーマッピング（Timeout/RequestError → BrokerAPIError、429 → RateLimitError、JSON パース失敗 → BrokerAPIError）。
    - WebSocket push は別途 websocket や broker の stream_push を利用する設計（stream_push がない場合は警告してスキップ）。

- 監視用 DB 初期化と SystemMonitor（呼び出し箇所あり）
  - monitoring_db の初期化関数 init_monitoring_db を呼ぶ場所を実装（run_monitoring/run_execution など）。

- ロギング / プロセス優先度・ユーティリティ呼び出し
  - utils.logging_setup.setup_logging, utils.process_priority.set_process_priority を起動時に利用している（実装箇所はユーティリティに依存）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数ファイル（.env）に関する注意書きと、.env を Git にコミットしないようにテンプレートに明示。

### Notes / 実装上の注意点（重要）
- Settings の各種検証はプロパティアクセス時に ValueError を投げる設計のため、起動処理中に settings のプロパティを参照する箇所では例外処理を考慮する必要があります。
- send_order の挙動はクラッシュ安全性を重視しているが、OrderSent 状態でプロセスが停止した場合は Reconciler / sync 処理で復旧することが期待されます。
- .env のパース実装は多くのケース（export プレフィックス、クォート中のエスケープ、インラインコメント判定）をサポートしますが、特殊なフォーマットの .env では想定外の挙動をする可能性があります。
- KabuStationClient は同期実装（httpx.Client）であり、将来的に非同期対応が必要な場合は httpx.AsyncClient への差し替えで対応可能な作りになっています。
- monitor/run scripts は stop_flag（data/stop_requested.flag）や kill.flag の存在をトリガーに停止/kill を行います。運用時のフラグの管理に注意してください。

---

今後のリリースでは以下を検討すると良い点（例）:
- テスト・モックの充実（BrokerClient のユニットテスト向け抽象化の拡張）。
- Reconciler や RiskManager の詳細実装に関するドキュメントと運用ガイド。
- 非同期 I/O（WebSocket/HTTP）の選択肢追加。
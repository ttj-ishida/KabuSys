# Changelog

すべての重要な変更点を Keep a Changelog の形式で記載します。  
リリース履歴は日付順（新しい順）です。

全般:
- バージョンはパッケージの `kabusys.__version__` に従います。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション構成
  - パッケージ初期バージョンを追加（`__version__ = "0.1.0"`）。

- 環境設定/読み込み
  - Settings クラスを導入。環境変数から各種設定（J-Quants トークン、kabuAPI パスワード、DB パス、ログ設定、しきい値など）をプロパティ経由で取得・検証できるようにした。
  - 自動 .env ロード機能を実装（プロジェクトルートに基づいて `.env` → `.env.local` の順で読み込み）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - `.env` ファイルのパースロジックを強化：
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - クォート無しの行におけるインラインコメント判定（直前が空白/タブの場合のみ）
  - `PAPER_FILL_MODE` の検証（有効値: "instant" | "partial" | "never" | "reject"）など、各種プロパティに入力検証を追加。
  - データベース用パスプロパティ（`duckdb_path`, `sqlite_path`, `paper_sqlite_path`）とプロセス監視関連のファイルパスプロパティ（`pid_file_path`, `kill_flag_path`）を提供。

- 起動スクリプト / ランタイム
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - 環境変数 `KABUSYS_ENV=paper_trading` の場合は paper 専用 SQLite (`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`) を使用し、本番 DB と分離（MockBrokerClient が利用される想定）。
    - プロセス優先度を起動直後に `high` に設定。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine をスレッドで実行。停止フラグ（`data/stop_requested.flag`）を監視して安全に停止する。
    - RiskManager の既定設定を導入（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。初期ポートフォリオ価値はブローカーの利用可能現金から取得。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - デフォルトポーリング間隔は 60 秒。`MONITOR_POLL_INTERVAL` 環境変数で上書き可能（不正値は警告してデフォルトにフォールバック）。
    - 監視は環境にかかわらず production の `sqlite_path` を使用（監視 DB は環境ごとに分離しない設計）。
    - 停止フラグ `data/stop_requested.flag` の検出でループを終了、`SystemMonitor.check_once()` の例外はログに残して次回ポーリングへ継続。
    - duckdb 接続も確保して SystemMonitor に渡す。

- ユーティリティ
  - logging_setup: 統一的なログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日分保持）を設定。
    - LOG_LEVEL / LOG_DIR / app_name に基づく解決と、既存ハンドラの二重登録防止処理を実装。
    - ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソール出力のみで継続。
  - process_priority: プロセス優先度と CPU affinity のユーティリティを追加。
    - set_process_priority(level) で Windows / POSIX を吸収して優先度設定を試行。サポート外 OS や権限不足時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を提供（利用可能コア数より大きい場合は全コア使用、cpu_count < 1 は ValueError）。
    - 優先度レベル: "high" / "normal" / "low"。
  - validate_config: 設定検証 CLI を実装。
    - 必須環境変数チェック（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）や `KABUSYS_ENV` / `LOG_LEVEL` の検証、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在と PyYAML がある場合のパース検証を行う。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 本番 (`KABUSYS_ENV=live`) 時のガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）を追加。
  - config_setup: 対話式 .env 作成ウィザードを実装。
    - 対話で主要な環境変数を生成・更新できる。既存 .env の読み込み、シークレット表示のマスク、選択肢チェック、最終確認後に `.env` を保存。
    - 保存テンプレートはコメント付きで `.env` を生成。`.env` を絶対にコミットしない旨を明記。
  - tools/paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - SQLite（デフォルト: `data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`）を読み、`system_status`, `trade_logs`, `risk_logs` などから指標を集計。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数など。P95 計算ロジックと閾値を定義して PASS/FAIL 判定を出力。
    - CLI オプション: `--from`, `--to`, `--db`。
  - portfolio モジュール（純粋関数群）
    - portfolio_builder:
      - select_candidates: スコア降順（同点は signal_rank 昇順）でトップ N を選択。
      - calc_equal_weights / calc_score_weights: 等金額・スコア正規化重み算出。スコア合計が 0 の場合は等金額にフォールバック（警告ログ）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中を抑制するため既存保有のセクター別時価を計算し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）と未知レジームでのフォールバック（1.0）を実装。
    - position_sizing:
      - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に従い発注株数を計算。
      - risk_based: 許容リスク率（risk_pct）と損切り率（stop_loss_pct）に基づく計算。単元（lot_size）で丸め。1銘柄上限（max_position_pct）を考慮。
      - aggregate cap: 全銘柄コストが available_cash を超える場合に縮小スケーリングを行い、余剰キャッシュで端数（lot 単位）を残差順に追加配分するロジックを実装。
      - price 欠損時のスキップやログ出力、コストバッファ（cost_buffer）考慮など。

- research
  - research/factor_research.py を追加（モメンタム・ボラティリティ等のファクター計算基盤）。（注: ファイルは途中までの実装／設計コメントを含む）

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Migration
- .env の自動ロードが有効（プロジェクトルート検出可能な場合）。テストや特殊な起動環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化してください。
- 本番環境で `.env` を誤ってコミットしないでください（config_setup のテンプレートにも警告あり）。
- run_monitoring は監視 DB に常に `sqlite_path`（production 想定）を使います。監視 DB を環境ごとに分けたい場合は `SQLITE_PATH` を変更してください。
- run_execution は paper_trading モード時に paper 専用 DB を使用します。paper と production の DB 分離によりテストが安全になります。
- ログはデフォルトで logs/<app>.log に日次ローテーションで出力されます。ログディレクトリの指定は `LOG_DIR` 環境変数または `setup_logging()` の引数で行ってください。

---

今後の予定（未実装・改善提案）
- factor_research の完全実装（DB クエリと正規化ユーティリティとの連携）。  
- broker / execution 周りのより詳細なエラーハンドリングと永続化（注文履歴、再試行戦略）。  
- 単体テスト・統合テストの追加および CI 設定。
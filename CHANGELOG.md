# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の方針に従います。  
このファイルはコードベースから推測して生成した変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージを追加（初回リリース相当）
  - パッケージメタ情報: `__version__ = "0.1.0"` を設定。

- 環境変数・設定管理
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に。
  - .env 自動ロード機能:
    - プロジェクトルート（.git または pyproject.toml を基準）を検出して `.env` と `.env.local` を読み込む。
    - OS 環境変数を保護する仕組み（上書き禁止の保護セット）。
    - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサが以下に対応:
    - `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等。
  - 多数の設定プロパティを提供（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_FILL_MODE` 等）。
  - `PAPER_FILL_MODE` のバリデーション（有効値: "instant", "partial", "never", "reject"）。
  - `KABUSYS_ENV` / `LOG_LEVEL` の妥当性検証。

- 設定ウィザード CLI
  - `kabusys.config_setup`:
    - 対話式で `.env` を生成/更新するウィザードを実装。
    - シークレット値は画面上でマスク表示。
    - 生成される `.env` の雛形と保存プロンプトを提供。
    - `.env` を誤って Git 管理下に置かないようヘッダコメントを付与。

- 設定検証 CLI
  - `kabusys.validate_config`:
    - 実行前に必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の検証、DB パスや config/*.yaml の存在検査を実行。
    - PyYAML が無ければ YAML 検証をスキップして警告を出す。
    - `--strict` オプションでワーニングを FAIL 扱いにできる。
    - 結果を INFO/WARNING/ERROR として出力して終了コードを返す。

- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装:
    - すべての起動スクリプトで共通のログ設定を提供。
    - stdout 出力の StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト `logs/<app_name>.log`、30日保持）を設定。
    - ログレベルの解決順（引数 > LOG_LEVEL 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - stdout を使うことで cron / scheduler でのリダイレクト運用を想定。

- プロセス優先度・CPU アフィニティユーティリティ
  - `kabusys.utils.process_priority` を実装:
    - `set_process_priority(level)` で Windows / POSIX（Linux / macOS / FreeBSD）を吸収して優先度を設定（"high"/"normal"/"low"）。
    - `set_cpu_affinity(cpu_count)` で最初の N コアに固定可能（許可がない場合は警告を出してスキップ）。
    - psutil のアクセス拒否等に対してフォールバックしてログ警告で続行。

- 実行系 / 監視起動スクリプト
  - `run_execution.py`:
    - ExecutionEngine を起動する CLI スクリプトを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード専用 SQLite (`PAPER_TRADING_SQLITE_PATH` / default: `data/paper_trading.db`) を使用し、本番 DB と分離。
    - BrokerClientFactory により本番/モックブローカーを選択。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで起動。停止フラグ（`data/stop_requested.flag`）でエンジン停止。
    - PID ファイル (`data/execution.pid`) をサポート。
    - RiskConfig によるリスク制限設定（max_position_pct, max_utilization 等）。初期ポートフォリオ値を broker.get_available_cash() から取得。
  - `run_monitoring.py`:
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、1 秒未満の不正値はデフォルトにフォールバック）。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視用 DB 初期化を行う（monitoring は環境にかかわらず本番 sqlite_path を使用する設計）。
    - 停止フラグ（`data/stop_requested.flag`）の検知、例外時のロギングおよびループ継続、KeyboardInterrupt のハンドリングを実装。

- モニタリング DB 初期化
  - `init_monitoring_db` を呼び出して監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築機能（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - `select_candidates`：score 降順（同点は signal_rank 小さい方優先）で上位 N を選択。
    - `calc_equal_weights`：等金額配分。
    - `calc_score_weights`：スコア比率で重み計算、全スコアが 0 の場合は等分にフォールバックして警告出力。
  - `kabusys.portfolio.risk_adjustment`:
    - `apply_sector_cap`：既存ポジションを基にセクター集中を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - `calc_regime_multiplier`：レジーム ("bull"/"neutral"/"bear") に基づく投下資金乗数（未定義レジームは 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - `calc_position_sizes`：allocation_method ("risk_based", "equal", "score") に応じた発注株数算出。
    - 単元株（lot_size）丸め、1 銘柄上限の強制、aggregate cap（available_cash 超過時のスケーリング）および残差配分ロジック、コストバッファ（手数料/スリッページ見積り）対応。

- 研究用ファクター計算（基盤）
  - `kabusys.research.factor_research` にモメンタム等のファクター計算ロジックの骨格を実装（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。
  - 定義済みファクター／パラメータ例: 1M/3M/6M リターン、MA200 乖離、ATR、20日平均出来高 等。

- ツール: Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report` を追加:
    - Paper Trading 用 SQLite (`data/paper_trading.db` がデフォルト) からデータを集計して検証レポートを標準出力に表示。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、レイテンシ (avg/max/P95) 等。
    - Pass/Fail 基準を定義（例: 稼働率 >= 99%、Fill >= 90%、P95 <= 200ms 等）。
    - CLI: `--from` / `--to`（YYYY-MM-DD）、`--db`（DB パス）をサポート。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- `.env` の取り扱いに関する注意メッセージを config_setup に追加（.env を絶対に Git へコミットしないよう警告）。

---

注:
- 本 CHANGELOG はソースコードの内容から推測して記載しています。実際のリリースノート作成時はコミット履歴やリリース管理情報を参照して正確な差分を記載してください。
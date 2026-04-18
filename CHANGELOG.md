# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-18

Added
- 全体
  - 初回リリース。KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト / 実行管理
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御: プロジェクトルート下 `data/stop_requested.flag` を監視して安全にループ終了。
    - 監視は設定にかかわらず本番用の `sqlite_path` を使用して DB 接続を行う（監視データは一元管理）。
    - duckdb 接続を確立し SystemMonitor に渡す。
    - 起動時にプロセス優先度を "high" に設定（`set_process_priority` を呼び出し）。

  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、Paper Trading 用 DB（`data/paper_trading.db`）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: `data/stop_requested.flag` の存在をチェックし、既に立っている場合は起動を中止。実行中に検出した場合は Engine を停止。
    - ExecutionEngine の PID ファイル管理用パス（`data/execution.pid`）をサポート。

- 設定・環境変数管理
  - `config.py`
    - 環境変数の読み込み・解釈ロジックを実装。
    - プロジェクトルート自動検出 (`.git` または `pyproject.toml`) に基づき `.env` と `.env.local` を自動ロード。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - `.env` パースの改善:
      - `export KEY=val` 形式対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
      - クォートなしでのインラインコメント扱いをスペースやタブで判別。
    - 多数の設定プロパティを提供（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `paper_fill_mode`, `pid_file_path`, 各種閾値など）。
    - `Settings` クラスとグローバル `settings` を提供。

  - `config_setup.py`
    - 対話式ウィザードで `.env` ファイルの初期作成/更新を支援する CLI を追加。
    - シークレット項目は入力時にマスクし、既存値の再利用（Enter）や選択肢サポートを提供。
    - 書き込み時は `.env` にヘッダコメントを付与し Git へのコミットを注意喚起。

  - `validate_config.py`
    - 起動前の設定検証ツールを追加。
    - 必須環境変数チェック、`KABUSYS_ENV`/`LOG_LEVEL` の妥当性、DB パスの親ディレクトリ存在確認、`config/*.yaml` の存在とパース検証（PyYAML がある場合）などを実施。
    - `--strict` オプションで警告もエラー扱いにできる。
    - 本番モード (`KABUSYS_ENV=live`) 時の追加ガード（LINE 設定未設定・KILL_FLAG_CLEAR_ON_START 設定警告）を実施。

- ロギング / プロセスユーティリティ
  - `utils/logging_setup.py`
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler（標準出力）と、日次ローテーションの TimedRotatingFileHandler（デフォルト `logs/<app_name>.log`、30 日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - 環境変数 `LOG_LEVEL` / `LOG_DIR` による上書き、引数での指定をサポート。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールへフォールバック。

  - `utils/process_priority.py`
    - プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加（Windows/Linux/macOS 対応）。
    - `set_process_priority(level: "high"|"normal"|"low")` を提供。psutil の権限エラー等は警告ログでフォールバック。
    - `set_cpu_affinity(cpu_count: int | None)` により最初の N コアにピン留め可能。引数検証あり。

- ポートフォリオ構築（純粋関数群）
  - `portfolio/portfolio_builder.py`
    - 候補選定と重み計算関数を追加:
      - `select_candidates`（スコア降順、タイブレークは signal_rank）
      - `calc_equal_weights`
      - `calc_score_weights`（全スコアが 0 の場合に等配分へフォールバック）
  - `portfolio/risk_adjustment.py`
    - セクター集中（apply_sector_cap）や市場レジーム乗数（calc_regime_multiplier）を実装。
    - `apply_sector_cap` は既存保有のセクター時価を算出し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - `calc_regime_multiplier` は "bull"/"neutral"/"bear" に対して 1.0/0.7/0.3 を返す（未知値は警告後 1.0 にフォールバック）。
  - `portfolio/position_sizing.py`
    - 株数決定ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）、コストバッファ反映、残余キャッシュによる再配分ロジックを含む。

- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 用 SQLite DB から検証指標を抽出してレポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成立率（fill rate）、送信率（send rate）、P95 レイテンシなど。
    - デフォルト DB パスは `data/paper_trading.db`。`PAPER_TRADING_SQLITE_PATH` 環境変数または `--db` オプションで指定可能。
    - 判定基準（しきい値）を定義し PASS/FAIL 判定を出力。
    - P95 計算のユーティリティ実装。

- 研究用ファクター計算（骨組み）
  - `research/factor_research.py`
    - DuckDB を用いたモメンタム/バリュー/ボラティリティ/流動性等のファクターを計算するモジュールを追加（設計と定数を含む）。関数シグネチャと骨組みを提供。
    - 実装は DuckDB の `prices_daily` / `raw_financials` テーブル参照を想定。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Notes / 注意点
- 監視 (run_monitoring) は「監視データの一元化」のため、実行環境にかかわらず Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。開発時に監視データを分離したい場合は sqlite_path を明示的に設定してください。
- 実行エンジン (run_execution) は paper_trading モード時に専用 SQLite (`paper_sqlite_path`) を使用して本番 DB との完全分離を行います。
- .env の自動ロードは便利だが、テストや特殊ケースで無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- process priority / cpu affinity の設定は OS 権限に依存します。権限不足や未対応環境では警告を出して安全にフォールバックします。
- `PAPER_FILL_MODE`（Paper Trading の約定モード）は "instant"/"partial"/"never"/"reject" のいずれかで、無効な値は起動時に例外を発生させます。

開発者向けメモ
- CLI 実行例:
  - 環境検証: python -m kabusys.validate_config
  - 設定ウィザード: python -m kabusys.config_setup
  - Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 監視起動: python -m kabusys.run_monitoring
  - 実行エンジン起動: python -m kabusys.run_execution

今後の改善予定（候補）
- factor_research の完全実装（SQL 実装と正規化、Zスコア統合）。
- portfolio ロジックのユニットテスト強化（特にスケーリング／端数処理）。
- ログハンドラのより柔軟な設定（外部ローテーションポリシー・リモート送信）。
- PID/ロック管理や graceful shutdown の追加強化（複数プロセス環境対応）。
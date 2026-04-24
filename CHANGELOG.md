# Changelog

すべての重要な変更は「Keep a Changelog」形式で記載します。  
このファイルは履歴の要約であり、コードの実装詳細はソースを参照してください。

フォーマット:
- Added: 新機能
- Changed: 変更・改善
- Fixed: バグ修正
- Deprecated / Removed / Security: 今回該当なし（必要に応じて追記）

-----------------------------------------------------------------------

## [Unreleased]

（次バージョンでの変更をここに記載）

-----------------------------------------------------------------------

## [0.1.0] - 2026-04-24

初回リリース。本リリースではシステム全体の実行・監視・設定・ポートフォリオ構築・検証ツールを含むコア機能を実装しています。

### Added
- 全体
  - パッケージ初期版を追加。バージョンは `kabusys.__version__ = "0.1.0"`。
  - DuckDB / SQLite を用いた分析・監視用データ管理をサポート（デフォルトのパスは `data/kabusys.duckdb`, `data/monitoring.db`）。
- 設定管理
  - 環境変数ロード・管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml で自動検出し、`.env` / `.env.local` を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
    - `.env` のパースは以下に対応:
      - export KEY=val 形式
      - シングル/ダブルクォート内でのバックスラッシュエスケープ
      - 行内コメントの取り扱い（クォート外かつ直前が空白/タブでのみコメント扱い）
    - 必須値取得ヘルパー `_require()` と Settings クラスを提供（J-Quants / kabu API 等の設定をプロパティで取得可能）。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を初期作成・更新する。各項目の説明付き。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - `.env` と config/*.yaml（存在する場合）の基本チェック、必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 等の妥当性確認。
    - `--strict` オプションで警告も失敗扱いにできる。
- 実行 / 監視
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を設定（"high"）。
    - KABUSYS_ENV が `paper_trading` の場合は専用 Paper DB（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用し、Mock ブローカ・ロジックと分離。
    - 起動／停止は `data/stop_requested.flag`（プロジェクトルート配下の data）で制御。実行 PID を `data/execution.pid` に管理。
    - ExecutionEngine の組立て（BrokerFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）とデフォルト RiskConfig を実装（パラメータはコード参照）。
  - SystemMonitor 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - ポーリングループ（デフォルト 60 秒）を提供。環境変数 `MONITOR_POLL_INTERVAL` で上書き可。
    - Monitoring は実行環境に関わらず本番（production）用の sqlite_path を使用する仕様。
    - 停止フラグ `data/stop_requested.flag` を検知して安全にループ終了。
- ロギング / プロセス制御
  - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに stdout 出力（StreamHandler）と日次ローテートファイル出力（TimedRotatingFileHandler、30日保持）を設定。
    - ログレベル・ログディレクトリは引数 / 環境変数 / デフォルトの順で解決。ログディレクトリ作成失敗時はコンソール出力にフォールバック。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差異を吸収して `set_process_priority(level)`（high/normal/low）と `set_cpu_affinity(n)` を提供。
    - psutil を利用。権限不足等で設定できない場合は警告してスキップ。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み算出（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、同点は signal_rank で破棄）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、スコア合計が 0 の場合は等金額にフォールバック）
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存ポジションによりセクター上限を検査し、新規候補を除外）
    - calc_regime_multiplier（regime に応じた投下資金乗数: bull/neutral/bear）
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：allocation_method ("risk_based"/"equal"/"score") に対応。lot_size（単元）で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリングを実装。スケール後の残差配分ロジックも実装。
  - 上記モジュールを package としてエクスポート（src/kabusys/portfolio/__init__.py）。
- 研究用ファクター計算
  - ファクター計算モジュールの骨組みを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity 等の計算仕様、DuckDB 接続を受ける設計方針を明記（モジュール内での定数と calc_momentum の雛形を含む）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper DB（--db オプションまたは PAPER_TRADING_SQLITE_PATH）からシステム稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）等を集計し、PASS/FAIL 判定を行う。閾値はソース内定義（例: 稼働率 >= 99%）。
    - 日付範囲指定（--from/--to）に対応。
- その他ユーティリティ
  - パッケージ構成用の空 __init__ ファイル群を追加（tools, utils 等）。

### Changed
- デフォルトのログ出力を stdout に統一（cron/Task Scheduler 連携を意識）。
- .env のロード順を OS 環境 > .env.local > .env とし、.env.local は OS 環境を保護しつつ上書き可能に変更（既存環境の保護機構を導入）。
- run_monitoring/run_execution 起動時にプロセス優先度を最初に設定するようにし、起動時の応答性・優先度確保を向上。

### Fixed
- 環境変数値のパースを堅牢化:
  - 引用符付き値のバックスラッシュエスケープ処理を実装し `.env` の複雑な文字列を正しく読み込めるようにした。
  - inline コメントの誤判定を改善（クォート内はコメントとして扱わない、クォート外は直前が空白/タブのときのみコメントと判断）。
- 実行スクリプトのリソースクリーンアップを強化:
  - run_monitoring と run_execution で finally ブロック内で DB 接続を確実にクローズするようにした。

### Notes / Caveats
- run_monitoring は「監視用 DB（sqlite_path）は環境に関わらず本番パスを使用する」という設計意図があります（監視データは本番パスへ集約する想定）。開発やテストで分離したい場合は sqlite_path を環境変数で変更してください。
- Process priority / CPU affinity の操作は OS 権限に依存します。権限不足や未サポート環境では警告を出してスキップします。
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ行います。未インストール時は YAML 検証をスキップして警告を出します。
- research/factor_research.py はファクター計算ロジックの骨格を含みますが、完全実装（全関数の完成）は別途継続実装が必要です。

-----------------------------------------------------------------------

メンテナンス方針、追加機能やバグ修正については今後のリリースで追記していきます。README やドキュメント（PortfolioConstruction.md 等）も合わせて参照してください。
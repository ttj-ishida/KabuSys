CHANGELOG
=========

この CHANGELOG は Keep a Changelog のフォーマットに準拠しています。  
セマンティクスはおおむね初期リリース向けの変更点をコードから推測して記載しています。

[Unreleased]
------------

なし。

[0.1.0] - 2026-04-19
-------------------

Added
- 基本パッケージ初期実装を追加。
  - src/kabusys/__init__.py にバージョン情報を追加（0.1.0）。
- 実行用エントリスクリプトを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行・停止フラグ検知を実装。
    - プロセス優先度を "high" に設定（set_process_priority 呼び出し）。
    - 実行中の PID を data/execution.pid に保存（pid_file に渡す）。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告を出す。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループを終了。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用する設計。
- 環境設定・検証ユーティリティを追加。
  - src/kabusys/config.py
    - 環境変数のラッパー Settings を提供。各種パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等）、閾値、動作モードフラグ（is_live/is_paper/is_dev）を取得。
    - .env の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を起点）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースは export 形式・クォートやエスケープ・インラインコメントを考慮した堅牢な実装。
    - PAPER_FILL_MODE の検証ロジック（instant/partial/never/reject）など。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env ファイルを生成・更新する CLI。
    - 項目定義に基づく入力、現在値の再利用、secret マスク表示、保存確認、.env のテンプレート書き出しを実装。
  - src/kabusys/validate_config.py
    - 起動前に必須環境変数や config/*.yaml、パス存在、KABUSYS_ENV の妥当性などをチェックする CLI。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス制御ユーティリティを追加。
  - src/kabusys/utils/logging_setup.py
    - ルートロガー設定ユーティリティ。コンソール stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）を設定。
    - LOG_LEVEL / LOG_DIR / レベル解決の順序や既存ハンドラのクリア処理を実装。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
  - src/kabusys/utils/process_priority.py
    - Windows/Linux/macOS の差分を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティ。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足時は警告を出してスキップ。
- ポートフォリオ構築・リスク調整・サイズ決定ロジックを追加（純粋関数群）。
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等比率配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等配分へフォールバックして警告。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有を元にセクターごとの上限 (max_sector_pct) をチェックし、新規候補を除外するロジック。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す。未知レジームは警告の上 1.0 でフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") に基づく発注株数計算を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に対するスケールダウンロジック、cost_buffer を考慮した保守的評価を実装。fractional remainder を用いた端数調整処理あり。
  - src/kabusys/portfolio/__init__.py で上記関数群をエクスポート。
- Paper Trading 検証レポート生成ツールを追加。
  - src/kabusys/tools/paper_verification_report.py
    - SQLite の paper_trading DB（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）を読み、期間指定でシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均 / 最大 / P95）を集計してレポート出力。
    - P95 算出ユーティリティ、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
- 研究用ファクタ計算基盤（部分実装）を追加。
  - src/kabusys/research/factor_research.py
    - Momentum / Value / Volatility / Liquidity の設計記述とモメンタム計算関数の実装着手（DuckDB 経由で prices_daily / raw_financials を読む設計）。（ファイル末尾付近で実装が途中で終わっている箇所あり）
- 監視用 DB 初期化ユーティリティを参照する import を追加（init_monitoring_db を各起動スクリプトで呼び出し）。
- 小さなユーティリティや空パッケージ初期化ファイルを追加。
  - src/kabusys/tools/__init__.py、src/kabusys/utils/__init__.py など。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 該当なし。

Notes / ユーザー向けメモ
- 環境変数自動読み込み
  - プロジェクトルートが特定できる場合、起動時に .env を自動読み込みします（OS 環境変数を保護）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env ウィザード
  - config_setup.py を実行すると安全に .env を作成できます。生成された .env は絶対に Git にコミットしないでください（README 相当のヘッダが付与されます）。
- 実行 / 監視スクリプト
  - run_execution/run_monitoring はデフォルトでログを logs/ に出力し、data/ 以下のファイル（PID, stop flag, paper_trading.db など）を参照します。環境変数でほとんどのパスを上書きできます。
- Paper Trading の分離
  - paper_trading モードでは paper_trading 用の SQLite を使用するため、本番データと混ざらない設計です（PAPER_TRADING_SQLITE_PATH で上書き可能）。
- ログ設定
  - setup_logging() は既存ハンドラをクリアして重複設定を防ぎます。ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。
- 注意点（既知の未実装 / TODO）
  - research/factor_research.py の一部（ファイル末尾）は実装途中で切れているため完全なファクター計算は現時点では未完。
  - position_sizing の price フォールバック（price が欠損した場合に前日終値等を使う）は TODO コメントあり。
  - apply_sector_cap は "unknown" セクターを除外しない仕様（設計上の明示）。

ライセンス、貢献、バグ報告
- この CHANGELOG はコードから推測して作成しています。実際の意図と異なる点がある場合は issue/PR をお願いします。
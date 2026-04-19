CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

v0.1.0 - 2026-04-19
-------------------

Added
- 初期リリース。以下の主要機能・モジュールを追加しました。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite（既定: data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアントのファクトリ経由でリアル/モックの切替を行う。
    - process priority を "high" に設定してから起動。
    - 停止はプロジェクトルートの data/stop_requested.flag を検知して行う。
    - 実行時 PID を data/execution.pid に記録する（Engine に pid_file パラメータを渡す）。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバック。
    - 監視用 DB（SQLite）は環境に関わらず本番 sqlite_path を使用して監視データを一元管理。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止を実装。

- 設定管理・初期化ツール
  - config.py
    - 環境変数 / .env ファイル読み込みのユーティリティ。
    - プロジェクトルートを .git または pyproject.toml から検出し、.env/.env.local を自動読み込み（OS 環境変数優先）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメントを考慮して安全に処理。
    - 各種設定プロパティ（DB パス、ログレベル、KABUSYS_ENV、Paper Trading 関連、監視閾値等）を提供。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）や KABUSYS_ENV の妥当性チェックを実装。

  - config_setup.py
    - .env を対話的に作成・更新するウィザード CLI。
    - デフォルト値提示、既存値の再利用、シークレット項目のマスク表示、保存前の確認ダイアログ等を備える。
    - 書き出し時に .env 作成テンプレート（コメント付き）を出力。

  - validate_config.py
    - 起動前チェック用 CLI。必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検査（PyYAML がインストールされている場合）を実施。
    - 本番モード（KABUSYS_ENV=live）向けの追加警告（LINE 通知設定や Kill Switch 設定など）。
    - --strict オプションで警告を FAIL として exit(1) を返すモードを提供。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - アプリ共通のログ初期化ユーティリティ。
    - stdout へ StreamHandler、日次ローテーション（TimedRotatingFileHandler）で logs/<app_name>.log に出力（30 日分保持）。
    - LOG_LEVEL / LOG_DIR の解決順や、ハンドラの二重登録防止を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

  - utils/process_priority.py
    - Windows と POSIX(Linux/Mac/FreeBSD) を吸収するプロセス優先度設定。
    - nice / Windows priority クラスを切替えて設定。設定に失敗した場合は警告を出して続行。
    - set_cpu_affinity() を実装してプロセスを最初の N コアにピン固定可能。

- ポートフォリオ構築（Portfolio Construction）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレークに signal_rank 使用）と候補上位切り出し。
    - 等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。スコア合計が 0 の場合は等配分へフォールバック（警告ログ）。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）：既存保有のセクター比率が上限を超える場合、新規候補を除外するロジック。unknown セクターは上限適用外。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング）。未知レジームは 1.0 でフォールバックし警告を出す。

  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score）。
    - 損切り幅、許容リスク率、単元株（lot_size）考慮、1 銘柄上限や aggregate cap（available_cash を越えた場合のスケールダウン）などを実装。
    - cost_buffer を考慮した保守的なコスト見積りと、残余キャッシュを使った lot 単位での再配分アルゴリズムを搭載。

- リサーチ / ファクター計算（下書き）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity などのファクター計算を行うモジュールの骨子を追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（関数 calc_momentum 等を含む、実装の一部が続きます）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均/最大/P95）を算出して判定 (PASS/FAIL)。
    - P95 計算、期間フィルタ（--from/--to）、PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB 指定可能。
    - 判定基準はソース内定数で定義（例: 稼働率 >= 99%、P95 <= 200ms など）。

- パッケージ定義
  - package root の __init__.py に __version__ = "0.1.0" を追加。

Changed
- N/A（初回リリースのため、変更履歴はありません）

Fixed
- N/A（初回リリース）

Deprecated
- N/A

Removed
- N/A

Security
- N/A（現時点で特筆すべきセキュリティ修正はありません）

Notes / 実運用上のポイント
- .env 自動ロードが有効な場合、OS 環境変数が保護され .env.local が .env を上書きする挙動になっています。テスト環境等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL 等は設定値の妥当性チェックを行います。無効値を設定すると起動時に例外が発生しますので .env 生成 / validate_config による事前チェックを推奨します。
- run_monitoring と run_execution はプロセス優先度を "high" に設定して起動します（プラットフォームにより権限不足で失敗する場合は警告が出ます）。
- 停止フラグ（data/stop_requested.flag）および kill/kill-clear 関連の挙動に注意してください。validate_config は本番環境用のガード（LINE 通知設定や Kill Switch 設定）を行います。
- ログは標準で logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリ作成に失敗するとコンソールのみの出力にフォールバックします。

Acknowledgements
- 初期実装の各モジュールは設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に基づいて構築されています。今後はユニットテスト、ドキュメントの充実、漏れのあるエッジケース処理の強化を予定しています。
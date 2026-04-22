Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに従います。

リリース日付の書式: YYYY-MM-DD

Unreleased
----------

(なし)

0.1.0 - 2026-04-22
-----------------

Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するメインスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行する。
    - 停止制御: data/stop_requested.flag を監視し、検知時にエンジン停止。実行 PID を data/execution.pid に出力する想定。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors, circuit_breaker_window_sec, max_drawdown）を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。不正値（0 以下や非数）はデフォルトへフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用（本番監視データは共通 DB を想定）。
    - 停止制御: data/stop_requested.flag を検知してループを終了。
- 設定管理とセットアップ
  - config.py: 環境変数読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出ロジック（.git または pyproject.toml を探索）を導入し、.env / .env.local の自動ロード機能を提供。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env のパースは export 形式、クォート文字列、バックスラッシュエスケープ、行内コメントの取り扱いに対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）。PAPER_FILL_MODE のバリデーションを実装（instant/partial/never/reject）。
  - config_setup.py: 対話式 .env ウィザードを実装。初期 .env 作成・更新を支援。
  - validate_config.py: 設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在および PyYAML によるパース検証、live 環境向けの追加ガードを実装。
    - --strict オプションで警告を FAIL として扱うモードを提供。
- ポートフォリオ構築関連の純関数群（DB 参照なし、純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選出（タイブレークに signal_rank を使用）。
    - calc_equal_weights, calc_score_weights: それぞれ等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等分配へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限のフィルタリングを実装（sell_codes を除外、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market_regime に基づく投下資金乗数（bull/neutral/bear）を実装。未知レジームは 1.0 へフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-position および aggregate cap 判定、available_cash によるスケールダウン、cost_buffer を考慮した保守的見積り、残余キャッシュを用いた端数配分アルゴリズムを実装。
  - portfolio/__init__.py で上記 API を公開。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力（logs/<app_name>.log、30 日保持）。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続。既存ハンドラの二重設定を避けるためハンドラをクリアしてから再構成。
    - ログレベル・ログディレクトリ解決ルールをドキュメント化。
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定を追加。
    - Windows/Linux/macOS/FreeBSD をサポート（対応不可能または権限不足時には警告してスキップ）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - DB（PAPER_TRADING_SQLITE_PATH）から system_status / trade_logs / risk_logs を集計し、稼働率、注文成功率、送信率、レイテンシ（avg / max / P95）等を算出して PASS/FAIL を判定。
    - CLI オプション: --from, --to, --db（--db > 環境変数 > デフォルトの優先度）。
    - デフォルト基準値（稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200 ms）を設定。
- research/factor_research.py: ファクター計算モジュール（Momentum 等）を追加（DuckDB を使って prices_daily / raw_financials を参照する設計）。設計ドキュメント参照の注釈を含む。
- パッケージメタ
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- 初期リリースのため該当なし（初期導入）。

Fixed
- 初期リリースのため該当なし（初期導入）。

Deprecated
- なし

Removed
- なし

Security
- 環境変数の取り扱いに注意する旨をドキュメント化（.env は決して Git にコミットしないことを .env ウィザードで明記）。

Notes / 備考
- 実行前の準備
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（validate_config でチェック）。
  - .env の作成: python -m kabusys.config_setup を推奨。
  - 設定検証: python -m kabusys.validate_config（--strict オプションあり）。
  - ログディレクトリ: デフォルトは logs/。作成に失敗した場合はコンソール出力のみになる。
  - data/ ディレクトリ: stop_requested.flag や execution.pid などを置く想定のため、適切なディレクトリ作成と権限設定を行ってください。
- 実行コマンド例
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Paper Trading と本番 DB の分離
  - paper_trading モードでは SQLite の保存先が PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に切り替わり、本番データベースと完全に分離されます。
- 既知の開発中箇所
  - research/factor_research.py は設計に従った実装を含みますが、ファイル末尾で未完（スニペットが途中で終了）になっている可能性があるため、実運用前に動作確認・追加実装が必要です。

マイグレーション / 導入手順（簡易）
1. リポジトリをクローンし、Python 仮想環境を作成・有効化する。
2. 必要パッケージ（psutil, duckdb, sqlite3（組み込み）、PyYAML（任意）など）をインストールする。
3. python -m kabusys.config_setup で .env を作成し、JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD を設定する。
4. python -m kabusys.validate_config で問題点を確認（--strict 推奨は運用前）。
5. data/ および logs/ ディレクトリのパーミッションを確認。
6. python -m kabusys.run_monitoring や python -m kabusys.run_execution を起動して動作確認する。

クレジット
- 初期実装（0.1.0）。今後のフィードバックで改良、テスト追加、ドキュメント整備を予定しています。
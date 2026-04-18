CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-11
-----------------

初回リリース — KabuSys 基本機能群の実装

Added
- コア CLI / 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全分離。
    - Engine をデーモン（バックグラウンドスレッド）で実行し、data/stop_requested.flag による外部停止制御に対応。
    - 起動時にプロセス優先度を "high" に設定。
    - execution.pid に PID を書き込む仕組み（pid_file を使用）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用して監視テーブルを記録。
    - stop flag（data/stop_requested.flag）検知で安全にループ終了。
- 設定管理
  - config.py: 環境変数読み込み・アクセス用 Settings クラスを実装。
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - 多数の設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視および閾値 / 環境判定など）。
    - 入力値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - config_setup.py: 対話式 .env 作成ウィザードを実装（.env の読み書き、既存値の再利用、シークレットマスク表示など）。
  - validate_config.py: 起動前の設定検証ツールを実装（必須環境変数や config/*.yaml の存在・パース確認、--strict オプション）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア順ソートと上位 N 抽出。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存保有を基に当該セクターの新規候補を除外、unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 発注株数算出（risk_based / equal / score の配分方式、単元株丸め、per- と aggregate cap、cost_buffer を考慮したスケーリング）を実装。
    - 投入資金が available_cash を超える場合のスケールダウンと残差処理（lot 単位での再配分）。
- ユーティリティ
  - utils/logging_setup.py:
    - setup_logging(): stdout ストリームハンドラ + 日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。logs/ ディレクトリを自動作成し、ファイル作成に失敗した場合はコンソールログのみでフォールバック。
    - LOG_LEVEL / LOG_DIR の解決順をサポート。
  - utils/process_priority.py:
    - set_process_priority(): Windows / POSIX を吸収したプロセス優先度設定を実装（権限不足時は警告してスキップ）。
    - set_cpu_affinity(): 指定コア数への固定（存在しない場合や権限不足時は警告してスキップ）。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_* から呼び出し、監視用テーブルの存在を保証（冪等）。
- DuckDB 統合
  - 複数箇所で duckdb 接続を受け付ける設計（ExecutionEngine／分析用処理向け）。
- Tools
  - tools/paper_verification_report.py:
    - ペーパートレード用検証レポート生成ツールを実装（システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計）。
    - P95 計算や期間フィルタ（ISO8601 UTC 文字列化）、閾値による PASS/FAIL を提供。
- Research
  - research/factor_research.py:
    - ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）設計と一部実装骨子。DuckDB の prices_daily / raw_financials テーブルを参照する想定。

Changed
- .env 読み込み仕様
  - .env のパースが厳密化（export KEY=val 形式の対応、シングル/ダブルクォートのバックスラッシュエスケープ対応、インラインコメントの扱い等を実装）。
  - .env.local を .env の上位で上書き（OS 環境変数は protected して上書きされない）。
- ログ出力
  - StreamHandler は stdout を使用（stderr ではなく）。これはタスクスケジューラや cron の出力リダイレクト運用を意識した設計。
- DB パスの扱い
  - run_monitoring は環境にかかわらず production sqlite_path を使用するよう明示的に設計（監視データを本番 DB に集約する意図）。
  - run_execution は paper_trading の場合に paper_sqlite_path を使用して完全分離。

Fixed
- 環境変数パースの不整合を修正（上記「Changed」の .env パース改善により、引用符付き値や export プレフィックス、インラインコメントの誤認識を修正）。

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known issues / TODO
- research/factor_research.calc_momentum の実装が途中で終端（ファイル末尾に未完の箇所あり）。本関数はまだ完全実装されていないため、投入前に追加実装が必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に 0.0 がある場合にエクスポージャーが過小見積りされ、期待通りに除外されない可能性あり。コメント内でフォールバック価格（前日終値など）を使う拡張が TODO として示されている。
- portfolio/position_sizing:
  - 将来的に銘柄別単元（lot_size）をサポートする旨の TODO がある（現状は全銘柄共通の lot_size を想定）。
- ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続するが、このときは標準エラーへ直接メッセージを出力するため、環境によっては拾いにくい可能性がある。
- set_process_priority / set_cpu_affinity は権限不足や未対応 OS で失敗する可能性があり、その場合は警告を出してスキップする設計。

Migration / Upgrade notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。validate_config で未設定だとエラーが報告される。
- .env の取り扱い:
  - 自動読み込みはプロジェクトルートが検出される場合にのみ行われる（.git または pyproject.toml を基準）。テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- Paper Trading:
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH を設定してペーパートレード DB を分離することを推奨。

作者注
- ドキュメントコメントやコード中に設計方針／制約／将来の拡張予定を多く含めています。実運用前に validate_config と config_setup を使って設定を確認してください。
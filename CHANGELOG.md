Keep a Changelog に準拠した CHANGELOG（日本語）
※この変更履歴はソースコードの内容から推測して作成しています。

0.1.0 - 2026-04-19
-----------------

Added
- 起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 停止フラグファイル data/stop_requested.flag を監視して安全にループを終了。
    - 監視は KABUSYS_ENV にかかわらず production の sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に切り分けて Mock ブローカーで動作。 production DB と完全に分離。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用した起動/停止制御。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で安全に停止するループを実装。
- 設定管理・初期化ツール
  - config.py
    - Settings クラスを提供。環境変数から各種設定値を取得・検証。
    - .env 自動ロード機能（プロジェクトルート自動検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - PAPER_FILL_MODE のバリデーション、paper_trading 用 DB パス、各種閾値・フラグなどをプロパティで提供。
    - env 値や LOG_LEVEL の妥当性チェックを行う。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。既存 .env 読み込みやシークレット表示（マスク）に対応。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、PyYAML が無い場合の処理、KABUSYS_ENV=live 時の追加警告などを実装。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガー設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフェイルセーフを備える。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py
    - Windows / POSIX の差異を吸収してプロセス優先度を設定するユーティリティを追加（set_process_priority）。
    - CPU affinity を第 N コアに固定する set_cpu_affinity を提供（実行失敗時は警告でスキップ）。
    - 起動スクリプト（monitoring/execution）で最初に優先度を "high" に設定する採用。
- ポートフォリオ構築関連（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコア全てが 0 の場合のフォールバック警告あり。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を追加。
    - セクターが "unknown" の扱いや、過剰セクター除外のロジックを実装。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes を実装。
    - allocation_method に "risk_based", "equal", "score" をサポート。lot_size（単元株）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer（手数料/スリッページ見積）等を考慮。
    - 価格欠損時のスキップやログ出力の扱いを実装。
- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db の呼び出しにより、監視スキーマの存在を起動時に保証（冪等）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。日付フィルタ、データ不足ハンドリング、各種閾値（稼働率、成立率、送信率、P95 レイテンシ）による PASS/FAIL 判定、レポートの整形出力を実装。
    - DB パス解決: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト。
- 研究用モジュール（開始）
  - research/factor_research.py（作業中）
    - ファクター計算モジュールの骨格を追加。DuckDB 接続を受け取り prices_daily/raw_financials を参照して Momentum/Value/Volatility/Liquidity 等を計算する方針（calc_momentum の実装が途中であることを示唆）。

Changed
- パッケージ初期リリースにつき大規模な追加が中心。ログ出力はデフォルトで logs/ に日次ローテーションを行うように統一。

Fixed
- run_monitoring のポーリング間隔取得ロジックで不正な環境変数値（0 や非整数）を検知した際に警告を出しデフォルトにフォールバックするように改善（time.sleep の ValueError 回避）。
- 設定読み込み（.env）のパースロジックを強化（クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い等）。

Notes
- 安全設計:
  - 実行系（ExecutionEngine）は paper_trading と production を明確に分離（DB とブローカー実装を切替）。
  - 停止フラグと PID ファイルにより外部からの安全停止・起動制御をサポート。
  - 本番環境（KABUSYS_ENV=live）では追加の警告（LINE 設定や Kill Switch のクリア設定等）を出す設計。
- 自動 .env ロード:
  - デフォルトでプロジェクトルートの .env/.env.local を自動的に読み込む（ただし OS 環境変数は保護）。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DB 初期化:
  - 起動時に監視テーブルが存在しない場合でも init_monitoring_db によって冪等に初期化されるため、初回起動の失敗を軽減する設計。
- 未完成箇所:
  - research/factor_research.calc_momentum 以下の実装が途中（ファイル末尾が切れている）ため、本リリースでは完全なファクター計算セットは未搭載。今後のリリースで追加予定。

References
- 環境変数の主な名前:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, LOG_DIR, MONITOR_POLL_INTERVAL, KILL_FLAG_CLEAR_ON_START, PID_FILE_PATH, KILL_FLAG_PATH, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

今後の予定（想定）
- research/factor_research の完全実装（全ファクター計算）
- Strategy / Execution の詳細ユニットテスト拡充
- ログローテーション・ログ保管ポリシーの運用面整備
- portfolio モジュールの拡張（銘柄別 lot_size、過去価格フォールバック等）

以上。
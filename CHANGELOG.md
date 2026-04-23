# CHANGELOG

すべての注目すべき変更点はここに記載します。  
このファイルは Keep a Changelog の形式に準拠しています。

履歴
=====

Unreleased
----------

（現在のコードベースは初回リリース向けのまとまった機能群を含んでいるため、以下は初版リリースの記録です。）

[0.1.0] - 2026-04-23
-------------------

Added
- 全体
  - パッケージ初期リリース (バージョン 0.1.0)。
  - モジュール構成を整理し、実運用向けの起動スクリプト・ユーティリティ・ポートフォリオ構築ロジック・解析ツール群を提供。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。
    - 停止制御に data/stop_requested.flag を使用して安全にループを抜ける仕組みを実装。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計を採用。
    - duckdb を併用して分析用接続を確保。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを行う。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、専用の MockBrokerClient を使用し、データは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に分離。
    - 起動前に停止フラグと PID 管理（data/execution.pid）をサポート。
    - スレッド（daemon）でエンジンを実行し、停止フラグ検知で安全停止。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を組み込み、初期ポートフォリオ値を broker.get_available_cash() から取得して初期化。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行パーサを実装（`export KEY=val`、シングル/ダブルクォート中のエスケープ、インラインコメントの扱いを考慮）。
    - Settings クラスを提供し、各種環境変数（J-Quants、kabu API、LINE、DB パス、監視閾値、システム設定等）をプロパティで取得。バリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を行う。
    - デフォルト値やパスの expanduser 対応を備える。

  - validate_config.py
    - CLI ベースの設定検証ツールを追加。
    - 必須 / 任意環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML が使える場合は）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 設定や Kill Switch の自動クリア設定）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

  - config_setup.py
    - インタラクティブな .env 作成ウィザードを追加。
    - J-Quants・kabu API 等の必須項目や、ログレベル・DB パス・Kill Switch 設定などを対話的に入力し .env を生成／更新する機能を実装。
    - 既存 .env の読み込みと既存値の再利用、シークレット項目のマスク表示、保存確認までのフローを提供。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化関数 setup_logging を実装。
    - stdout への StreamHandler（標準出力）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック。
    - ログレベルの解決は引数 > 環境変数 LOG_LEVEL > デフォルト "INFO" の順。
    - 30 日分のローテーション保持をデフォルトに設定。

  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。
    - psutil を利用して Windows / POSIX（Linux, Darwin, FreeBSD 等）で適切な優先度を設定、権限不足等の例外は警告でスキップする。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補抽出 select_candidates（スコア降順、同点は signal_rank でブレーク）、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）を提供。

  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap を実装。既存保有のセクター別エクスポージャを計算し、上限を超えるセクターの新規候補を除外する（"unknown" セクターは緩和）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear に対応、未知レジームは 1.0 でフォールバック）を提供。

  - portfolio/position_sizing.py
    - 複数の配分方式（risk_based, equal, score）に対応した株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、総投下上限（max_utilization）や cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap のスケーリング、残差処理によるロット単位での再配分などを実装。
    - risk_based モードでは stop_loss_pct と risk_pct から理論株数を計算し、現有保有を差し引いた追加発注量を求める。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から system_status, trade_logs, risk_logs を参照して各種指標（稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95））を算出。
    - P95 計算、期間フィルタ (--from / --to)、閾値を定義して PASS/FAIL 判定を行う（デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - DB が存在しない・テーブルがない場合でも安全にフォールバックしてレポート出力。

- 研究用ファクター計算（解析）
  - research/factor_research.py
    - DuckDB を利用したファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity を計画）。
    - calc_momentum 等の関数設計を導入（prices_daily / raw_financials テーブルのみ参照、結果は (date, code) をキーとした dict リストを返す方針）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 環境変数ファイル (.env) は絶対に Git にコミットしない旨を config_setup のヘッダに明記。

Notes / 注意事項
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされます（配布パッケージ化された環境での安全措置）。
- run_monitoring は monitoring 用 DB を常に本番用 sqlite_path に接続します（環境にかかわらず）。ペーパートレードと分離して運用したい場合は実行設計に注意してください（実行エンジン側は paper_trading で paper_db を使う設計になっています）。
- process_priority / cpu_affinity の設定は実行権限やプラットフォームに依存します。権限不足時は警告ログを出してスキップします。
- ログファイル出力先ディレクトリが作成できない場合はファイル出力を無効化して stdout のみで継続します。

今後の予定（例）
- factor_research の各ファクター実装完了とテスト追加。
- ExecutionEngine / BrokerClient の追加テスト・統合テスト。
- 銘柄別単元（lot_size）や手数料モデルの拡張（stocks マスタの導入）。
- config ファイル（config/*.yaml）に対するより厳密なスキーマ検証（pykwalify / jsonschema 等の導入検討）。

----------------------------------------
この CHANGELOG はリポジトリ内のコードをもとに推測して作成しています。実際のコミット単位の差分や過去履歴が存在する場合はそちらに合わせて更新してください。
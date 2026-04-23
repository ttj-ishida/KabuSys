Keep a Changelog
================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-04-23
-------------------

Added
- 基本リリース: KabuSys 初回公開（バージョン 0.1.0）。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告の上でデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する（監視 DB は本番 DB を参照）。
    - 停止制御はプロジェクトルート下 data/stop_requested.flag ファイルにより行う。
    - duckdb 接続の利用を想定（duckdb を接続）。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient を利用する設計想定）。
    - プロセス優先度を開始時に "high" に設定。
    - BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立てて実行（スレッドで実行、停止フラグ監視による安全停止）。
    - 起動時に停止フラグが既にある場合は起動を行わない。実行中は data/execution.pid を PID ファイルとして扱う。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env のパースを強化（export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント考慮）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供し、アプリで必要な設定値（J-Quants / kabu API トークン、DB パス、paper_trading 設定、監視しきい値、環境判定ロジックなど）をプロパティとして取得可能に。
    - PAPER_FILL_MODE の入力検証（instant|partial|never|reject）を実装。
    - 環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）のバリデーションを実装。

  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* など）と保存ロジックを提供。
    - デフォルト値・シークレット項目のマスク表示・保存確認を実装。

  - validate_config.py
    - .env と config/*.yaml の起動前検証用 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の検証、DB パス親ディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML がインストールされていればパース検証も実施）、本番環境向けの追加ガードを実装。
    - --strict オプションで警告を FAIL として扱うモードを追加。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加。StreamHandler(stdout) と TimedRotatingFileHandler（日次ローテーション、30 日分保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL 環境変数対応、ファイル作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py
    - プラットフォーム差（Windows / POSIX）を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加（psutil 使用）。
    - CPU affinity 設定ユーティリティ set_cpu_affinity を提供（最初の N コアにピン留め）。
    - アクセス権限不足や未対応 OS では警告ログを出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選別（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を追加。score が全て 0 の場合は等金額配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有・価格マップに基づいてセクターごとのエクスポージャを計算し、上限超過セクターの新規候補を除外。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知のレジームは警告のうえ 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を実装。
    - allocation_method により risk_based / equal / score をサポート。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、合計投下上限（max_utilization）および aggregate cap スケーリング、cost_buffer（手数料・スリッページ見積り）を考慮。
    - risk_based ではリスク許容率（risk_pct）と損切り率（stop_loss_pct）によりベース株数を算出。
    - 価格欠損時のスキップやログ出力の挙動を実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加。
    - SQLite（デフォルト data/paper_trading.db / 環境変数 PAPER_TRADING_SQLITE_PATH）を読み分析し、稼働率、注文成功率、送信率、P95 レイテンシ等を集計。
    - P95 計算、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db オプションをサポート。

- 研究モジュール（基礎実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム / ボラティリティ / バリュー / 流動性等を想定）。DuckDB を用いた prices_daily / raw_financials 参照設計。

Changed
- 初回リリースのため変更履歴なし（新規追加のみ）。

Fixed
- 初回リリースのため修正内容なし。

Security
- 機密情報 (.env) の Git 管理禁止を README 相当の注意書き（config_setup にコメントとして出力）で明示。

Notes / マイグレーション・運用上の注意
- 停止制御:
  - run_monitoring/run_execution はプロジェクトルート下 data/stop_requested.flag による停止検出を行う。サービス停止時は該当ファイルを作成することで安全に停止させられる。
  - kill flag（KILL_FLAG_PATH / data/kill.flag）や KILL_FLAG_CLEAR_ON_START の挙動は Settings 経由で制御される。
- データベース:
  - 監視（monitoring）は常に sqlite_path（デフォルト data/monitoring.db）を使用する設計。paper_trading 環境では run_execution が paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と明確に分離する。
- ロギング:
  - デフォルトで logs/<app_name>.log に日次ローテーションでログを出力（30 日保持）。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続する。
- 環境変数自動読み込み:
  - .env 自動読み込みはデフォルトで有効。テスト等で自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- Paper Trading:
  - PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。不正値は起動時エラーとなるため注意。
- 依存:
  - duckdb, psutil は動作時に必要。validate_config にて PyYAML が存在する場合は config/*.yaml のパース検証を行う。存在しない場合は YAML 検証をスキップして警告を出すのみ。

Acknowledgements
- 本リリースは初期機能群（監視・実行起動・設定管理・ポートフォリオ構築・位置決め・ユーティリティ・検証ツール）を含みます。今後、Strategy/Execution の詳細ロジック、テスト、ドキュメント拡充、運用自動化に関する改善を予定しています。
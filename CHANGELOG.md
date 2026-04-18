CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
Semantic Versioning を意識した変更分類を行っています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 全体
  - 初期リリースを追加。パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。
- 設定関連
  - 環境変数 / .env の自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 複雑な .env のパース（export 構文、クォート内のエスケープ、インラインコメント扱いなど）に対応。
  - Settings クラスを実装し、アプリケーションで使用する各種設定値をプロパティ経由で取得可能にした（J-Quants、kabu API、DB パス、監視閾値、実行環境判定など）。
  - PAPER_FILL_MODE や PAPER_TRADING_SQLITE_PATH など、Paper Trading 用の設定をサポート。
- 設定ツール
  - 対話式 .env 設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の読み込み、既存値の再利用、機密項目のマスク表示、保存機能を提供。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数や KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース（PyYAML が存在する場合）をチェック。
    - --strict モードをサポート（警告を失敗扱いにする）。
- 実行/監視スクリプト
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し本番 DB と分離。
    - BrokerClientFactory を使って実際の/モックブローカーを切り替え可能。
    - ExecutionEngine をスレッドで起動し、 data/stop_requested.flag による外部停止、pid ファイル管理等を考慮。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors 等）を提供し、初期ポートフォリオ値は broker.get_available_cash() から取得。
  - SystemMonitor（監視）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - data/stop_requested.flag による停止検知、例外時のログ出力を実装。
- ロギング・プロセス制御
  - 統一的なロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR 指定と引数優先の解決ルールを実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使用することで cron/Task Scheduler などからの起動時にリダイレクトしやすくした。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/Mac の差分を吸収して優先度設定（high/normal/low）を行う。
    - CPU affinity を最初の N コアに設定する set_cpu_affinity を実装。権限欠如等の例外は警告にフォールバック。
- ポートフォリオ構築（Portfolio）
  - 銘柄選定・重み計算モジュールを追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順＋タイブレーク）、calc_equal_weights、calc_score_weights（スコア全0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数を追加（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap：既存保有のセクター別時価が max_sector_pct を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier：'bull'/'neutral'/'bear' に応じた乗数（1.0/0.7/0.3）を返す。未知レジームは警告後 1.0 でフォールバック。
  - 株数決定（position sizing）を追加（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）で丸め、1 銘柄上限、aggregate cap（利用可能現金 available_cash に基づくスケーリング）、cost_buffer（手数料・スリッページ見積もり）を考慮したスケーリングロジックを実装。
- Paper Trading 検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を SQLite（PAPER_TRADING_SQLITE_PATH）から集計してレポート出力。
    - P95 計算、期間フィルタ、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
- 研究用ファクター計算基盤
  - ファクター計算モジュールの雛形を追加（src/kabusys/research/factor_research.py）。
    - Momentum/Value/Volatility/Liquidity の設計方針と定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - calc_momentum の雛形（引数・処理設計）を実装（実装途中まで含む）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Notes / Implementation details
- run_execution.py と run_monitoring.py はプロセス優先度を起動直後に "high" に設定するように呼び出すコードを含み、実行時の優先度向上を試みますが、権限不足などで失敗した場合は警告を出して継続します。
- .env のパースロジックはシェル風のクォートとエスケープをある程度サポートしますが、完全なシェルパーサーではない点に留意してください（意図しない構文はスキップされます）。
- Portfolio 関連は純粋関数で DB 参照を行わない設計（単体テストしやすい）です。
- Paper Trading 用 DB と本番監視 DB は明示的に分離される設計になっています（paper_trading 環境では data/paper_trading.db を使用）。

今後の予定（TODO）
- factor_research.calc_momentum の実装完了および他ファクター（Value/Volatility/Liquidity）の実装。
- monitoring_db モジュールの提供（run_* スクリプトから参照されている init_monitoring_db 等の詳細実装）。
- ExecutionEngine / BrokerClient 周りの結合テストおよび mock の充実。
- 銘柄ごとの lot_size をマスタで持つ拡張（position_sizing の TODO）。

ライセンス、貢献方法等についてはプロジェクトの README を参照してください。
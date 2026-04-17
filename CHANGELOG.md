CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はリリース日です。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初回公開リリース: KabuSys パッケージを追加。パッケージバージョンは __version__ = "0.1.0"。
- 環境設定管理:
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 複雑な .env 行（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント）に対応する堅牢なパーサ実装。
  - Settings クラスを追加し、アプリケーション全体で利用する設定プロパティ群を提供（J-Quants / kabuステーション / DB パス / Paper Trading 設定 / 監視設定等）。
  - PAPER_FILL_MODE の値検証、KABUSYS_ENV / LOG_LEVEL の許容値チェックを実装。
- 環境設定ウィザード CLI:
  - python -m kabusys.config_setup による対話式 .env 生成・更新ウィザードを実装（既存 .env の読み込み、入力マスク、デフォルト・選択肢の提示、書き出し）。
  - .env のテンプレート出力（.env に書き込む際の注意書き/セクション付）。
- 設定検証 CLI:
  - python -m kabusys.validate_config による起動前チェックツールを実装。必須環境変数確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML 有りの場合は）パース検証、live 環境時のガードチェック等を行う。--strict オプションで警告を FAIL 扱いにできる。
- 実行系エントリスクリプト:
  - run_execution.py を追加。ExecutionEngine 起動のためのブローカー生成（BrokerClientFactory）、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、別スレッドでの engine.run_session 実行、停止フラグ監視、paper_trading 環境時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用するなどを実装。
  - RiskManager の初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_* 等）を設定し、初期の portfolio value を broker.get_available_cash() から取得する仕組みを追加。
  - 監視テーブルが存在することを保証するため init_monitoring_db を呼び出す（冪等）。
- 監視系エントリスクリプト:
  - run_monitoring.py を追加。SystemMonitor を使ったポーリングループ、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル監視、例外時のログ出力、SQLite / DuckDB 接続管理を実装。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する明示的な挙動。
- ポートフォリオ構築ライブラリ:
  - portfolio_builder: BUY シグナルの候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバック（警告を出力）。
  - risk_adjustment: セクター集中制限を行う apply_sector_cap（"unknown" セクターは制限を適用しない）、市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）を実装。
  - position_sizing: calc_position_sizes を実装。allocation_method に応じた株数算出（risk_based / equal / score）、単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer を用いた保守的見積り、端数処理のための残差配分ロジックを実装。
- リサーチ（ファクター計算）:
  - research/factor_research.py を追加。DuckDB を用いたファクター計算関数（calc_momentum, calc_volatility）を実装。モメンタム（1m/3m/6m / MA200乖離）、ATR 等を営業日ベースのウィンドウで計算し、データ不足時は None を返す設計。設計はドキュメント（PortfolioConstruction.md / StrategyModel.md 等）に準拠。
- ユーティリティ:
  - utils/process_priority.py: psutil を用いたクロスプラットフォームのプロセス優先度（high/normal/low）と CPU affinity 設定関数を実装。Windows / POSIX の差分吸収、権限不足や未対応環境での警告ハンドリングを行う。
- ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を実装。system_status/trade_logs/risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出し、閾値に基づいて PASS/FAIL を判定する。P95 計算、日付フィルタ (--from/--to/--db オプション) に対応。

Changed
- （初回リリースのため該当なし）

Fixed
- 環境変数読み込み・運用上の安全性改善:
  - .env の読み込みは既存 OS 環境変数を保護する仕組み（protected set）を導入。これによりシステム環境変数の意図しない上書きを防止。
  - MONITOR_POLL_INTERVAL の値検証を追加。0 以下や非整数が渡された場合は警告を出してデフォルト（60 秒）へフォールバックすることで time.sleep による例外を回避。
  - set_process_priority / set_cpu_affinity は権限不足や未対応機能発生時に例外で落ちないよう警告出力でフォールバックするよう改善。
  - calc_score_weights: スコア合計が 0 の場合にゼロ割や不正な重みを防止して等金額配分にフォールバック（警告）。
  - apply_sector_cap: セクター情報が欠落している銘柄を "unknown" 扱いにして誤ってブロックされないようにした。
  - position_sizing: 価格未取得（None/<=0）の銘柄はスキップして不正な株数算出を避けるロジックを追加。
  - run_execution/run_monitoring: 監視・実行プロセスが停止フラグを検知した際に安全に終了する仕組みを実装（PID ファイル・stop flag の扱い、例外ログ）。

Security
- .env の取り扱いに関する注意を config_setup の出力に明記（.env を絶対に Git にコミットしないこと）。ウィザードはシークレット項目を入力時にマスク表示する。

Notes / Design
- DuckDB / SQLite を組み合わせた設計:
  - DuckDB は分析（prices_daily / raw_financials など）用途、SQLite（monitoring.db / paper_trading.db）は監視・取引ログ用途に想定。
  - run_monitoring は監視データ用の本番 sqlite_path を常に使用する（KABUSYS_ENV に依存しない）。
  - run_execution は paper_trading 時に DB を分離（PAPER_TRADING_SQLITE_PATH）して本番データと完全分離する設計。
- 複数の設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に従った純粋関数群を提供し、DB 参照なしでメモリ内計算可能な実装（テスト容易性を重視）。

Known limitations / TODO
- position_sizing の lot_size は現状グローバル固定（将来的には銘柄別 lot_map を導入する予定）。
- apply_sector_cap の exposure 算出で価格欠損時は過少見積りが発生する可能性があり、前日終値や取得原価を用いたフォールバックを検討中（コードに TODO コメントあり）。
- research/factor_research の一部（calc_volatility の集計部分）は長い SQL を使用しており、今後の最適化余地あり。

Acknowledgements
- 初期実装にあたり設計文書群（PortfolioConstruction.md, StrategyModel.md 等）を参照して実装しています。
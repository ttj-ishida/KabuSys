CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に従って記載しています。  
日付はリポジトリ内容から推測して付与しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-23
------------------

Added
- 基本機能・アーキテクチャ
  - 初期バージョンの KabuSys を追加。パッケージバージョンは __version__ = 0.1.0。
  - モジュール分割により、実行（execution）、監視（monitoring）、ポートフォリオ（portfolio）、リサーチ（research）、ユーティリティ（utils）、設定（config）などを分離。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離して MockBrokerClient を利用（BrokerClientFactory を経由）。
    - engine を別スレッドで実行し、プロジェクトルートの data/stop_requested.flag により安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルを data/execution.pid に出力する運用に対応。
    - Execution 用の依存コンポーネント（OrderRepository、OrderManager、RiskManager、Reconciler）を組み立てるロジックを実装。RiskManager のデフォルトパラメータ（max_position_pct 等）をコード上に定義。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検出によりループ終了。監視は環境にかかわらず本番 sqlite_path を使用する挙動を明記。

- 設定関連
  - config.py
    - .env の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順と上書きルール（OS 環境変数保護）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
    - .env の行パースで export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメントの扱いなどを考慮した堅牢な実装。
    - Settings クラスで各種環境変数をプロパティとして取得。値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を行う。
    - paper_trading 用の paper_sqlite_path や pid/kill flag パス、しきい値（CPU/MEM/DISK）などを設定プロパティとして提供。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を実装。デフォルト値、選択肢、シークレット項目マスク表示に対応。
    - 保存前の確認表示および .env の書式テンプレート出力機能を提供。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数の存在・プレースホルダ検知、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けのガードチェックを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通して使えるロギング設定を提供。
    - コンソール出力は stdout を使用し、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で 30 日分保持。既存ハンドラをクリアして二重設定を防止する。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力を安全にスキップ。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を提供（set_process_priority）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未サポート環境に対するフォールバックと警告を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等配分へフォールバック。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター時価合計から上限超過セクターを判定し、新規候補を除外。unknown セクターは上限適用除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マップ、未知レジームは警告とフォールバック）。

  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り、残差の順序付けによる追加配分ロジックを含む。価格欠損時のスキップやログ出力も実装。
    - 将来的な拡張点（銘柄ごとの lot_size など）をコメントで明記。

- リサーチ（ファクター計算）スケルトン
  - research/factor_research.py
    - Momentum 等のファクター計算モジュールの骨組みを実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針、定数（短中長期窓など）を定義。calc_momentum の説明と設計が含まれる（実装途中の箇所あり）。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出し、閾値比較で PASS/FAIL 判定を出力。
    - CLI 引数 --from/--to/--db、環境変数 PAPER_TRADING_SQLITE_PATH に対応。DB が空またはテーブルがない場合の安全なフォールバック処理を実装。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes / Implementation details
- DB 関連: monitoring 用の SQLite と分析用の DuckDB を併用する設計。monitoring DB は起動スクリプト側でテーブル初期化（init_monitoring_db）を保証。
- 安全性: 本番環境（KABUSYS_ENV=live）向けのガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険性警告）を validate_config にて実装。
- 設定周りの堅牢性を重視しており、.env のパースや自動ロードルール、環境変数の検証ロジックが豊富に含まれる。

将来の改善案（コードにコメントあり）
- position_sizing: 銘柄別 lot_size を扱うための拡張（stocks マスタの導入）。
- apply_sector_cap: price の欠損時のフォールバック（前日終値や取得原価）を導入して過少見積りを防ぐ。
- factor_research: calc_momentum の実装完了および他ファクター（Value/Volatility/Liquidity）実装。

署名
-----
この CHANGELOG は提示されたソースコードの内容から推測して作成しました。実際のリリースノートとして公開する際は、リリース日や差分の確定情報（コミット/PR 番号など）を併記してください。
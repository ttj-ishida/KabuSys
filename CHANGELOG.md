Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。
このプロジェクトはセマンティックバージョニングを採用します。

0.1.0 - 2026-04-25
------------------

初回リリース。以下の主要機能・ユーティリティ群を追加しました。

Added
- 基本バージョン情報
  - package version を __version__ = "0.1.0" として追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の実行／停止制御（stop flag / pid ファイルの扱い）。
    - プロセス優先度を High に設定する仕組みを導入（utils.process_priority を利用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下／不正値はデフォルトにフォールバックして警告を出力。
    - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用するよう明示。
    - stop flag（data/stop_requested.flag）検知でループを安全に終了。

- 設定管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env と .env.local の読み込み順序を実装（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - Settings クラスを導入し、アプリケーションで使用する設定（DB パス、API トークン、KABUSYS_ENV、ログレベル、監視閾値など）をプロパティとして検証付きで提供。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）。
    - is_live / is_paper / is_dev 等のヘルパープロパティ。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - J-Quants / kabu API / DB パス / LINE 設定等の入力を支援。秘密項目はマスク表示。
    - .env 書き出しテンプレートを実装（Git にコミットしないよう注意書き付き）。

- 設定検証ツール
  - validate_config.py
    - 起動前に環境変数や config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML が利用可能な場合）、本番向けガード（LINE 未設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通的なログ初期化関数 setup_logging を追加。
    - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数からの解決をサポート。
  - utils/process_priority.py
    - Windows と POSIX（Linux/Mac 等）の差分を吸収してプロセス優先度（high/normal/low）を設定するヘルパーを追加。
    - CPU affinity を最初の N コアにピン留めする set_cpu_affinity を追加。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分の重みを計算。
    - calc_score_weights: スコア正規化による重み計算（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーが閾値を超える場合に新規候補を除外するロジック。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックして 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき発注株数を計算。
    - 単元株（lot_size）で丸め、1 銘柄上限／アグリゲート上限（available_cash）を考慮したスケーリング、cost_buffer による保守的評価、残余配分ロジックを実装。

- 監視・レポート関連
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）などを集計し PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ（--from / --to）、DB パスの指定（--db / 環境変数）をサポート。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。

- 研究用モジュール（部分実装）
  - research/factor_research.py
    - DuckDB を利用したファクター計算基盤（Momentum / Value / Volatility / Liquidity）を追加。モメンタム関連の定数と計算方針を実装（prices_daily / raw_financials を参照）。
    - （ファイル末尾で実装の続きが想定される：モメンタム計算関数等）

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / 注意事項
- .env ファイルは秘密情報を含むため絶対に Git にコミットしないでください。.env の自動読み込みはデフォルトで有効ですが、テスト環境等で無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。
- run_execution / run_monitoring は stop flag（data/stop_requested.flag）を用いた外部停止制御と pid ファイルの管理を行います。運用時は該当ファイル名・場所を確認してください。
- ロギングはデフォルトで logs/ に日次ローテーションで出力します。ログディレクトリが作成できない場合はコンソール出力のみになります。
- process_priority / set_cpu_affinity は権限や OS に依存します。設定に失敗した場合は警告が出力され、処理は継続します。
- PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL などは Settings により値検証が行われます。不正な値を設定すると起動時に例外が発生します。

今後の予定（例）
- research/factor_research の完全実装（各ファクターの SQL/集計ロジックの完成）。
- 監視・実行コンポーネント間のより細かなメトリクス連携とアラート機能の強化。
- 単体テスト・統合テストの整備と CI 連携。

--- 
（この CHANGELOG はコードベースからの推測に基づき作成されています。動作や設定値については該当ソースのドキュメント・ソースコメントを参照してください。）
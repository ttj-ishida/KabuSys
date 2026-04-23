CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。
（https://keepachangelog.com/ja/1.0.0/）

Unreleased
----------
- なし（作業中の変更はここに記載してください）。

[0.1.0] - 2026-04-23
-------------------
Added
- 初回リリース: KabuSys 自動売買基盤の基本コンポーネントを実装。
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
- 実行・監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離。
    - BrokerClientFactory を介してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session を別スレッドで実行。
    - 停止フラグ（data/stop_requested.flag）および実行 PID（data/execution.pid）を管理し、安全に停止可能。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
- 設定関連
  - config.py
    - Settings クラスで環境変数アクセスを集中管理（データベースパス、API トークン、LINE 設定、監視閾値等）。
    - .env 自動読み込み機能（プロジェクトルートの検出: .git / pyproject.toml を基準）。OS 環境変数を保護する上書き動作を実装。
    - .env の詳細なパース処理を実装（export プレフィックス、クォート文字列、エスケープ、インラインコメント処理など）。
    - paper_trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）や kill/ pid 関連の設定を提供。
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を実装。
    - 各種設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を対話的に編集可能。
  - validate_config.py
    - 起動前に .env および config/*.yaml の設定を検証する CLI を実装。
    - 必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在および PyYAML が利用可能であればパース検証を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合に等金額へフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとのエクスポージャー上限チェック。既存ポジションと当日売却予定を考慮して候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: 等配分/スコア/リスクベースの割当方式に対応した発注株数計算。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、コストバッファ対応を実装。
- ユーティリティ
  - utils.logging_setup
    - 統一的なログ設定関数 setup_logging を提供。stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）を設定。ログディレクトリ自動作成、既存ハンドラの再設定処理を実装。
  - utils.process_priority
    - set_process_priority / set_cpu_affinity を実装。Windows/Linux/macOS の差分を吸収（psutil 利用）。権限不足や未対応 OS では警告を出してスキップ。
- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成スクリプトを実装。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計し、PASS/FAIL 判定（閾値はソース内で定義）を行う。
    - --from / --to / --db オプションで期間・DB を指定可能。
- 研究用モジュール（骨組み）
  - research.factor_research
    - ファクター計算（Momentum, Value, Volatility, Liquidity）を行う設計と関数 calc_momentum の先頭実装（DuckDB 経由での prices_daily / raw_financials 参照を想定）。大規模な計算ロジックは今後追加予定。
- DB 接続
  - sqlite3 と DuckDB の併用を想定した接続処理を導入（monitoring 用 SQLite、分析用 DuckDB）。
- 安全性・堅牢性
  - 停止フラグ（stop_requested.flag）や kill flag の扱いを標準化し、安全にプロセスを停止できる仕組みを導入。
  - 設定値検証やファイル存在チェック、例外発生時のログ出力やフォールバック処理を各所に追加。

Changed
- n/a（初回リリースのため履歴上の「変更」はありません）。

Fixed
- n/a（初回リリースのため履歴上の「修正」はありません）。

Security
- 現状、機密情報（API トークン等）は .env として管理する前提。生成された .env を絶対に Git にコミットしないことを README 等で注意すること。

Notes / Known limitations
- research.factor_research は計算ロジックの骨格を提供しているが、主要な SQL / 集計ロジックの実装はまだ完了していない箇所がある（ファイル末尾で未完のコード断片あり）。
- position_sizing の lot_size は現在グローバル共通であり、将来的に銘柄別 lot_map に対応する予定（TODO コメントあり）。
- apply_sector_cap は price_map に価格欠損（0.0）がある場合にエクスポージャーが過少見積もられる旨の注記がある。フォールバック価格の導入が今後の改善点。
- process_priority / cpu_affinity は psutil の機能と OS 権限に依存するため、環境によっては設定が失敗して警告となる場合がある。

References
- ソース内ドキュメント・コメントを元に要点を抽出して記載しています。詳細な使用方法・設計意図は各モジュールの docstring を参照してください。
CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠します。

フォーマット:
  - 追加: 新規機能・公開API
  - 変更: 既存機能の変更
  - 修正: バグ修正
  - 削除: 削除された機能
各項目はコードベースから推測して記載しています。

[Unreleased]
-------------

- （現時点の開発中変更点はありません）

[0.1.0] - 2026-04-23
--------------------

Added
- 全体: KabuSys 初期実装を追加。
  - パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。

- 実行スクリプト:
  - run_execution:
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は専用の紙上発注 DB（data/paper_trading.db など）を使用し、本番 DB と明確に分離。
    - BrokerClientFactory によるブローカークライアント生成（本番/モックを選択可能）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ (data/stop_requested.flag) による安全停止に対応。
    - 実行時に process priority を "high" に設定（utils.process_priority）。

  - run_monitoring:
    - SystemMonitor のポーリングループを起動するスクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する（監視データは一貫して本番 DB に格納）。
    - 停止フラグ (data/stop_requested.flag) によるループ終了対応。

- 環境・設定管理:
  - config.py:
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 独自の .env パーサ実装（export 形式、クォート・エスケープ、インラインコメント処理などに対応）。
    - Settings クラスで環境変数アクセスをラップし、デフォルト値やバリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を実装。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）、PIDファイル、Kill Switch の設定を提供。

  - config_setup.py:
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を提供。
    - 各設定項目（実行環境、トークン/パスワード、DBパス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）の説明・デフォルト値・シークレット入力に対応。
    - 既存 .env の読み込みと Enter による既存値再利用、保存前の確認を実装。
    - .env ファイルのテンプレート書き出しロジックを実装（.env を絶対にコミットしない旨のコメント含む）。

  - validate_config.py:
    - 起動前に .env および config/*.yaml の妥当性を検証する CLI を提供。
    - 必須環境変数チェック (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD) や KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェックを実装。
    - PyYAML が利用可能なら YAML のパース検証も実施。--strict オプションで警告も失敗（exit 1）扱いにできる。
    - Live 環境向けの追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険性等）を実装。

- ポートフォリオ構築関連 (pure functions; メモリ内計算):
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N 件を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコアに基づく重み付けを計算。全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。

  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーが閾値を超える場合、同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバックし WARNING を出力。

  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づき各銘柄の発注株数を計算。
    - 単元株（lot_size）丸め、最大ポジション比率・利用率 (max_position_pct, max_utilization) を考慮。
    - risk_based モードでは許容リスク率 risk_pct と stop_loss_pct から株数を算出。
    - aggregate cap を超えた場合はスケーリングし、端数の分配を残差順に行うロジックを実装。
    - cost_buffer を用いて保守的にコスト見積り（スリッページ/手数料）を反映。

- 監視・実行共通ユーティリティ:
  - utils.logging_setup:
    - StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテーション・30 日保持）をルートロガーに設定する共通関数 setup_logging を実装。
    - ログレベルとログディレクトリは引数 / 環境変数 / デフォルトの順で解決。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - stdout を利用することで cron 等でのリダイレクト運用を想定。

  - utils.process_priority:
    - psutil を用いてプラットフォーム差異（Windows / POSIX）を吸収したプロセス優先度設定機能を実装（set_process_priority）。
    - CPU affinity 固定関数 set_cpu_affinity を提供（利用は任意）。権限不足や未対応環境では警告を出してスキップ。

- Monitoring / DB 初期化:
  - monitoring.monitoring_db への初期化呼び出し（init_monitoring_db）を run_monitoring / run_execution から実行し、必要な監視テーブルが存在することを保証（冪等）。

- Execution / Risk defaults:
  - RiskManager に渡す既定値を Execution スクリプト内で設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。initial_portfolio_value は broker.get_available_cash() から取得して初期化。

- paper_trading 検証ツール:
  - tools.paper_verification_report:
    - paper_trading 用 SQLite DB（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシなど）を集計し、閾値比較で PASS/FAIL を判定するレポート生成 CLI を提供。
    - レポートは期間指定 (--from / --to) と DB パス指定 (--db) に対応。
    - デフォルト閾値: 稼働率 99.0%, 成功率 90.0%, 送信率 95.0%, P95 レイテンシ 200 ms。

- 研究用ファクター計算:
  - research.factor_research:
    - DuckDB 接続を受け prices_daily / raw_financials を参照してモメンタム / Value / Volatility / Liquidity 等のファクターを計算する設計（calc_momentum 等）。純粋関数群で DuckDB を利用するアプローチを導入。
    - 設計において移動平均や ATR の日数等の定数を定義（例: MA200, ATR=20 等）。
    - （実装途中のファイルが存在。ファイル末尾が途中で切れているため、完全実装は今後の作業予定）

Changed
- 初期リリースのため変更履歴はなし。

Fixed
- 初期リリースのため修正履歴はなし。

Deprecated
- なし。

Removed
- なし。

Known issues / Notes
- research/factor_research.py が末尾で途中（ソース切れ）になっている箇所が確認される（calc_momentum の実装が途中で終わっている）。今後の実装完了が必要。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に 0.0（価格欠損）が含まれる場合にエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価等のフォールバック価格を利用する拡張が検討されている（TODO コメントあり）。
- process_priority / set_cpu_affinity / set_process_priority:
  - 実行環境の権限不足や未対応プラットフォームでは警告を出してスキップする実装になっている。
- .env の自動読み込みは便利だが、テスト等で無効化するためのフラグ (KABUSYS_DISABLE_AUTO_ENV_LOAD) を用意している点に注意。

Contributing
- バグ報告や機能改善の提案は issue を立ててください。research モジュールや実装途中の関数については PR を歓迎します。

License
- 各ファイルのヘッダに明示的なライセンス表記はないため、配布前に LICENSE の追加を推奨します。
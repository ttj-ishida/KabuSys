CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース: KabuSys Python パッケージ（バージョン 0.1.0）。
- 実行用スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルート/data/stop_requested.flag により制御。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して初期化。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に記録して本番 DB と分離。
    - エンジンの PID を data/execution.pid に記録する仕組みと停止フラグ検知による安全終了処理を実装。
- 設定管理
  - config.py: 環境変数読み込み・管理モジュールを追加。
    - プロジェクトルート（.git または pyproject.toml ベース）を探索して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env のパース実装は export 構文・クォート・インラインコメント等に対応。
    - Settings クラスで各種設定項目（J-Quants、kabu API、DB パス、Paper Trading 設定、監視しきい値、環境判定等）をプロパティとして提供。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等の環境変数をサポート。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式ウィザードで .env を作成・更新するツールを追加。
    - 標準的な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、Kill Switch オプション等）を網羅。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードチェック等を実行。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder
    - 銘柄選定 (select_candidates)、等配分重み (calc_equal_weights)、スコア重み (calc_score_weights) を実装。全体は副作用なしでメモリ内計算。
  - portfolio.risk_adjustment
    - セクター集中制限の apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。
    - セクターが "unknown" の場合は上限を適用しない等の仕様を明示。
  - portfolio.position_sizing
    - risk_based / equal / score ベースの株数計算を実装。単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）等を考慮したスケーリングロジックを実装。
    - 投下合計が利用可能現金を超える場合のスケールダウンと端数処理（lot_size 単位での再配分）を実装。
- 研究（Research）
  - research.factor_research: DuckDB を用いたファクター計算モジュールを追加。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR、相対 ATR）、Liquidity（20日平均売買代金等）を prices_daily テーブルから計算。
    - データ不足時は None を返すなど堅牢性を考慮。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（fill）、送信率（send）、リスク却下数、API レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を行う。
    - CLI で期間指定 (--from / --to) と DB パス指定 (--db) に対応。
    - デフォルト閾値（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）を設定。
- インフラ / ユーティリティ
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定ユーティリティを追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収し、nice / HIGH_PRIORITY_CLASS 等を使い分ける。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定する機能を提供（例外時は警告ログでスキップ）。
    - 権限不足や未対応プラットフォームでのフォールバックロジックを実装。
- データベース
  - DuckDB を分析用 DB として利用するパターンを採用（Settings.duckdb_path）。
  - monitoring 用の SQLite DB 初期化（init_monitoring_db をスクリプトから呼び出す）により監視テーブルの存在を保証。
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- なし（初回リリースのためなし）

Fixed
- なし（初回リリースのためなし）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 備考
- run_monitoring の挙動: Monitoring は環境にかかわらず本番用 sqlite_path を参照する設計になっているため、Paper Trading と完全分離したい場合は注意して設定（PAPER_TRADING_SQLITE_PATH 等）を確認してください。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされます。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config_setup により生成された .env は「絶対に Git にコミットしないこと」をドキュメントに明記しています。

-- END --
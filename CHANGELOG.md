CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。  

Unreleased
---------

(現在未リリースの変更はありません)

0.1.0 - 2026-04-24
-----------------

Added
- 基本リリース: KabuSys 初期実装を追加（バージョン 0.1.0）。
- 起動スクリプト:
  - run_execution.py を追加。ExecutionEngine の起動ロジックを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のバックグラウンド実行と停止フラグ監視を実装。
    - エンジン用 PID ファイル path（data/execution.pid）対応。
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動を実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化する挙動を明示。
    - 停止フラグ（data/stop_requested.flag）検出でループを正常終了。
- 設定管理:
  - config.py を追加。.env 自動ロード（.env → .env.local の順、OS 環境変数を保護）と環境変数アクセス用 Settings クラスを実装。
    - .env パースは export プレフィックス、クォート、エスケープ、インラインコメントの取り扱いに対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化を提供。
    - 各種プロパティ（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE / PID/KILL フラグ / リソース閾値 / env/log_level 判定等）を追加。
- 設定関連 CLI:
  - config_setup.py を追加。対話式ウィザードで .env を初期作成・更新する機能。
    - シークレット値のマスク表示、選択肢・デフォルト表示、保存確認を実装。
  - validate_config.py を追加。起動前に .env と config/*.yaml を検証する CLI を実装（--strict オプションを提供）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML があれば config/*.yaml のパース検証、本番環境用ガード（LINE 通知設定や Kill Switch 設定）を実装。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等分配・スコア加重配分の関数を追加。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知レジームのフォールバックとログ警告あり。
  - portfolio/position_sizing.py: 株数決定ロジックを追加（risk_based / equal / score の allocation_method 対応、lot_size による丸め、per-position 上限 / aggregate cap スケーリング、cost_buffer を考慮した保守的見積り）。
  - portfolio/__init__.py で上記関数群をエクスポート。
- ユーティリティ:
  - utils/logging_setup.py: 統一ログ設定ユーティリティを実装。
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / 引数による設定解決順を実装。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を抽象化。権限不足や未対応 OS では警告を出してスキップ。
- モニタリング DB 初期化:
  - monitoring/monitoring_db.init_monitoring_db の初期化呼び出し（起動時に監視テーブルが存在することを保証）。
- ツール:
  - tools/paper_verification_report.py を追加。Paper Trading の検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出。
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）。
    - PASS/FAIL の基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
- リサーチ:
  - research/factor_research.py を追加。DuckDB の prices_daily/raw_financials を使ったファクター計算の基盤を実装（モメンタム等のファクターを計算する意図、定数定義、calc_momentum の雛形あり）。
- パッケージメタ:
  - __init__.py に __version__="0.1.0" を設定。

Changed
- n/a（初期リリースのため変更履歴はなし）

Fixed
- n/a（初期リリース）

Removed
- n/a（初期リリース）

Security
- n/a（初期リリース）

補足・実装上の注意
- .env の自動読み込みはプロジェクトルート検出に依存（.git または pyproject.toml）。配布後や CWD に依存しない動作を意図。
- .env のロードは OS 環境変数を保護するため既存値を上書かない（.env.local は上書き可能）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- run_monitoring は監視用 DB 初期化のために常に Settings.sqlite_path を使用する設計。紙上の運用ルールに注意。
- run_execution は paper_trading モード時に paper_sqlite_path を使用することで本番 DB とデータ分離を行う。
- process_priority / cpu_affinity は権限やプラットフォームにより動作しない場合があり、その際は警告ログでスキップされる。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別拡張を想定した TODO コメントあり）。
- research/factor_research はファイル末尾で実装途中（calc_momentum の続きが必要）に見えるため、実運用前に追加実装およびテストが必要。

今後の予定（提案）
- factor_research の完全実装とユニットテスト追加。
- ExecutionEngine / SystemMonitor 周りの統合テスト、エンドツーエンドの paper_trading 検証。
- 銘柄ごとの lot_size 対応、手数料／スリッページの実測反映。
- config/*.yaml の雛形生成スクリプトと CI での validate_config 実行を自動化。

以上
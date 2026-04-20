CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はリリース日を表します。

unreleased
----------

（なし）

0.1.0 - 2026-04-20
-----------------

Added
- 初回リリース。KabuSys の基本機能群を追加。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて Engine を起動するスレッド駆動の実行ループを実装。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の取り扱い。
  - run_monitoring.py
    - SystemMonitor ポーリングループの起動エントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知で安全にループを終了。
- 設定関連
  - config.py
    - 環境変数 / .env / .env.local の読み込みロジックを実装（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .git または pyproject.toml を基準にプロジェクトルートを検出して .env ファイルの相対パス解決を行う。
    - .env の行パースは export プレフィックス、クォート内部のエスケープ、インラインコメント処理等に対応。
    - Settings クラスで各種設定プロパティを提供（J-Quants/Kabu API、DB パス、Paper Trading 設定、監視しきい値、環境／ログレベル等）。値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実施。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。既存の .env 読み取り、項目のマスク表示、確認後保存をサポート。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な妥当性検査を行う CLI。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検査（PyYAML があれば内容チェック）などを実施。
    - --strict モードで警告を失敗（exit 1）扱いに可能。
- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。全スコアが 0 の場合は等配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャを計算し、max_sector_pct を越えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に対する投下資金乗数を実装。未知の値は警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた株数計算を実装。
    - 単位株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケールダウン、コストバッファの適用、残余キャッシュに対する再配分ロジックを含む。
    - 価格欠損時のスキップやログ出力を実装。
- ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティ。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。ログレベル / ログディレクトリの解決順を実装。既存ハンドラのクリアを行い二重設定を防止。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows の priority class、POSIX の nice）と CPU affinity 設定を実装。アクセス権不足等は警告でスキップ。
- モニタリング / DB 初期化
  - monitoring/monitoring_db.py への参照（init_monitoring_db を起動スクリプトから呼び出し）により監視テーブルの存在を保証（冪等に初期化）。
  - SystemMonitor の呼び出し設計（check_once を定期実行、例外はログ出力して次サイクルへ継続）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から期間指定でレポートを生成。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等の指標を集計し、閾値に基づく PASS/FAIL 判定を出力。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ、DB パス指定（--db / PAPER_TRADING_SQLITE_PATH）、存在チェック、SQL の例外ハンドリングを実装。
- research/factor_research.py
  - ファクター計算基盤を追加（モメンタム、ボラティリティ等を想定）。DuckDB の prices_daily / raw_financials を利用する設計。関数群のコメント・定数を定義（実装は一部）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 備考
- バージョン番号はパッケージ __version__ により 0.1.0 としている。
- .env ファイルは機密情報を含むためリポジトリにコミットしないよう README 等で案内することを推奨（config_setup.py のヘッダーにも注意喚起あり）。
- 一部モジュール（例: research/factor_research.py）は実装の続きが存在するため、将来のサブリリースで機能拡張が見込まれる。
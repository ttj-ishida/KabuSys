CHANGELOG
=========

すべての重要な変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式で記載しています。

Unreleased
----------
- なし（次回リリースに向けた未確定の変更点をここに記載します）。

[0.1.0] - 2026-04-24
-------------------

Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を定義。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV により paper_trading 用に専用の SQLite（data/paper_trading.db デフォルト）を使用する分離設計。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）の扱いを実装。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を含む。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。Monitoring は環境に関わらず本番用 sqlite_path を使用。
    - stop フラグ / KeyboardInterrupt による優雅な停止処理を実装。
- 設定管理と初期化ツール
  - config.py: 環境変数・設定管理を実装。
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env 読み込みの優先順位: OS 環境 > .env.local > .env。自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD の仕組み。
    - .env のパースで export KEY=val 形式やクォート内のエスケープに対応。
    - Settings クラスで各種設定値をプロパティとして提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE の検証、paper_sqlite_path、PID/kill flag パス、閾値等）。
    - KABUSYS_ENV / LOG_LEVEL の検証と便利プロパティ（is_live/is_paper/is_dev）。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 入力プロンプト、既存値再利用、シークレットマスク、.env ファイルの書き込みロジックを実装。
    - デフォルト値や説明文を含む項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の有無チェック（PyYAML がない場合はスキップの旨を警告）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict モードで警告を FAIL 扱いにするオプションを提供。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定する共通ユーティリティを実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル解決順 (引数 > 環境変数 LOG_LEVEL > デフォルト) とログディレクトリ解決順 (引数 > LOG_DIR > デフォルト) を実装。
    - stdout を使用する理由（cron 等で stdout/stderr をリダイレクトしやすくするため）を明記。
  - utils/process_priority.py:
    - Windows/Linux/macOS 向けにプロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを実装。
    - psutil を利用し、プラットフォーム差分を吸収。権限不足や未実装の場合は警告して続行。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio/portfolio_builder.py:
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は警告して等配分へフォールバック。
  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）を実装。既存保有を基にセクター毎の時価を計算し、上限超過セクターの新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）を追加（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py:
    - allocation_method（risk_based / equal / score）に基づく株数計算を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に対するスケールダウン）ロジック、cost_buffer による保守的見積り、残差分の lot 単位での再配分アルゴリズムを実装。
    - risk_based では stop_loss_pct と risk_pct を用いたポジションサイズ算出を実装。
- リサーチ・ファクター計算（研究用）
  - research/factor_research.py （モジュール追加）
    - モメンタム等の定量ファクター計算を想定した基盤を追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。
    - モメンタム指標（1M/3M/6M リターン, MA200 乖離等）、ATR/出来高関連の計算方針を定義。
    - （注）ファイルは途中までの実装が含まれる（calc_momentum の実装冒頭までを含む）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）からデータを読み、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出してレポート出力。
    - デフォルトの合格閾値: 稼働率 >= 99.0%、注文成功率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms。
    - 日付フィルタ (--from / --to) と --db オプションをサポート。
- DB/モニタリングユーティリティ
  - monitoring.monitoring_db.init_monitoring_db の呼び出しが run_* スクリプトで組み込まれ、監視テーブルの冪等的初期化を保証。
- ドキュメント参照
  - 各モジュールに対して PortfolioConstruction.md / StrategyModel.md 等の設計文書を参照する旨の注記を含め、仕様に基づく設計であることを明示。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 補足
- 環境変数の自動読み込みはプロジェクトルートの検出に依存しており、配布後やテスト環境で自動読み込みを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD を用意しています。
- run_monitoring は監視用途の sqlite を常に本番 sqlite_path に接続する設計になっています。実運用時は sqlite_path の指し先に注意してください。
- Paper Trading と Live の DB は設計上分離されています（paper_trading 用 DB は paper_sqlite_path で上書き可能）。
- 一部モジュール（research/factor_research.py の詳細実装など）は今後の拡張を前提とした土台実装になっています。

---- 

この CHANGELOG はコードベースから推測して作成しました。実際のリリースノートを作成する場合は、コミット履歴／リリースノート等を参照して差分・責務・既知の問題点を具体的に反映してください。
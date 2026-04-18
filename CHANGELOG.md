CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- ドキュメント化や小さなリファクタリング（開発中）。主要な機能は 0.1.0 リリースに含まれています。

[0.1.0] - 2026-04-18
-------------------

Added
- プロジェクト初期リリースを追加（バージョン 0.1.0）。
- 実行用エントリスクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading DB（data/paper_trading.db、環境変数で上書き可）と MockBrokerClient を使用し、本番 DB と分離する挙動を実装。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
    - 停止制御: data/stop_requested.flag を監視して実行スレッドを安全に停止。
    - PID ファイル管理（data/execution.pid 相当のパス）。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をデフォルトで用意し、broker.get_available_cash() を初期ポートフォリオ値として使用。
- 監視用エントリスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止制御: data/stop_requested.flag を検知してループを終了。
- 設定管理
  - config.py
    - 環境変数を集約する Settings クラスを実装。プロパティで値取得・バリデーションを行う（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
    - .env 自動ロード機能を追加（プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込む）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - デフォルトの DB パス・各種設定値を定義（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）。
- 設定関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 入力プロンプト、シークレットマスク、既存 .env 読み込み、保存確認付きで .env を生成。
    - デフォルト値や選択肢を用意（KABUSYS_ENV, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース（PyYAML が存在する場合）を検査。
    - --strict オプションで警告をエラー扱いにできる。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを提供（setup_logging）。
    - stdout への StreamHandler（stdout を使用）と、日次ローテーション（TimedRotatingFileHandler）で logs/<app_name>.log を出力（30 日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / app_name による挙動カスタマイズ。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（set_process_priority）。
    - CPU affinity 設定関数 set_cpu_affinity を提供。
    - アクセス権限不足や未サポート環境での安全なフォールバック処理を実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates（スコア降順で候補選定）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア比率での重み、全スコアが 0 の場合は等金額にフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中制限。既存保有のセクター時価比で新規候補を除外）
    - calc_regime_multiplier（market regime に応じた投下資金乗数。bull/neutral/bear をサポート、未知値は 1.0 にフォールバック）
  - portfolio/position_sizing.py
    - calc_position_sizes（risk_based / equal / score の各 allocation_method をサポート）
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に収めるためのスケーリングと残差配分）、cost_buffer（手数料・スリッページ換算）を実装
    - price 欠損時のスキップやログ出力、TODO コメントで将来的な銘柄別 lot_size 拡張を記載
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）。閾値はファイル冒頭で定義（例: 稼働率 >= 99% 等）。
    - --from / --to オプションで期間指定が可能。データがない場合は N/A を表示し、Fail 判定の根拠を出力。
- リサーチ
  - research/factor_research.py（ファクター計算基盤の追加）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を用いたモメンタム・バリュー・ボラティリティ等の計算を行う設計を導入（モジュール化された計算関数 calc_momentum などを実装開始）。
    - 設計は外部 API に依存せず、DuckDB SQL + Python で完結する方針。

Changed
- パッケージメタ
  - __init__.py にて __version__ を "0.1.0" に設定。
- 設定のロード順・保護
  - .env 自動ロード時に OS 環境変数を保護（protected set）して .env.local の上書きや OS 環境の上書きを適切に制御。

Fixed
- 不正な MONITOR_POLL_INTERVAL 値や PAPER_FILL_MODE の不正値に対する明示的な検証・フォールバック処理を追加（警告出力）。

Known issues / Notes
- research/factor_research.py は機能設計を含む実装があるものの、ファイル末尾で未完の箇所（実装途中・補完必要）が確認されます。実運用前に完全実装とテストが必要です。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価の使用）は TODO として残っています。価格欠損がある場合の挙動に注意してください。
- apply_sector_cap は "unknown" セクターを上限適用から除外する仕様です。マスタにセクター情報が無い銘柄は塩漬け防止のため意図的に除外しています。
- logs ディレクトリや data ディレクトリの親パスが存在しない場合、起動時に自動作成を試みますが権限等の理由で作成できない可能性があります。その場合はログファイル出力が無効化され、コンソールのみでログが出力されます。

Migration notes
- 既存環境から導入する場合は .env（.env.local）をプロジェクトルートに配置してください。config_setup.py による対話ウィザードで簡単に初期化できます。
- 本番運用（KABUSYS_ENV=live）の前に python -m kabusys.validate_config で設定検証を強く推奨します（--strict モードで警告も FAIL 扱いにできます）。
- Paper Trading を行う場合は PAPER_TRADING_SQLITE_PATH（または環境変数 PAPER_TRADING_SQLITE_PATH）でデータベースパスを明示的に設定すると本番 DB と完全に分離できます。

セキュリティ
- .env は決してリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きを追加）。

----------
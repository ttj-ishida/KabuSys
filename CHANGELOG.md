Keep a Changelog
=================

すべての重要な変更をこのファイルに記載します。  
このプロジェクトは Keep a Changelog 準拠の様式で管理しています。

0.1.0 - 2026-04-20
-----------------

Added
- コア: パッケージ初期リリース。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 設定管理:
  - 環境変数／.env 読み込みユーティリティ（src/kabusys/config.py）を追加。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行うため、CWD に依存しない自動ロード。
    - .env と .env.local の読み込み順序をサポート（.env.local が上書き、既存 OS 環境変数は保護）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env のパースは export 形式やクォート、インラインコメント、エスケープを考慮した堅牢な実装。
  - Settings クラスを追加し、環境変数の取得・検証をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - KABUSYS_ENV / LOG_LEVEL の有効値チェック、PAPER_FILL_MODE の検証ロジックを実装。
    - paper_trading 用 DB パス PAPER_TRADING_SQLITE_PATH、pid/kill flag パス等を提供。

- 設定ヘルパー CLI:
  - .env 作成・更新ウィザード（src/kabusys/config_setup.py）を追加。
    - 対話式に環境変数を入力し .env を生成（秘密項目はマスク表示）。
    - 既存 .env の読み込みと Enter での既存値継承をサポート。
    - 保存前の確認と .env のテンプレート出力を実装。
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリチェック、config/*.yaml の存在確認（PyYAML がない場合はパースチェックをスキップ）。
    - --strict オプションで警告を失敗扱いにできる。

- 実行・監視ランナー:
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離（BrokerClientFactory により MockBrokerClient を選択する設計）。
    - 監視テーブル初期化（init_monitoring_db）と DuckDB 接続を確立。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動（Engine は別スレッドで実行）。
    - data/execution.pid と data/stop_requested.flag による PID 管理・停止フラグ処理を実装。
    - RiskManager のデフォルト設定（max_position_pct=0.20 等）を適用し、initial_portfolio_value を broker.get_available_cash() から初期化。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒、0 以下や不正値はデフォルトにフォールバックして警告を出力）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用して監視データを記録。
    - SystemMonitor の check_once() を定期実行し、例外はログに記録してループ継続。
    - 停止フラグ（data/stop_requested.flag）検知でループ停止。KeyboardInterrupt をハンドルして終了処理を行う。

- ポートフォリオ構築（pure functions、DB 非依存）:
  - portfolio_builder:
    - select_candidates: スコア降順、同点時は signal_rank でタイブレークする選定。
    - calc_equal_weights / calc_score_weights: 等配分とスコア正規化。全スコアが 0 の場合は等配分へフォールバック（警告ログ）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を満たすための候補除外ロジック。unknown セクターは除外対象外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知のレジームは 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") による発注株数決定、lot_size（単元）丸め、per-stock 上限・aggregate cap（available_cash） に応じたスケーリング、cost_buffer を考慮した保守的見積り、残余での端数分配などのアルゴリズムを実装。

- ユーティリティ:
  - ロギングセットアップ（src/kabusys/utils/logging_setup.py）を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。既存ハンドラはクリアして再設定。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
    - ログディレクトリ解決順: 引数 > 環境変数 LOG_DIR > デフォルト "logs/"。ディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみ継続。
    - StreamHandler は stdout を使用（cron 等で stdout/stderr を一本化する運用を想定）。
  - プロセス優先度ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - set_process_priority(level): Windows (psutil の priority class) と POSIX (nice 値) を吸収する実装。サポート外 OS では警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能（権限や非対応 OS では警告を出してスキップ）。

- ツール:
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite を解析し、稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等の指標を算出。
    - 合否判定ルール（デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を実装。
    - P95 計算、日付フィルタリング、テーブル欠如時のフォールバックハンドリングを実装。
    - コマンド例:
      - python -m kabusys.tools.paper_verification_report
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- リサーチ:
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加。
    - DuckDB 接続を用いて prices_daily / raw_financials を参照し、Momentum / Value / Volatility / Liquidity 系ファクターを計算する方針と定数（ウィンドウ長等）を定義。
    - 計算関数は DuckDB 接続を受け取り (date, code) ベースの dict リストを返す設計。

Changed
- 初リリースのため該当なし。

Fixed
- 初リリースのため該当なし。

Notes / migration
- 監視データベースについて:
  - run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。開発中に監視データを別 DB に分けたい場合は SQLITE_PATH を適切に設定してください。
- Paper Trading モード:
  - KABUSYS_ENV=paper_trading の場合、発注処理は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）に記録され、本番データと分離されます。
- ロギング:
  - デフォルトでログは stdout と logs/<app_name>.log（日次ローテート）に出力されます。ログファイル保存に失敗した場合はコンソールのみでの出力にフォールバックします。
- 環境変数自動読み込み:
  - 自動ロードの挙動を無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。

参照コマンド
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report

セキュリティ
- 初回リリースのため該当なし。秘密値（API トークン等）は .env に保存し、決して Git にコミットしないでください（config_setup のヘッダにも注意喚起あり）。

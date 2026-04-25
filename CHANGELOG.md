# CHANGELOG

すべての重要な変更点は Keep a Changelog の方針に従って記載しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

### [0.1.0] - 2026-04-25

Added
- 初期リリース。以下の主要機能・ユーティリティを追加。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全に分離する実装。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のデーモンスレッド起動・停止制御を実装。
    - 起動前に data/stop_requested.flag を確認して起動を抑止する仕組みを実装。
    - 実行中は停止フラグを監視して安全に engine.stop() を呼ぶループを実装。
    - 実行 PID 保持用ファイル（data/execution.pid）を利用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明示。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。
- 設定・ヘルパ
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env パースの強化: export 形式、クォートとバックスラッシュエスケープ、インラインコメントの扱いに対応。
    - Settings クラスを追加し、環境変数アクセスをメソッド化（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DB パス / PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を実装。
    - KABUSYS_ENV / LOG_LEVEL の値検証および is_live / is_paper / is_dev プロパティを追加。
    - KILL_FLAG_CLEAR_ON_START 等の監視関連設定のプロパティを提供。
  - config_setup.py
    - .env を対話式に作成・更新するウィザード CLI を追加。
    - サンプル項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE トークン等）を用意し、既存値の再利用・秘密値マスク等の UX を実装。
    - 保存時に .env の雛形を書き出す処理を実装（.env を Git 管理しない旨の注意を記載）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証）。
    - --strict オプションで警告を FAIL 扱いにするモードを追加。
    - 本番（KABUSYS_ENV=live）時のガード（LINE 通知設定未設定の警告、KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）のファイルハンドラをルートロガーに設定。
    - LOG_DIR 作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続する堅牢性を実装。
    - ログレベル解決順（引数 > 環境変数 > デフォルト）をサポート。
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX(Linux/macOS/FreeBSD) の違いを吸収する実装。
    - アクセス権や未対応 OS の場合に警告を出して安全にフォールバック。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - calc_score_weights は全銘柄スコアが 0 の場合に等配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。
    - unknown セクターはセクター上限適用外とする挙動を採用。
    - レジームマップ（bull/neutral/bear）と未知レジームのフォールバック（警告）を実装。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジックを実装。
    - lot_size（単元）で丸め、単銘柄上限・投下合計（aggregate cap）に対するスケーリングと残差の分配アルゴリズムを実装。
    - cost_buffer を用いた保守的コスト見積もりをサポート。
- 研究・分析 & ツール
  - research/factor_research.py（ファクター計算モジュール）
    - DuckDB の prices_daily / raw_financials テーブルを用い、Momentum / Value / Volatility / Liquidity などのファクター計算を行う基盤を追加（設計・定数・インターフェース実装）。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）等を SQLite の各テーブルから集計し、PASS/FAIL 判定（閾値はソース内で定義）を出力。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数を優先的に使用。

Changed
- プロジェクトの設定読み込みポリシーを明確化
  - .env 自動読み込みをプロジェクトルート探索ベースに変更（CWD 依存から解放）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- ログ出力先
  - logging_setup により全起動スクリプトが統一されたログ出力形式・ファイル名（logs/<app_name>.log）を利用するように推奨。
- 起動時のプロセス優先度
  - run_execution、run_monitoring は起動直後に set_process_priority("high") を呼ぶようにし、重要プロセスの優先度を上げる挙動を導入。

Fixed
- 設定パースの堅牢化
  - .env のクォート内バックスラッシュエスケープやインラインコメントの扱いなど、以前の簡易パーサで起きる誤解釈を修正（config._parse_env_line を改善）。

Security
- .env の扱いに関する注意
  - config_setup が生成する .env に対して「絶対に Git にコミットしないこと」を明記。

Notes / Breaking Changes / 注意点
- run_monitoring は KABUSYS_ENV の値に関わらず production 用 sqlite_path（Settings.sqlite_path）を使用する仕様です。監視データが本番 DB に書き込まれるため、テスト環境で監視を動かす場合は sqlite_path を明示的に差し替えてください。
- PAPER_FILL_MODE に無効な値を設定すると Settings.paper_fill_mode が ValueError を送出します。設定値は instant | partial | never | reject のいずれかを使用してください。
- .env 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストやパッケージ配布後の動作制御用）。
- logging_setup はデフォルトで logs/ ディレクトリを作成しファイル出力を行いますが、ディレクトリ作成に失敗した場合はコンソール出力のみで継続します。ログディレクトリを変更する場合は LOG_DIR 環境変数または setup_logging の引数を使用してください。
- process_priority は psutil を使用し、実行環境により権限不足や未対応 OS の場合は設定をスキップして警告を出します。

Other
- パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- tests は含まれていません（初期実装）。将来的にユニットテストを追加予定。

--- 

今後の予定（例）
- research/factor_research の完全実装（SQL クエリ・正規化処理の完成）。
- ExecutionEngine / SystemMonitor の単体テスト追加と E2E テスト基盤整備。
- 銘柄ごとの lot_size マスタ対応、手数料・スリッページモデルの拡張。
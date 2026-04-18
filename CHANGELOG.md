Changelog
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。
このプロジェクトはセマンティック バージョニングに従います。

Unreleased
----------

- （現時点の作業中の変更はここに記載）

[0.1.0] - 2026-04-18
--------------------

Added
- 基本パッケージ初版を追加（バージョン: 0.1.0）。
  - src/kabusys/__init__.py に __version__ を定義。

- 実行・監視プロセス起動スクリプトを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行（デーモンスレッド）。
    - data/execution.pid を PID ファイルとして使用。data/stop_requested.flag による停止監視を実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下等）はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path（デフォルト: data/monitoring.db）を使用して監視テーブルを初期化。
    - stop_requested.flag によるループ終了、KeyboardInterrupt 対応。

- 環境変数 / 設定管理機能を追加。
  - src/kabusys/config.py
    - .env ファイルの自動読み込み（.env → .env.local、OS 環境変数を保護）。
    - .git または pyproject.toml を起点にプロジェクトルートを自動検出（CWD 非依存）。
    - 複雑な .env パーサ実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルール対応）。
    - Settings クラスに各種プロパティを提供（J-Quants、kabu API、DB パス、PID/Kill flag、閾値や環境判定など）。バリデーションとデフォルト値を実装。
    - PAPER_FILL_MODE の有効値チェック、PAPER_TRADING_SQLITE_PATH 等の提供。

- 設定関連 CLI を追加。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 秘匿項目のマスク表示、選択肢・デフォルト提示、キャンセル時の安全挙動、.env のテンプレート書き出しを実装。
    - .env に書き込む際のヘッダ（Git にコミットしない旨の注意）を追加。
  - src/kabusys/validate_config.py
    - 起動前に環境変数・config/*.yaml の妥当性を検証する CLI。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリチェック、YAML ファイルの存在とパース検証（PyYAML がある場合）。
    - --strict オプションで警告も失敗扱いにできるモードを提供。
    - 本番環境（live）用の追加ガード（LINE 通知設定や Kill Switch の確認）を実装。

- ユーティリティを追加。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity 設定を行うユーティリティ。
    - Windows と POSIX（Linux/macOS/FreeBSD）に差分対応し、権限不足や未対応環境では警告を出してスキップ。
    - run_monitoring / run_execution 起動時に set_process_priority("high") を呼び出すようにした。

- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ計算のみ）。
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を返す（タイブレークに signal_rank を利用）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア正規化配分（全スコアが 0 の場合は等配分にフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別の既存エクスポージャ超過時に新規候補を除外。unknown セクターは除外しないなどの挙動を明記。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告とともに 1.0 フォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき株数を算出。単元株（lot_size）丸め、max_per_stock、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）考慮、残余処理における安定した優先付けロジックを実装。

- 研究用ファクター計算モジュールを追加（DuckDB ベース）。
  - src/kabusys/research/factor_research.py
    - calc_momentum, calc_volatility 等の関数を用意。prices_daily / raw_financials テーブルのみを参照してモメンタム（1/3/6M、MA200乖離）、ボラティリティ（ATR20）、流動性指標などを計算。
    - ウィンドウサイズや欠損データの扱い（行数不足時は None）を明記。

- Paper Trading 検証レポートツールを追加。
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポートを生成。
    - 日付フィルタ (--from / --to)、--db オプション対応。閾値（稼働率 99%、成功率 90% 等）を定義して PASS/FAIL 判定を行う。
    - P95 計算、NULL 値・テーブル未存在時のフォールバックを考慮。

- 監視 DB 初期化ユーティリティ呼び出しを整備。
  - run_* スクリプト内で init_monitoring_db(sqlite_conn) を呼び、監視用テーブルが存在することを冪等に保証。

Changed
- .env 読み込みのデフォルト優先順位を明確化。
  - OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。

Security
- config_setup に .env 書き出し時の注意ヘッダを追加（.env を絶対に Git にコミットしない旨の明記）。

Notes / Implementation details
- stop/kill フラグのファイルパスは data/stop_requested.flag / data/kill.flag 等を使用。設定は Settings で上書き可能。
- process_priority は権限不足や未対応 OS 時に安全にスキップし、ログで通知する設計。
- Paper Trading と本番 DB の明確な分離を設計上重視（発注処理の誤接続防止）。
- 多くの関数は副作用を持たない純粋関数として実装され、テストや解析に適した設計になっている。

Acknowledgements
- 初版の API や計算ロジックは設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）に準拠して実装されています（ソース内コメント参照）。
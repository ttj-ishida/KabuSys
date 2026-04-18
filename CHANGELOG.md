Changelog
=========

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-04-18
------------------

初回リリース。

Added
- 基本パッケージ情報
  - パッケージバージョンを追加: kabusys.__version__ = "0.1.0"。

- 実行用エントリスクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。環境に応じて本番・ペーパートレード用 DB を切り替え。
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient を利用し、data/paper_trading.db（または環境変数で指定）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag を検出するとエンジンを停止する仕組みを実装。execution.pid に PID を保存する仕組みあり（Engine 側で利用）。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てる処理を追加。
    - RiskManager にデフォルトのリスクパラメータを設定（max_position_pct, max_utilization, rate_limit_per_sec, など）。初期ポートフォリオ値は broker.get_available_cash() から取得。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番の sqlite_path を使用して監視データを記録。
    - 起動時にプロセス優先度を "high" に設定し、data/stop_requested.flag でループ停止。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。

- 環境設定・管理
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml から検出し .env, .env.local をロード）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを抑止可能。
    - 強力な .env パーサ実装（export 構文、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等をサポート）。
    - Settings クラスを実装し、各種設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE など）をプロパティで取得。
    - PAPER_FILL_MODE の検証（有効値: "instant","partial","never","reject"）と paper_sqlite_path の分離をサポート。
    - 環境種別（development/paper_trading/live）やログレベルの検証メソッドを提供。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）をサポート。
    - シークレット項目は表示をマスク、既存 .env の読み込みと Enter による既存値継承、保存確認を実装。
    - .env 書き込み時に注意文を付与（.env をコミットしない旨）。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml の妥当性を検証する CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認と（PyYAML が利用可能なら）パース検証を実装。
    - 本番環境（KABUSYS_ENV=live）向けの追加警告（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定等）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ロジック（純粋関数）
  - portfolio.portfolio_builder
    - 候補選定（select_candidates）: スコア降順、同点は signal_rank でタイブレーク。
    - 等金額配分（calc_equal_weights）。
    - スコア加重配分（calc_score_weights）: 全銘柄スコアが 0 の場合は等分配にフォールバックし警告を出力。

  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）: 既存保有比率が閾値を超えるセクターの新規候補除外ロジック。sell_codes を考慮して当日売却予定銘柄を除外可能。
    - レジーム乗数（calc_regime_multiplier）: "bull","neutral","bear" に応じた乗数を返す（未知のレジームは 1.0 でフォールバックし警告）。

  - portfolio.position_sizing
    - position size 計算（calc_position_sizes）: allocation_method ("risk_based","equal","score") をサポート。
    - risk_based: risk_pct と stop_loss_pct に基づく株数計算。
    - 上限管理: per-stock 上限（max_position_pct）と aggregate 上限（available_cash）を適用。
    - lot_size（例: 100 株）単位で丸め、コストバッファ（手数料・スリッページ）を考慮したスケーリングと残余配分の実装。
    - 価格欠損時のスキップとログ出力。

- 監視・モニタリング関連
  - monitoring_db の初期化呼び出し（init_monitoring_db）を run_monitoring と run_execution の起動時に行い、冪等に監視テーブルを保証。

- ユーティリティ
  - utils.process_priority
    - プロセス優先度設定ユーティリティを追加（set_process_priority）。
    - Windows と POSIX 系（Linux, Darwin, FreeBSD）を抽象化して対応。失敗時は警告を出してスキップ。
    - CPU affinity 固定関数 set_cpu_affinity を追加（最初の N コアにプロセスをピン留め）。

- 研究・ファクタ計算
  - research.factor_research
    - DuckDB を用いたファクター計算モジュールを追加（calc_momentum, calc_volatility 等）。
    - モメンタム（1M/3M/6M リターン、MA200乖離）、ATR ベースのボラティリティ、出来高・出来高比率などを計算。
    - DuckDB の SQL とウィンドウ関数を活用し、データ不足時の None ハンドリングを実装。

- ツール
  - tools.paper_verification_report.py
    - ペーパートレード結果用の検証レポート生成スクリプトを追加。
    - system_status, trade_logs, risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポート出力。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）し Pass/Fail 判定を行う。
    - 日付フィルタ（--from / --to）と --db オプションによる DB 指定をサポート。

Changed
- ドキュメント・ログ出力の充実
  - 各モジュールに説明ドクストリングを追加し、挙動と設計意図を明示。
  - run_* スクリプトで起動環境情報とポーリング間隔などを INFO ログで出力。

Fixed
- N/A（初回リリースのため既存バグ修正は無し、ただし各所で堅牢性を考慮した例外処理 / 存在チェックが追加されている）

Notes / 注意事項
- .env ファイル内の機密情報は絶対に Git 等の VCS にコミットしないでください（config_setup にも注意喚起あり）。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化できます（テスト時に便利）。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能ですが、1 未満や不正値はデフォルト 60 秒にフォールバックします。
- run_execution/run_monitoring は起動時に高優先度へ設定しようとしますが、OS 権限やプラットフォームにより設定に失敗する場合があります（その場合はログに警告が出ます）。
- Paper Trading と Live のデータは明確に分離する設計になっています。paper_trading 用 DB を使用するには KABUSYS_ENV を適切に設定してください。

Security
- 環境変数・シークレットの取り扱いに注意。config_setup ではシークレットをマスク表示するが、保存先のファイル権限管理は利用者側で行ってください。

Acknowledgements
- 本リリースはシステムの初期基盤（設定管理、起動スクリプト、ポートフォリオ構築ロジック、監視、検証ツール、研究用ファクタ計算）を提供します。今後のリリースで機能拡張・安定化を予定しています。
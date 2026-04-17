# Changelog

すべての日付はコミット／リリース日を示します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-17
初回公開リリース。

### Added
- コアランタイム / 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はリポジトリ直下の data/stop_requested.flag によるフラグ検知で行う。
    - 監視用 DB は環境に依らず本番の sqlite_path を使用して初期化（init_monitoring_db）。
    - duckdb 接続を併用。
    - 予期しない例外時はログ出力してループを継続。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db デフォルト）を用いて本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine を別スレッドで起動し、stop flag により安全停止。
    - PID ファイルの取り扱い（data/execution.pid を利用）。

- 設定管理・検証・ウィザード
  - config.py
    - Settings クラスを追加。環境変数経由で設定を提供。
    - .env と .env.local の自動読み込み（プロジェクトルートが検出できる場合）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 環境変数のパースが堅牢化（クォート、エスケープ、コメント処理など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や paper_sqlite_path、各種閾値設定など多数プロパティを提供。
  - config_setup.py
    - 対話式 .env 作成 / 更新ウィザードを追加。
    - 秘匿項目は表示をマスクし、デフォルト・既存値の再利用をサポート。
    - .env 書き込みテンプレートを用意（.env を絶対に Git にコミットしない旨の注意を含む）。
  - validate_config.py
    - 起動前チェック CLI を追加。必須環境変数・KABUSYS_ENV の妥当性・パス存在・config/*.yaml の存在・本番環境向けガード等を確認。
    - --strict で警告を失敗扱いにできる。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出力。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソート/切り取り。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア全0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有時価を考慮）、"unknown" セクターは制限除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知はフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate 上限、cost_buffer による保守的見積り、available_cash に対するスケールダウン処理を実装。
    - ログ出力により価格欠損などをデバッグ可能に。

- 研究／ファクター計算
  - research.factor_research
    - DuckDB を用いたファクター計算モジュールを追加（momentum, volatility 等）。
    - prices_daily / raw_financials テーブルのみを参照する純粋計算ロジック。
    - 各種ウィンドウサイズやスキャン日数は定数として定義。
    - P95 等の統計計算・欠測値（None）取り扱いに対応。

- ツール
  - tools.paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計。
    - 閾値に基づいて PASS/FAIL を判定。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能。

- ユーティリティ
  - utils.process_priority
    - プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, macOS 等）差分を吸収し、psutil を用いて優先度設定（nice / HIGH_PRIORITY_CLASS 等）。
    - 権限不足や未対応プラットフォームでは警告を出して安全にフォールバック。
    - set_cpu_affinity(cpu_count) により最初の N コアにプロセスを固定可能（例外時は警告）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- .env の自動生成テンプレートおよび README に対して「.env を絶対に Git にコミットしない」注意を挿入（config_setup に記載）。

### Notes / Implementation details
- run_monitoring は KABUSYS_ENV の値に関係なく監視用の sqlite_path（production path 想定）を使用する設計になっています。監視 DB の分離運用が必要な場合は設定で sqlite_path を切り替えてください。
- run_execution は paper_trading モード時に paper_sqlite_path（data/paper_trading.db がデフォルト）を使用し、本番 DB とログ・注文データを分離します。
- Settings は OS 環境変数を保護するため、.env の読み込み時に既存 OS 環境変数を上書きしない仕組み（.env.local は override）を採用しています。
- position_sizing の aggregate スケールダウンは lot_size（単元）に基づく丸め処理を行い、残差分は fractional remainder の順位で追加配分することで再現性を高めています。
- factor_research の SQL は DuckDB 上でのウィンドウ関数と集約に依存しており、prices_daily テーブルのスキーマ・データ品質に依存します。データ不足時は None を返す仕様です。

---

この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、各項目を実際のコミットや設計書（PortfolioConstruction.md, StrategyModel.md など）に基づいて調整します。
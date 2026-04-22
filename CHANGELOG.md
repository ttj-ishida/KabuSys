# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
主なバージョンは semantic versioning に準拠します。

なお、ここに記載した内容はソースコードから推測して作成しています。

## [0.1.0] - 2026-04-22

### Added
- 全体
  - 初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを追加。
  - duckdb / sqlite を用いたデータ基盤との統合を実装（設定でパスを変更可能）。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ開始スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止はプロジェクト直下の data/stop_requested.flag によるファイルフラグで制御。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを組み立て、ExecutionEngine を別スレッドで実行。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応。

- 設定関連
  - config.py: 環境変数 / .env 管理モジュールを追加。
    - .env の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - エクスポート形式（export KEY=val）、クォート付き値、エスケープ、インラインコメントの取り扱いに対応するパーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応。
    - Settings クラスを実装し、各種設定値（パス、閾値、環境判定など）をプロパティ経由で提供。入力値の検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 複数の設定項目を対話入力可能。既存 .env の読み込み、最後に .env を書き出し。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パースチェック、live 用の追加ガードなどを実行。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御
  - utils/logging_setup.py: ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一ログ設定。
    - LOG_DIR / LOG_LEVEL の環境変数や引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - set_process_priority("high"|"normal"|"low") で Windows / POSIX の差分を吸収して優先度設定。
    - set_cpu_affinity(n) で最初の n コアにプロセスを固定（権限不足等はログ警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選択（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（全スコア = 0 の場合は等配分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づく候補フィルタリング（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を提供（bull/neutral/bear とフォールバック）。未知レジームは警告して 1.0 を返す。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。
    - 単元株（lot_size）で丸め、1銘柄上限、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ考慮）を考慮した分配ロジックを実装。

- リサーチ
  - research/factor_research.py（未完の箇所あり）: DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム等の計算を想定）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 向けの検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などのテーブルから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出。
    - デフォルト閾値（稼働率 99% 等）を定義し、PASS/FAIL 判定を出力。
    - --from / --to / --db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数を参照。

- その他
  - パッケージ初期化ファイルに __version__="0.1.0" を追加。

### Changed
- run_monitoring.py / run_execution.py
  - 起動時に set_process_priority("high") を呼び出すようにして、重要プロセスの優先度を高める（起動直後に実行）。
  - DB 初期化関数 init_monitoring_db を起動フロー内で呼び出し、監視テーブルの存在を保証（冪等）。

- logging_setup
  - stdout を利用することで、cron / タスクスケジューラ実行時のリダイレクト運用を想定。

### Fixed
- config._parse_env_line / _load_env_file
  - .env パーサを堅牢化。export プレフィックス、クォート（エスケープ対応）、インラインコメントの処理を改善。
  - .env の読み込みでファイルアクセスエラー時に警告を出すように変更。

- position_sizing.calc_position_sizes
  - aggregate cap により総コストが available_cash を超える場合にスケールダウンし、端数配分ロジックで残余キャッシュを再配分する実装を追加（reproducible な順序付け含む）。

### Security
- .env 生成ウィザードでシークレット項目は出力時に伏せ字表示（マスク）するなど、取り扱いに配慮。

---

今後の予定（例）
- research/factor_research.py のモメンタム計算の完成と単体テスト追加。
- ExecutionEngine / Broker クライアントの e2e テストとペーパートレードのシミュレーション強化。
- 設定検証・ウィザードの日本語英語対応や CI 連携。

もし特定ファイルや機能の変更点をより詳しく記載する必要があれば、対象を指定してください。
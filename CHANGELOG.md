# Changelog

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）準拠で記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期実装を追加（パブリック API: kabusys）。
  - バージョン情報を src/kabusys/__init__.py に `__version__ = "0.1.0"` として定義。

- 実行・監視用エントリポイントを追加。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全に分離して動作。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御用に data/stop_requested.flag と data/execution.pid を利用。停止フラグを検知すると安全に Engine を停止。
    - RiskConfig のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 等）を組み込み。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や非整数）の場合はデフォルトにフォールバックし警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を参照して監視テーブルを初期化。
    - 停止フラグファイル（data/stop_requested.flag）を監視し、検知時にループを終了。

- 環境設定管理・自動読み込みと検証ツールを追加。
  - config.py
    - .env ファイルおよび環境変数から設定を読み込むユーティリティ。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づき .env/.env.local を自動ロード（OS 環境変数が優先）。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env の行パーサは export プレフィックス、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメントの扱いをサポート。
    - Settings クラスで各種設定をプロパティとして提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、しきい値等）。
    - KABUSYS_ENV の有効値チェック、LOG_LEVEL の検証、PAPER_FILL_MODE の有効値制限等のバリデーションを実装。

  - config_setup.py
    - 対話式ウィザードにより .env の初期作成／更新を支援する CLI。
    - J-Quants / kabuステーション / DuckDB / SQLite / LINE / ログレベル / Kill Switch 設定など主要項目を対話で入力可能。
    - 既存 .env の読み込み、秘密値のマスク表示、保存前の確認表示を実装。
    - .env の出力テンプレートを生成（Git へのコミットを避ける旨の注記を含む）。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml の整合性をチェックする CLI。
    - 必須環境変数の未設定チェック、プレースホルダ値チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DUCKDB/SQLITE パスの親ディレクトリ存在確認、config/*.yaml の存在チェックと（PyYAML があれば）パースチェック、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告を FAIL 扱い（exit 1）にする機能を追加。
    - 結果の INFO / WARNING / ERROR を標準出力に整形して出力。

- プロセス制御ユーティリティを追加。
  - utils/process_priority.py
    - Windows と POSIX 系を吸収したプロセス優先度設定ユーティリティ（set_process_priority）。
    - CPU affinity を設定する set_cpu_affinity を提供（使用コア数を指定して最初の N コアにピン留め）。
    - 権限不足や非対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築関連の純粋関数群を追加（DB非依存、メモリ内計算）。
  - portfolio/portfolio_builder.py
    - BUY シグナルから候補選定（score 降順、同点は signal_rank でタイブレーク）。
    - 等重配分（calc_equal_weights）とスコア加重配分（calc_score_weights）を実装。全スコアが 0 の場合は等重にフォールバックして警告。

  - portfolio/risk_adjustment.py
    - セクター集中上限適用（apply_sector_cap）：既存保有のセクター別時価を計算し、max_sector_pct を超えるセクターの候補銘柄を除外（"unknown" セクターは適用除外）。
    - レジーム乗数（calc_regime_multiplier）：regime に応じて投下資金の乗数を返す（bull=1.0 / neutral=0.7 / bear=0.3、未知レジームは警告して 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - allocation_method に基づく株数計算を実装（"risk_based", "equal", "score"）。
    - risk_based: リスク許容率（risk_pct）と損切り率（stop_loss_pct）から理論株数を算出し単元株（lot_size）に丸める。
    - equal/score: 各銘柄の重みと portfolio_value・max_utilization から配分を計算。
    - per-stock 上限（max_position_pct）、aggregate cap（available_cash）を考慮し、コストバッファ（cost_buffer）で保守的に見積もる。
    - aggregate cap 超過時はスケーリングし、端数は lot_size 単位で残差（fractional）に基づいて順次割当てるロジックを実装。

  - portfolio/__init__.py をエクスポート用に追加。

- 研究・因子計算モジュールを追加（DuckDB を用いた時系列計算）。
  - research/factor_research.py
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比）等の計算関数を実装。
    - DuckDB 接続を受け取り prices_daily テーブルから SQL ウィンドウ関数で効率的に計算。
    - データ不足時の None ハンドリングやスキャン範囲（MA200 のバッファなど）を考慮している。

- Paper Trading 向け検証レポート生成ツールを追加。
  - tools/paper_verification_report.py
    - paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を解析してレポートを標準出力に生成。
    - 指標: 稼働率 (uptime %)、注文成功率 (fill_rate %)、送信率 (send_rate %)、P95 レイテンシ（ms）、リスク却下数 等。
    - デフォルトの合格基準（しきい値）を定義（稼働率 >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 <= 200ms）。
    - --from / --to / --db の CLI オプションをサポート。
    - データ欠損に対する安全なフォールバック（テーブル未存在時の例外吸収）を実装。

- 監視 DB 初期化ユーティリティ呼び出しを各起動スクリプトに追加（monitoring_db.init_monitoring_db を使い監視テーブルの存在を保証）。

### Changed
- .env 自動読み込みの優先順を明確化（OS 環境変数 > .env.local > .env）。既存 OS 環境変数は保護され上書きされない。
- 設定検証とウィザードを導入することで、起動前に設定不備が検出しやすくなった。

### Fixed
- MONITOR_POLL_INTERVAL に不正な値が与えられた場合に time.sleep に渡して例外になることを防ぐため、0 以下または非整数はデフォルト値へフォールバックするよう改善（警告ログ出力）。

### Security
- .env ファイル生成テンプレートに「.env を絶対に Git にコミットしないこと」を明記し、CLI ウィザードで秘密情報をマスクして表示することで秘匿情報取り扱いの注意を促進。

### Notes / Implementation details
- run_execution/run_monitoring は起動時にプロセス優先度を上げる（set_process_priority("high")）処理を最初に行うため、OS 権限に依存して失敗する場合はログに警告を残しスキップする動作となる。
- portfolio の純粋関数群は DB 非依存でテストしやすく設計されている（副作用なし）。
- research/factor_research の SQL 部分は DuckDB のウィンドウ関数を多用しており、大規模データに対して効率的に集計可能。
- validate_config は PyYAML 未導入時に YAML 検証をスキップして警告を出すが、可能なら PyYAML をインストールして config/*.yaml の構文チェックを行うことを推奨。

---

今後の改善候補（未実装/検討中）
- position_sizing: 銘柄ごとの lot_size をマスタから読み込めるよう拡張（現在は全銘柄共通の lot_size）。
- risk_adjustment: price 欠損時のフォールバック（前日終値や取得原価など）を導入してエクスポージャー評価精度を改善。
- research/factor_research: 他ファクター（Value, Liquidity 等）の実装拡充とユニットテストの整備。
- エンドツーエンドの統合テスト（paper_trading を使ったシナリオテスト）を追加。
# Changelog

すべての重要な変更点を文書化します。フォーマットは「Keep a Changelog」に準拠します。←（このファイルはコードベースから推測して生成しています）

注: リリース日やバージョンはソース内の __version__ や現在日付に基づいて記載しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-17

Added
- プロジェクト初期実装を追加。
- 起動スクリプト / CLI:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止制御にプロジェクト内 data/stop_requested.flag を使用。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用（分離された）SQLite（data/paper_trading.db を想定）と MockBroker を利用する挙動をサポート。
    - 停止フラグ（data/stop_requested.flag）検知および PID ファイル管理（data/execution.pid）。
  - validate_config.py
    - .env および config/*.yaml 等の起動前検証ツールを追加（--strict オプションあり）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、ファイル/ディレクトリ存在チェック、PyYAML があれば YAML パース検証も行う。
  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを追加。シークレット項目はマスク表示。
    - 生成される .env に関する注意（Git へコミットしない等）を含むテンプレート出力機能を持つ。

- 設定管理:
  - kabusys.config.Settings クラスを導入。
    - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 多数のプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE 検証ロジックを含む。
    - settings = Settings() のインスタンスをモジュールレベルで提供。

- 監視・実行周辺ユーティリティ:
  - monitoring.monitoring_db.init_monitoring_db（起動時に監視用テーブルを冪等に初期化する想定で使用）。
  - utils.process_priority
    - プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux/Mac/FreeBSD) 間の差分吸収、psutil による実装。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供し、権限不足や未対応環境では警告を出して安全にスキップする。

- ポートフォリオ構築関連（純粋関数群: DB を参照しない設計）:
  - portfolio.portfolio_builder
    - select_candidates: スコア降順ソートと tie-break（signal_rank）を実装。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分。スコアが全て 0 の場合に等配分へフォールバックして WARNING を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存ポジションのセクター比率が閾値を超える場合、新規候補を除外）。"unknown" セクターは制限を適用しない。
    - calc_regime_multiplier: 市場レジーム（bull / neutral / bear）に応じた投下資金乗数を返す。未知のレジームは警告とともに 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算、lot_size（単元株）丸め、単銘柄上限／総投下上限（aggregate cap）とスケーリング・端数配分アルゴリズム（fractional remainder による再配分）を実装。
    - 手数料/スリッページ考慮の cost_buffer、max_position_pct / max_utilization / risk_pct / stop_loss_pct 等のパラメータをサポート。

- リサーチ / ファクター計算:
  - research.factor_research
    - DuckDB を使ったファクター計算モジュールを追加。prices_daily / raw_financials を想定して計算を行う設計。
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20）、流動性指標等の計算関数を実装（calc_momentum, calc_volatility 等）。
    - 計算範囲やウィンドウ期間の定数を定義（200日 MA, ATR20 など）。結果は (date, code) キーの dict リストで返す。

- ツール:
  - tools.paper_verification_report
    - ペーパートレード用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から各種指標を集計して検証レポートを生成するコマンドラインツールを追加。
    - 集計指標: 稼働率(uptime_pct)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ、リスク却下数等。
    - デフォルト閾値（例: 稼働率 >= 99.0%、fill_rate >= 90%、P95 <= 200ms）および PASS/FAIL 判定を実装。
    - 日付フィルタ（--from, --to）と --db オプションをサポート。DB が存在しない場合はエラーメッセージを出力。

- パッケージメタデータ:
  - kabusys.__version__ = "0.1.0"
  - kabusys.__all__ に主要サブパッケージを追加（data, strategy, execution, monitoring）。

Changed
- なし（初回リリース想定）

Fixed
- .env 読み込み関連:
  - config._parse_env_line にて export KEY=val 形式、クォート（シングル/ダブル）内のエスケープ処理、インラインコメントの扱い、クォートなし時の '#' のコメント判定などを丁寧に処理するロジックを実装。これにより .env の柔軟な記述を許容。
  - .env 読み込み時に存在しないプロジェクトルートを検出した場合は自動読み込みをスキップする安全策を追加。
  - .env の読み書き（config_setup）で既存の値再利用、秘密値のマスク表示、Cancel 処理のハンドリングなどを改善。

Security
- .env の生成時に「.env は絶対に Git にコミットしないこと」を明示。シークレット入力はウィザードでマスク表示。

Notes / Implementation details / Behavior
- run_monitoring と run_execution は双方とも起動直後に set_process_priority("high") を呼び、プロセス優先度を上げようとする（権限不足時は警告でスキップ）。
- run_execution は broker の生成を BrokerClientFactory に委譲し、paper_trading 環境では本番 DB と完全に分離された専用 SQLite を使用する。
- monitoring 用 DB 初期化（init_monitoring_db）は冪等で呼べることを前提としている（存在確認・テーブル作成）。
- position_sizing の aggregate cap では lot_size 単位で丸め、端数は fractional remainder の大きい順に追加配分することで再現性のあるスケーリングを行う。
- research.factor_research は DuckDB を利用して SQL ウィンドウ関数で移動平均やラグを計算する設計。データ不足時は None を返すことで上流でのフィルタリングが可能。

Removed
- なし

Deprecated
- なし

Security
- なし（既知の脆弱性はソースからは検出できず）

――
開発者注: 上記は提供されたコードベースからの推測による CHANGELOG です。実際のリリースノートとして公開する場合は、実際の変更履歴やコミットログをもとに微調整してください。
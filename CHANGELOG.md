# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

- リリースノートは主にコードベースからの推測に基づいて作成しています。
- 省略・推測が含まれる点はご了承ください。

## [0.1.0] - 2026-04-19

### Added
- 全体
  - プロジェクト初版リリース相当の機能群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を設定可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルの存在で検知。
    - 監視用 DB は環境に関係なく Settings.sqlite_path（本番相当）を使用。
    - SQLite と DuckDB の接続確立、監視 DB 初期化を行う。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）と MockBroker を使用して本番 DB と分離。
    - プロセス優先度を高優先（high）に設定。
    - 停止フラグの検知で実行エンジンを安全に停止。
    - 実行エンジンの PID を data/execution.pid に保持（設定により上書き可）。

- 設定周り
  - config.py: 環境変数 / .env 読み込みと Settings クラスを実装。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により .env 自動読み込み（.env, .env.local の優先度）をサポート。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサは `export KEY=val`、クォートやエスケープ、インラインコメント等に対応する堅牢な実装。
    - 必須チェックを行う `_require()` と Settings の各種プロパティ（J-Quants / kabu API / DB パス / PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の値検証（"instant"|"partial"|"never"|"reject"）。
    - 環境種別チェック（KABUSYS_ENV: development/paper_trading/live）やログレベルの検証を実装。
    - paper_sqlite_path 等の paper_trading 用の分離設定を提供。

  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE トークン等）を案内して .env を生成。
    - シークレット項目は入力時にマスク表示、既存値の有効活用、保存前の確認プロンプトを実装。
    - 生成された .env はコミットしないよう注意書きを出力。

  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数未設定やプレースホルダ値、KABUSYS_ENV/LOG_LEVEL の不正値を検出してエラー/警告を出力。
    - DUCKDB/SQLITE のディレクトリ存在チェック、config/*.yaml の存在および PyYAML があればパース検証を実行。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: ロギングの統一セットアップを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を使ったファイル出力を設定（デフォルト logs/<app_name>.log、30 日保持）。
    - 既存ハンドラをクリアしてから再設定することで二重登録を防止。
    - LOG_DIR/LOG_LEVEL の環境変数や引数からの上書きをサポート。ログディレクトリ作成失敗時はファイル出力を無効化して継続。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows（psutil の priority class）と POSIX（nice 値）の差分を吸収して単一 API を提供。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を実装。権限不足や未対応プラットフォーム時は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選出（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック（max_sector_pct）により新規候補を除外。既存保有・当日売却候補の扱い、"unknown" セクターは上限適用しない等の挙動を明示。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull:1.0 / neutral:0.7 / bear:0.3）、未知レジームは 1.0 にフォールバック（警告出力）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・ポートフォリオ値・利用可能現金等から買付株数を計算。
      - allocation_method: "risk_based"（リスクベース）, "equal", "score" をサポート。
      - risk_based: 損切り幅・リスク率から目標株数計算。全方式で単元株（lot_size）に丸め。
      - 単銘柄上限（max_position_pct）、総投下上限（max_utilization）を考慮。
      - cost_buffer による保守的コスト見積を受け入れ、aggregate cap 超過時はスケールダウンを行い、残差配分を lot 単位で再配分するロジックを実装。
      - 価格欠損時はスキップして安全に動作。

- 解析 / 研究ツール
  - research/factor_research.py（ファクター計算モジュールの骨格を追加）
    - Momentum, Value, Volatility, Liquidity といったファクター群設計と、DuckDB 接続を受ける方針を実装（モメンタム計算の骨組み開始）。
    - 日数定数、ウィンドウ定義、関数インターフェース等を含む（実装は続きあり／未完の可能性あり）。

- ユーティリティ・ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - CLI で期間指定（--from/--to）や DB パス指定（--db）を受け取る。
    - システム安定性（稼働率）、注文成功率（fill/send）、リスク却下数、API レイテンシ（avg/max/P95）等を集計・表示。
    - P95 計算、閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）による PASS/FAIL 判定を実装。
    - 参照テーブルが存在しない場合も例外をハンドリングして graceful に動作。

### Changed
- （新規リリースのため該当なし：初期追加が中心）

### Fixed
- （新規リリースのため該当なし）

### Security
- （なし）

注:
- 一部モジュール（例: execution/*.py の詳細な実装、monitoring.system_monitor 等）はこの差分に含まれていないため、動作はそれらの実装に依存します。
- research/factor_research.py はファイル末尾が途中で切れているため、モメンタム計算の完全実装は別途続きが必要です。
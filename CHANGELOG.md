# Keep a Changelog

すべての重要な変更点をここに記録します。フォーマットは Keep a Changelog に準拠します。

データモデル / API の互換性に関する重要な変更は、各リリースの注記に明記します。

## [0.1.0] - 2026-04-18

### Added
- 基本的な日本株自動売買フレームワーク「KabuSys」初期実装を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の MockBrokerClient を使用し、Paper Trading 用 DB（デフォルト: data/paper_trading.db）を利用して本番 DB と完全分離する挙動を実装。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
    - 停止制御のためのファイルフラグ（data/stop_requested.flag、data/execution.pid）に対応。
    - ExecutionEngine をデーモンスレッドで実行し、停止フラグ検知で安全停止を行うループを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログを出してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番用 `sqlite_path` を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py: 環境変数 / .env ファイル読み込み・ラッパー実装。
    - .env 自動ロード（優先順位: OS 環境 > .env.local > .env）。プロジェクトルートは `.git` または `pyproject.toml` を探索して決定。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。
    - 複数の設定プロパティを提供（J-Quants・kabu API トークン、DB パス、Paper Trading 用 DB、PID / Kill Flag パス、監視閾値、環境種別判定など）。
    - `paper_fill_mode` のバリデーション（"instant" / "partial" / "never" / "reject"）や `KABUSYS_ENV` の有効値チェックを実装。
    - `settings = Settings()` により容易に利用可能。

- 設定ユーティリティ CLI
  - config_setup.py: 対話式ウィザードで `.env` を生成・更新するツールを追加。
    - 対話的プロンプト、既存 .env の読み込みと表示、シークレット値のマスク表示、保存確認付き。
    - デフォルト値と選択肢を用意（例: KABUSYS_ENV, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）。
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML があれば実施）。
    - `--strict` オプションで警告を FAIL 扱いにする機能。
    - 本番 (KABUSYS_ENV=live) 向けの追加ガード（LINE 通知設定の未設定、KILL_FLAG_CLEAR_ON_START の危険設定等を警告）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定 `select_candidates`（スコア降順、signal_rank でタイブレーク）。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（スコア全 0 の場合はフォールバックで等金額配分）。
  - portfolio/risk_adjustment.py:
    - セクター集中対策 `apply_sector_cap`（既存保有のセクター比率が閾値を超える場合、新規候補を除外。unknown セクターは除外対象外）。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull"→1.0, "neutral"→0.7, "bear"→0.3。未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py:
    - 発注株数算出 `calc_position_sizes` 実装。
      - allocation_method に応じた算出 ("risk_based", "equal", "score")。
      - lot_size（単元株）を考慮した丸め、1 銘柄上限・aggregate cap（available_cash）チェックとスケールダウン。
      - cost_buffer を用いた保守的コスト見積り、スケールダウン時に残差を用いた再配分ロジックを実装。
  - portfolio パッケージのエクスポートを整備。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を使用）と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - LOG_DIR 環境変数や引数でログディレクトリを指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
  - utils/process_priority.py:
    - プロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して簡易 API を提供（set_process_priority, set_cpu_affinity）。
    - 権限不足などで設定できない場合は警告を出して続行。

- 監視 / モニタリング基盤
  - monitoring パッケージ用の DB 初期化呼び出し点を実装（init_monitoring_db を run スクリプトから呼び出し）。
  - SystemMonitor の単発チェック呼び出し（monitor.check_once）をポーリングで実行。例外はログに出して次のポーリングに継続。

- Paper Trading 向けレポートツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成ツールを追加。
    - 入力: PAPER_TRADING_SQLITE_PATH（または --db）、期間フィルタ（--from, --to）。
    - 指標:
      - 稼働率 (uptime_pct) の集計、総ポーリング数、エラー数
      - 注文成功率 (fill_rate)、送信率 (send_rate)、Created/Sent/Filled カウント
      - リスク却下数（risk_logs）
      - API レイテンシ（avg/max/P95）
    - Pass/Fail 判定の閾値を定義（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 latency <=200ms）。P95 は内製のパーセンタイル計算実装を使用。
    - DB テーブルが存在しない場合でも安全に N/A を返すフェイルセーフ。

- research/factor_research.py
  - ファクター計算モジュールの骨子を追加（モメンタム、MA200 乖離、ATR、出来高系等を想定）。
  - DuckDB を用いた prices_daily / raw_financials 参照ベースの計算設計（関数は DuckDB 接続を受け取り純粋関数として結果を返す方針）。
  - （注）ファイルは途中までの実装（calc_momentum などの実装枠組みを含む）。

### Changed
- N/A（初回リリースのため無し）

### Fixed
- N/A（初回リリースのため無し）

### Security
- 機密情報（API トークン等）は `.env` に保持し、config_setup の生成ファイルに「.env を Git にコミットしない」ことを明記。
- 本番環境 (KABUSYS_ENV=live) の設定検証で通知設定や Kill Switch の危険な設定を警告するガードを追加。

### Notes / Implementation details（補足）
- デフォルトの DB/ログパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
- ログ設定は起動スクリプトから `setup_logging(app_name=...)` を呼び出すことで統一される。
- Execution / Monitoring は停止フラグ（data/stop_requested.flag）により外部から安全に停止可能。
- 設定検証ツールは CI/デプロイ前チェック用途で想定。`--strict` により警告をエラー扱いにできる。

---

今後の予定（例）:
- research/factor_research の完全実装（ファクター計算ロジックの完成）。
- Strategy / Execution の追加実装および単体テスト、統合テストの拡充。
- 単体テスト用のモック/フィクスチャ整備と CI パイプライン統合。

---
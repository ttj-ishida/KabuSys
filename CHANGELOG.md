# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
注: 以下は提出されたコードベースの内容から推測して作成した変更履歴です（実際のコミット履歴ではありません）。

## [Unreleased]

- (なし)

---

## [0.1.0] - 2026-04-19
初回リリース。システム全体の実行スクリプト、設定管理、ユーティリティ、ポートフォリオ構築、検証ツールなどの基本機能を実装。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として設定。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準に探索）。
  - .env 自動ロード機能を実装（優先順位: OS環境 > .env.local > .env）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

- 設定管理
  - Settings クラスを提供し、環境変数から設定値を取得する統一インターフェースを実装。
  - 必須・任意の設定項目、環境判定（development / paper_trading / live）、各種既定値（例: `DUCKDB_PATH`, `SQLITE_PATH`）を定義。
  - `PAPER_FILL_MODE` の検証（有効値: instant/partial/never/reject）を実装。
  - Paper Trading 用 DB パス (`PAPER_TRADING_SQLITE_PATH`) や PID/kill flag 関連の設定を提供。

- 実行スクリプト
  - run_execution.py を実装:
    - プロセス優先度を高（"high"）に設定して起動。
    - 環境に応じて本番 DB と Paper Trading 用 DB を分離（`settings.is_paper` 判定）。
    - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）および PID ファイルの取り扱いを実装。
    - RiskManager のデフォルト設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。

  - run_monitoring.py を実装:
    - プロセス優先度を高に設定して起動。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用（設計上の意図）。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` により上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止フラグ検出によるループ中断、例外発生時のロギング、SQLite / DuckDB 接続のクローズ処理を実装。

- 設定関連 CLI / ツール
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。既存値の再利用、シークレットマスキング、保存確認を実装。
  - validate_config.py: 起動前に .env および config/*.yaml の検証を行う CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや YAML の存在/パース検査、`--strict` フラグを実装。

- ロギング・ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次回転、30日保持）を設定する `setup_logging()` を実装。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - 既存ハンドラのクリア処理を行い二重設定を防止。

- プロセス優先度・CPU 固定ユーティリティ
  - utils/process_priority.py:
    - Windows / POSIX (Linux, Darwin, FreeBSD) を透過的に扱う `set_process_priority(level)` を実装（"high"/"normal"/"low"）。
    - `set_cpu_affinity(cpu_count)` を実装（指定が None の場合は何もしない）。psutil 利用によるアクセス権限失敗時の警告処理を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定 select_candidates（スコア降順、tie-breaker: signal_rank）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバック、警告ログ出力）。

  - portfolio/risk_adjustment.py:
    - 同一セクターの上限チェック apply_sector_cap（既存保有の時価を計算し、上限超過セクターの候補を除外）。
    - レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear に対応、未知値は警告して 1.0 にフォールバック）。

  - portfolio/position_sizing.py:
    - ポジションサイズ計算 calc_position_sizes を実装:
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に応じたスケーリングと残余配分ロジックを実装。
      - cost_buffer による保守的なコスト見積りをサポート。

- 研究用モジュール（骨格）
  - research/factor_research.py:
    - Momentum 等のファクター計算方針と定数を実装（期間定義、スキャン範囲等）。DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計。モメンタム計算関数のスケルトンを実装（実装途中の箇所あり）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の SQLite データ（デフォルト: data/paper_trading.db）を解析して検証レポートを生成する CLI を実装。
    - 指標: 稼働率、Orders (Created/Filled/Sent) による成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出。
    - 判定閾値を定義（例: uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms）し、PASS/FAIL を出力。
    - 日付フィルタ (--from / --to)、DB パス (--db) をサポート。

### Changed
- (初回リリースのため過去の変更はなし。内部実装上の設計決定を記載)
  - Monitoring コンポーネントは環境に依存せず本番用の監視 DB を使用する設計になっている（意図的な分離）。

### Fixed
- (該当なし)

### Security
- (該当なし)

---

注記（実装上の注意）
- .env のパースはシングル/ダブルクォート内のエスケープやインラインコメントの扱いに配慮しており、柔軟な形式に対応しています。
- psutil による優先度/affinity 設定は権限不足や未対応環境で例外を握りつぶし、警告ログを出してスキップします。
- Paper Trading は本番 DB と完全分離されるよう設計されています（`settings.is_paper` による DB 切替、および MockBroker の利用を想定）。
- research/factor_research.py など一部モジュールは計算ロジックの骨格があるものの、完全実装は進行中の可能性があります。

もし特定のコミット単位の変更履歴やリリースノートを希望される場合は、コミットログやタグ情報を提供してください。提供頂ければより正確な CHANGELOG を生成します。
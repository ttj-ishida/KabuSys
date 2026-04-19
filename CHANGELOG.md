# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

なお、本ファイルの内容はリポジトリ内のソースコードから機能・振る舞いを推測して記載しています。

## [0.1.0] - 2026-04-19

### Added
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine 起動ロジックを実装。プロセス優先度を High に設定して実行。
    - KABUSYS_ENV が `paper_trading` の場合は Mock ブローカクライアントを使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に完全に分離して記録する挙動をサポート。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）による起動・停止制御を導入。
    - DuckDB を利用して分析用データベース（デフォルト: data/kabusys.duckdb）と接続。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境に依らず本番の sqlite_path を使う設計（監視 DB は常に production path を参照）。

- 設定・環境管理
  - config.py
    - Settings クラスで環境変数をラップ。必須変数の検査（_require）や各種パス・フラグ・閾値（CPU/MEM/DISK）をプロパティで提供。
    - 自動 .env 読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path、pid/kill flag 等の設定を提供。
    - KABUSYS_ENV の有効値検査（development / paper_trading / live）とログレベル検証を実装。

  - config_setup.py
    - 対話式ウィザードで .env ファイルの初期作成・更新を支援。
    - 入力項目一覧（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を定義。
    - 既存 .env の読み込み・編集、保存をサポート（保存時に注意文を挿入）。

  - validate_config.py
    - 起動前に環境変数と config/*.yaml を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在検査、YAML ファイルの存在確認と（PyYAML があれば）パース検証、live 環境向けの警告チェックを実装。
    - --strict オプションで警告をエラー扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを実装。root ロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / app_name 引数に基づく柔軟な解決ロジック。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラを安全にクローズしてから再設定することで二重出力を防止。

  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定するユーティリティを実装（Windows と POSIX の差分吸収）。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count: Optional[int]) を提供。アクセス拒否や未対応環境は警告してスキップ。

- Portfolio 構築関連（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank 昇順でタイブレークして上位 N を選出。
    - calc_equal_weights: 等金額配分を実装（N が 0 の場合は {}）。
    - calc_score_weights: スコア比例配分を実装。全銘柄スコアが 0 の場合は等金額配分にフォールバックして警告。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別の既存保有比率が閾値（max_sector_pct）を超える場合、新規候補を除外するロジック。unknown セクターは除外対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）を返す。未知レジームは警告して 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算を実装。
    - lot_size 単位で丸め、per-position 上限（max_position_pct）・aggregate cap（available_cash）・cost_buffer（スリッページ・手数料見積）を考慮したスケーリングロジックを実装。
    - risk_based モードでのベース算出（portfolio_value * risk_pct / (price * stop_loss_pct)）を実装。
    - aggregate 超過時はスケーリングし、余剰キャッシュで fractional remainder 順に lot 単位で追加配分する補正を実装。

- 分析・リサーチ
  - research/factor_research.py（未完の開始実装あり）
    - DuckDB 接続を受け、prices_daily/raw_financials を参照してモメンタム・ボラティリティ・バリュー等のファクターを計算する方針と定数を定義。
    - モメンタム（日次窓、MA200 乖離等）計算用の定数と calc_momentum の骨組みを用意（実装途中）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からレポートを作成する CLI を追加。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計し、閾値に基づいて PASS/FAIL 判定を行う。
    - デフォルト閾値: 稼働率 >= 99.0%、成立率 >= 90.0%、送信率 >= 95.0%、P95 <= 200 ms。
    - 日付フィルタ（--from, --to）と DB パスオーバーライド（--db）をサポート。

- パッケージ情報
  - __init__.py にてパッケージバージョンを "0.1.0" として定義。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

----------

注記:
- 本 CHANGELOG はソースコードからの推測に基づいて作成しています。挙動の詳細や運用上の注意（例: 本番 DB を誤って上書きしないための設定確認等）は実際の運用前に validate_config や config_setup を使って必ず確認してください。
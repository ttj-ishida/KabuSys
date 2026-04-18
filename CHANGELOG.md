# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルは、コードベース（バージョン 0.1.0）から推測できる主要な追加・仕様を記載しています。

全般注記
- 初回リリース相当のまとめ（ライブラリ / 実行スクリプト群、設定管理、ユーティリティ、ポートフォリオ構築ロジック、検証ツールなどを提供）。
- パッケージバージョン: 0.1.0
- 日付: 2026-04-18

## [0.1.0] - 2026-04-18

### Added
- エントリ / 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に記録することで本番 DB と完全分離。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知時のグレースフル停止、実行用 PID 保存（data/execution.pid）。
    - ExecutionEngine の組み立てに必要な OrderRepository / OrderManager / RiskManager / Reconciler 等の依存注入を実装。
    - RiskManager のデフォルト設定（max_position_pct / max_utilization / rate_limit_per_sec / circuit_breaker_errors 等）と初期ポートフォリオ値に broker.get_available_cash() を使用。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。不正値入力時はデフォルトにフォールバックして警告を出力。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず常に本番 sqlite_path を使用する（監視用 DB の一貫性を担保）。
    - 停止フラグ（data/stop_requested.flag）検知で監視ループを終了。
    - プロセス優先度を起動時に "high" に設定。

- 設定管理 / CLI
  - config.py: 環境変数 / .env 読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づき .env/.env.local を自動ロード（OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env のパースは引用符やエスケープ、export プレフィックス、インラインコメントなどに対応する堅牢な実装。
    - 設定プロパティを明確に分離（J-Quants, kabu API, LINE, DB パス, 監視閾値, システム設定 等）。
    - PAPER_FILL_MODE（paper trading の約定挙動）を追加。許容値: "instant" | "partial" | "never" | "reject"。無効値は ValueError。
    - paper_sqlite_path（Paper Trading 専用 SQLite パス）、pid_file_path、kill_flag_path、各種閾値（CPU/MEM/DISK）等を提供。
    - env / log_level の値検証（許容値外は ValueError）。

  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装。
    - 各項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE など）を対話的に入力し .env に保存。
    - 秘密情報はマスク表示、既存 .env の読み込みと再利用をサポート。

  - validate_config.py: 設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パス（親ディレクトリ存在）チェック、config/*.yaml の存在・パース検証（PyYAML が利用可能な場合）。
    - KABUSYS_ENV=live 向けの追加警告（LINE 設定や KILL_FLAG_CLEAR_ON_START に関する注意）。
    - --strict オプションで警告を FAIL として扱う（exit code 1）。

- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR /引数で上書き可能。ログディレクトリ作成失敗時はファイル出力を無効化して警告。
    - 既存ハンドラをクリアして二重設定を防止。

  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows (psutil の priority class) と POSIX (nice 値) を吸収して簡易 API を提供: set_process_priority("high"|"normal"|"low")。
    - set_cpu_affinity(n) で最初の N コアに固定可能。アクセス権限不足等は警告してスキップ。

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレークで signal_rank を利用して候補選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重の重み計算（スコア合計が 0 の場合は等分配にフォールバックし WARNING）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 同一セクターの既存保有比率が閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: マーケットレジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す。未知のレジームは 1.0 でフォールバックし警告。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づいた発注株数計算を実装。
      - lot_size（単元）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウン処理。
      - cost_buffer を考慮した保守的見積り、スケーリング後の端数（fractional）を lot 単位で再配分するアルゴリズムを実装。
      - 価格欠損時の挙動（価格がない銘柄はスキップ）についてのログ出力。

  - portfolio/__init__.py によるエクスポートを提供（select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier）。

- 監視・検証ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）を指定して SQLite を走査し、稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）などを集計してレポート出力。
    - P95 計算、しきい値による PASS/FAIL 判定を実装（デフォルト基準: uptime >= 99.0%, fill_rate >= 90.0%, send_rate >= 95.0%, P95 latency <= 200 ms）。
    - 日付フィルタ (--from/--to) による期間指定に対応。

- research/factor_research.py
  - ファクター計算モジュールの骨組みを追加（momentum, MA200, ATR, volume 等を想定）。DuckDB を利用して prices_daily / raw_financials を参照する設計。momentum 計算の実装開始（ファイル末尾が途中で切れているため実装は未完の可能性あり）。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし。ただし設計上の挙動・既定値は上記を参照）

### Fixed
- （初回リリースのため該当なし）

### Notes / Behavior & Defaults
- DB 関連既定パス
  - DuckDB: data/kabusys.duckdb
  - 監視用 SQLite (monitoring): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）
- ログ
  - デフォルトは logs/ 以下に app_name.log を日次ローテーションで保存。コンソール出力は stdout（stderr ではない）。
- 環境変数読み込み
  - OS 環境変数 > .env.local > .env の優先順で読み込む。既存 OS 環境変数は保護（.env で上書きされない）。.env.local は override=True（ただし OS 環境変数は保護）。
- Kill / Stop フラグ
  - run_execution/run_monitoring はプロジェクトルート配下 data/stop_requested.flag を監視してグレースフルに停止する設計。
  - kill フラグ関連の挙動は設定によりカスタマイズ可能（KILL_FLAG_CLEAR_ON_START 等）。

### Known / TODO (推測)
- research/factor_research.py の実装が途中で切れている（ファイル末尾に未完のコード断片あり）。完全なファクター計算ロジックの追加が必要。
- position_sizing の price 欠損時に別のフォールバック価格（前日終値や取得原価）を使う改善がコメントで示唆されている。
- 将来的に単元（lot_size）を銘柄別に持たせる拡張が想定されている（stocks マスタの導入）。

---

今後のリリースでは、research モジュールの完成、ExecutionEngine/Monitoring の実動作検証に基づくバグ修正やパフォーマンス改善、テストの追加等が想定されます。必要であれば、各項目についてより詳細な変更説明や影響範囲（例: 環境変数の一覧と意味）を追記します。
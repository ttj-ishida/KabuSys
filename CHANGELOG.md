CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 — 2026-04-25
------------------

Added
- パッケージ初期リリース。
- 基本設定/起動スクリプト
  - run_execution.py: 実行エンジン (ExecutionEngine) 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用し、MockBrokerClient を使って本番 DB と分離して動作する想定。
    - 起動時にプロセス優先度を "high" に設定するフローを追加。
    - 停止制御: data/stop_requested.flag を検知して安全に停止する仕組みを実装。実行中は PID ファイル (data/execution.pid) を管理。
  - run_monitoring.py: システム監視 (SystemMonitor) ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視用 DB は環境にかかわらず本番用 sqlite_path を使用して初期化。
    - 停止フラグ (data/stop_requested.flag) による停止動作を実装。
- 設定管理
  - config.py: 環境変数 / .env の読み込みと Settings クラスを実装。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読込順序: OS 環境変数 > .env.local > .env。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パースの堅牢化: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱い等に対応。
    - Settings による型付けされたアクセサ（duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode など）を提供。環境名やログレベルなどのバリデーションを行う。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env ウィザードを追加。既存 .env を読み込んで更新可能。出力は .env（Git にコミットしない旨を明記）。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、DB パス/ディレクトリの存在チェック、config/*.yaml の存在および PyYAML があればパース検証、KABUSYS_ENV=live 時の追加警告など。
    - --strict モードで警告を FAIL 扱いにできる。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を使用）、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。ログディレクトリが作れない場合はファイル出力をスキップして stdout のみで継続。
    - LOG_LEVEL / LOG_DIR / 引数での上書き対応。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度 & CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収。権限がない場合は警告を出してスキップ。
    - set_process_priority(level)、set_cpu_affinity(cpu_count) を提供。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコアソートと上位選抜。
    - calc_equal_weights, calc_score_weights: 等分配・スコア比率配分。全スコアが 0 の場合は等分配にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有の時価を計算して上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算、単元株（lot_size）丸め、per-stock 上限・aggregate キャップ（available_cash）に対するスケーリング、cost_buffer を用いた保守見積り、端数処理の再配分ロジックを実装。
  - portfolio/__init__.py で主要関数をエクスポート。
- 研究用ファクターモジュール（初期実装）
  - research/factor_research.py: DuckDB 接続を受け取り Momentum 等のファクター計算を行うモジュールを追加（モジュール設計、定数、calc_momentum の冒頭実装を追加。※ファイル末尾は一部省略）。
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を参照。
    - 期間指定 (--from / --to)、--db オプションに対応。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ などを算出して PASS/FAIL 判定を行う。閾値はソースに定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
- パッケージメタ
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （該当なし）

Notes / 環境変数まとめ（主なもの）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。Settings でバリデーション。
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須。
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）。
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）。monitoring は環境にかかわらず本番 sqlite_path を使用。
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）。
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）。不正値は例外。
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。デフォルト 60。1 未満や非整数は警告でデフォルトにフォールバック。
- LOG_LEVEL / LOG_DIR: ロギングの制御。
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（値が設定されていると無効化）。
- KILL_FLAG_CLEAR_ON_START: 起動時の Kill Flag 自動クリア制御（設定値 "1" は有効）。

既知の制限・今後の改善
- research/factor_research.py の実装は一部（ファクター計算ロジック）で未完部分があり、継続実装が必要。
- position_sizing の lot_size は全銘柄共通で固定。将来的に銘柄別単元を持たせる拡張を検討中（TODO コメントあり）。
- apply_sector_cap 内で price が欠損 (0.0) の場合、エクスポージャーが過少評価される可能性あり。フォールバック価格（前日終値等）導入を検討。
- ファイル入出力や権限に依存する処理（ログディレクトリ作成、プロセス優先度設定等）は権限不足時にフォールバックする実装だが、運用手順での確認を推奨。

今後の予定（案）
- factor_research の完備とユニットテスト追加
- ExecutionEngine / Broker クライアント周りの統合テスト、order/reconciler/risk manager のテストカバレッジ強化
- CI の導入、パッケージ配布（wheel）およびドキュメント整備

----

補足: この CHANGELOG はリポジトリ内の現在のコードから推測して作成しています。実際のリリースノートとして使用する場合は、マージ済みのコミットメッセージや開発者の追加情報を元に調整してください。
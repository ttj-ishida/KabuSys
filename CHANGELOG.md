Keep a Changelog 準拠 — CHANGELOG.md

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

Unreleased
=========

（現在のコードベースは初回公開相当の機能群を含むため、次のリリースノートは初期リリースとしてまとめられています。）

0.1.0 - 2026-04-19
------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレーディング用 SQLite を使用（data/paper_trading.db をデフォルト）。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組立てと実行ループを実装。
    - 停止管理: data/stop_requested.flag の検出で安全に停止。実行用 pid ファイル (data/execution.pid) を扱う。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視プロセスはプロダクション用 sqlite_path を常に使用（環境に依存せず監視DBを統一）。
    - 停止フラグの検出でループ終了。
- 設定・環境管理
  - config.py: 環境変数・設定読み込みモジュールを追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により .env の自動読み込みを行う（無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env 読み込みのパーサーは export プレフィックス・クォート・インラインコメント等に対処。
    - Settings クラスでアプリ設定をプロパティとして提供（例: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, 各種閾値, env/log_level 判定、paper_fill_mode のバリデーション等）。
- 設定ユーティリティ
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン等）を対話的に作成・更新し .env を書き出す。
    - 既存 .env の読み込み・既存値の再利用をサポート。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けの安全ガードチェック等を実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング
  - utils/logging_setup.py: 共通ロギングセットアップを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせてルートロガーを設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップしてコンソールのみ）。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）。
    - 日次ローテーションで 30 日分を保持。
- プロセス制御ユーティリティ
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供（high/normal/low）。
    - set_cpu_affinity(cpu_count) により最初の N コアへピンニング可能（権限がない場合は警告でスキップ）。
    - 呼び出し元スクリプト（run_execution/run_monitoring）で起動時に優先度を high に設定するよう利用。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコアソートと上位選定。
    - calc_equal_weights, calc_score_weights: 等分／スコア重み付け配分（スコア合計が 0 の際は等分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限の判定と候補除外（unknown セクターは適用外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知は警告で 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出、単元（lot_size）丸め、per-stock 上限・aggregate cap によるスケーリング、cost_buffer を使った保守的見積り、スケーリング時の端数配分ロジック等を実装。
- 研究・分析ユーティリティ（骨格）
  - research/factor_research.py: ファクター計算モジュールの導入（Momentum 等の計算方針を実装）。
    - DuckDB を受け取り prices_daily / raw_financials を元に各種ファクターを計算する設計（関数は純粋関数で DB 参照は限定）。
    - （実装途中の箇所あり）
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg, max, P95）等を集計。
    - Pass/Fail の閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200ms）を定義し、判定レポートを標準出力で出力。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数からの既定解決あり。
- DB 関連
  - DuckDB と SQLite の両方を利用する設計を採用（duckdb は分析、sqlite は監視/注文履歴等）。
  - init_monitoring_db による監視テーブルの存在保証（冪等）を実装。

Changed
- 初回リリースのため該当なし（新規追加のみ）。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 該当なし。

Notes / マイグレーション・運用上の注意
- 環境変数読み込み:
  - 自動でプロジェクトルートの .env / .env.local を読み込みますが、テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env の生成には python -m kabusys.config_setup を推奨。
- 起動・監視:
  - 監視プロセスは MONITOR_POLL_INTERVAL 環境変数（秒）で間隔を変更できます（不正値はデフォルト 60 秒にフォールバック）。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成することで行います（run_execution/run_monitoring ともに検出）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、実取引と完全分離された SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
  - PAPER_FILL_MODE（instant/partial/never/reject）の値検証があり、不正な値は例外を投げます。
- ログ:
  - デフォルトでは logs/ ディレクトリにアプリ名別のログを日次ローテーションで保存（30 日分保持）。LOG_DIR 環境変数で変更可能。ファイル出力に失敗してもコンソール出力は維持されます。
- 依存:
  - config の YAML 検証は PyYAML がインストールされている場合のみ実行されます（未インストール時は警告を出してスキップ）。

補足
- research/factor_research.py 等、一部モジュールは実装の続きが想定される（ファクター計算の詳細実装やテスト追加など）。
- 今後のリリースではテストカバレッジ、例外ハンドリングの強化、ログやメトリクスの更なる充実、Strategy/Execution コンポーネントの詳細な実装・検証結果に基づく改善を予定しています。
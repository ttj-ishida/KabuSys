CHANGELOG
=========

すべての重要な変更点をここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
  - Unreleased: 現在の開発中の変更
  - 各リリース: 日付とカテゴリ別の要約（Added / Changed / Fixed / Deprecated / Removed / Security）

Unreleased
----------
（なし）

[0.1.0] - 2026-04-24
--------------------

Added
- 初期リリースを追加（バージョン 0.1.0）。
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用し、本番 DB と完全に分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成を導入し、paper/live/dev での挙動を分離。
    - ExecutionEngine を別スレッドでデーモンとして起動し、data/stop_requested.flag の存在を監視して安全に停止。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
    - 実行用 PID ファイル対応（data/execution.pid）。
- 監視エントリスクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ file による安全停止対応（data/stop_requested.flag）。
    - 起動時にプロセス優先度を "high" に設定。
- 設定・環境管理
  - config.py
    - Settings クラスを導入し、環境変数からアプリケーション設定を取得するインタフェースを提供。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む（OS 環境変数を保護して上書き制御）。
    - .env のパース機能を堅牢化（export プレフィックス、クォート、エスケープ、インラインコメント対応など）。
    - PAPER_FILL_MODE（instant/partial/never/reject）など Paper Trading 特有の設定や、DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH など多数のプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - シークレット項目はマスク表示、デフォルト / 既存値の利用、保存前確認などの UX を提供。
  - validate_config.py
    - 起動前に環境変数および config/*.yaml の存在と簡易パースを検証する CLI を追加。
    - --strict モード（警告も失敗扱い）をサポート。
    - 本番向けの追加チェック（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の注意喚起等）。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定。ログディレクトリは LOG_DIR 環境変数で指定可能（デフォルト: logs/）。
    - 既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（nice / priority class）を設定するユーティリティを追加。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート/上位選抜。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み算出（全スコアが 0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェックと候補除外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株丸め、per-stock/aggregate のキャップ処理、コストバッファを考慮したスケールダウンロジック等を実装。
  - portfolio/__init__.py
    - 上述関数群をパブリック API としてエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB を読み取り、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計してレポートを出力。
    - デフォルトの閾値（稼働率 99%、成立率 90% など）を定義し、PASS/FAIL を判定。
    - コマンドライン引数で期間（--from/--to）や DB パス（--db）を指定可能。
- 研究用ファクター計算（開始実装）
  - research/factor_research.py
    - Momentum/Value/Volatility/Liquidity などを計算するモジュールの骨子を追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。モジュール一部（calc_momentum 等）実装の途上。

Changed
- パッケージメタデータ
  - __init__.py にてバージョンを "0.1.0" に設定。

Security
- なし

Deprecated
- なし

Removed
- なし

Fixed
- なし

Notes / 実装上の留意点
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テストなどで利用）。
- run_monitoring と run_execution はそれぞれ data ディレクトリ下のフラグファイル（stop_requested.flag）を参照して停止を判断します。運用時はこれらのファイル管理に注意してください。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を無効化して stdout のみで継続します。
- process_priority の設定は OS と権限に依存し、失敗した場合は警告を出してスキップします。

今後の予定（例）
- research/factor_research の完全実装（全ファクター計算とテスト）。
- ExecutionEngine / RiskManager 周りのユニットテスト拡充とドキュメント整備。
- 銘柄別単元株情報の追加（lot_size の銘柄別対応）。
- 監視系のアラート（LINE 通知）との統合テスト。

以上。
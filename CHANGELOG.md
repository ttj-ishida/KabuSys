CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
-------------------

Added
- 初回リリースとして基本機能を追加。
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動するエントリポイントを提供。
      - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite DB (data/paper_trading.db) を使用して本番 DB と分離。
      - 起動時に process priority を "high" に設定（utils.process_priority）。
      - 停止制御: プロジェクト内 data/stop_requested.flag を検知して安全に停止する仕組みを実装。
      - 実行中の PID を data/execution.pid に保存するための pid_file 連携。
    - run_monitoring.py
      - SystemMonitor のポーリングループを起動するエントリポイントを提供。
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値はログで警告しデフォルトにフォールバック。
      - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを管理。
      - 停止フラグ (data/stop_requested.flag) 検知でループ停止。
  - 設定管理
    - config.py
      - 環境変数・.env 読み込みロジックを実装。
      - プロジェクトルート自動検出（.git または pyproject.toml を探索）により .env 自動ロード（.env/.env.local、OS 環境変数保護あり）。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - .env の行パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの取り扱いに対応。
      - Settings クラスを提供し、アプリから安全に設定値を参照可能（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DBパス、paper_trading 用パス、各種しきい値やフラグなど）。
      - 環境名（KABUSYS_ENV）の有効値検査、LOG_LEVEL の検査、PAPER_FILL_MODE の検証等を実装。
  - 設定検証・セットアップツール
    - validate_config.py
      - .env と config/*.yaml の不備を起動前に検出する CLI を提供。
      - 必須環境変数のチェック、KABUSYS_ENV のガード、DB パスや YAML の存在/パース検査、live 環境時の追加警告などを実行。
      - --strict オプションで警告を FAIL 扱いにできる。
    - config_setup.py
      - .env を対話的に初期作成／更新するウィザード CLI を提供。
      - J-Quants、kabuAPI、DBパス、ログレベル、Kill Switch の設定など主要項目を対話で入力し .env に保存。
      - 秘匿項目はマスク表示して扱う。
  - 監視関連
    - monitoring.monitoring_db.init_monitoring_db 呼び出しを各起動スクリプトで行い、監視テーブルの存在を保証（冪等）。
    - run_monitoring/run_execution と duckdb の接続を利用（分析用 DB）。
  - ログ基盤
    - utils.logging_setup.setup_logging
      - stdout ストリームハンドラと日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。
      - LOG_DIR / LOG_LEVEL の解決順、既存ハンドラのクリア処理を実装。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - プロセス優先度 / CPU 固定
    - utils.process_priority
      - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定。
      - CPU affinity を最初の N コアに固定するユーティリティを提供。
      - psutil の権限エラー等はログ警告でフォールバック。
  - ポートフォリオ構築
    - portfolio.portfolio_builder
      - シグナルの候補選定（スコア降順、タイブレークは signal_rank）select_candidates。
      - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
    - portfolio.position_sizing
      - 複数の割当方法（risk_based / equal / score）に基づく発注株数計算 calc_position_sizes。
      - lot_size（単元）考慮、個別上限および aggregate cap（使用可能現金に収まるようスケーリング）を実装。
      - cost_buffer による保守的なコスト見積もりと残差処理での追加割当ロジックを実装。
    - portfolio.risk_adjustment
      - セクター集中上限を適用する apply_sector_cap（既存保有のセクター時価からブロックを判定）。
      - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームは警告して 1.0 にフォールバック）。
  - 解析 / レポート
    - tools.paper_verification_report.py
      - Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し検証レポートを生成する CLI を追加。
      - デフォルト DB は data/paper_trading.db。--from/--to/--db オプションをサポート。
      - 各指標に閾値を設定して PASS/FAIL 判定を行う（稼働率、成立率、送信率、P95 レイテンシ）。
  - 研究用モジュール（骨格）
    - research.factor_research
      - DuckDB 接続を受け取り prices_daily/raw_financials を用いて Momentum, Value, Volatility, Liquidity ファクターを計算する設計。
      - モメンタム計算 calc_momentum の骨格を追加（モジュールは今後完成予定）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Known issues / Notes
- research/factor_research.py の calc_momentum 関数は途中で切れている（ファイル末尾が不完全）。今後のリリースで完成させる予定。
- portfolio.risk_adjustment.apply_sector_cap は price_map に価格がない（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値などをフォールバックする改善が必要。
- process_priority の動作はプラットフォームや権限に依存し、権限不足時はログで警告してスキップする設計。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる。またテスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。

作者
- KabuSys チーム

-- END --
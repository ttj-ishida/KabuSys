CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) のフォーマットに従って記載しています。
リリース版のバージョンはパッケージ定義 (kabusys.__version__) に合わせています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初期リリースとして基本機能群を追加。
  - 実行・監視ランナー
    - run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のデーモンスレッド起動・停止制御（data/execution.pid, data/stop_requested.flag を利用）。
      - RiskManager のデフォルト設定（max_position_pct 等）を組み込み、初期ポートフォリオ値は broker.get_available_cash() を使用。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。0 以下の不正値はデフォルトへフォールバック。
      - Monitoring は環境設定にかかわらず本番 sqlite_path を使用する設計になっている（監視データは一元管理）。
  - 設定・環境管理
    - config.py
      - .env 自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml に基づく）。
      - .env/.env.local の取り込みルール（OS 環境変数を保護する protected 機構）。
      - export KEY=val 形式やクォート／エスケープ、インラインコメントの取り扱いに対応するパーサ実装。
      - Settings クラスに各種プロパティを実装（J-Quants / kabu API / DB パス / PID / Kill Switch /しきい値等）。KABUSYS_ENV のバリデーション、PAPER_FILL_MODE の検証（許容値チェック）等を含む。
    - config_setup.py
      - .env を対話式に生成・更新するウィザード CLI。項目定義・既存値の読み込み・秘匿表示・保存確認を実装。
    - validate_config.py
      - 起動前に .env と config/*.yaml の設定不備を検出する CLI。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML パースチェック（PyYAML がある場合）および本番環境向けのガード（LINE 関連設定や Kill Switch の設定など）を実装。
      - --strict オプションで警告も失敗扱いにできる。
  - ロギング・プロセスユーティリティ
    - utils/logging_setup.py
      - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を統一的に設定するユーティリティ。
      - LOG_DIR / LOG_LEVEL の解決順、既存ハンドラのクリーンアップ、ファイルハンドラ作成失敗時のフォールバック等を実装。
    - utils/process_priority.py
      - Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定を提供（psutil ベース）。権限不足などの例外は警告でスキップする安全設計。
  - ポートフォリオ構築ロジック（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定（スコア降順・タイブレーク）select_candidates。
      - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
    - portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap（既存保有を基にセクター別エクスポージャ計算、上限超過セクターの新規候補除外。unknown セクターは除外しない）。
      - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知値は 1.0 でフォールバック）。
    - portfolio/position_sizing.py
      - position sizes 計算 calc_position_sizes。allocation_method("risk_based" / "equal" / "score")をサポート。
      - 単元株（lot_size）丸め、1銘柄上限・aggregate cap のスケーリング処理、cost_buffer を使った保守的コスト見積り、残差分配ロジックを実装。
  - 研究・分析ユーティリティ
    - research/factor_research.py
      - DuckDB 接続を受けてモメンタム等のファクターを計算するモジュール（設計と定数を含む）。
      - Momentum（1M/3M/6M/MA200 乖離）、ATR、出来高指標などを計画（prices_daily / raw_financials テーブルのみ参照する設計）。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用 SQLite を集計して検証レポートを出力する CLI。
      - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計し、閾値（稼働率 99%、fill 90%、send 95%、P95 200ms）で PASS/FAIL 判定を行う。
      - --from / --to / --db オプションにより期間・DB を指定可能。
  - パッケージ初期化
    - kabusys.__init__.py にバージョン 0.1.0 を設定。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Security
- なし

Notes / 補足
- データベース接続は sqlite3（監視・paper_trading）と DuckDB（分析）を併用する設計。
- 設定の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用途を想定）。
- ファイル・ディレクトリ操作や外部ライブラリ（psutil, duckdb, PyYAML 等）の利用箇所は、例外時に警告やフォールバックを行うよう堅牢化されています。
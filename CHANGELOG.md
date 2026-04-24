CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
リリース日付はリポジトリ内の __version__ と現在の状態に基づき推定しています。

[Unreleased]
------------

（現在の差分は次回リリースにまとめられます）

[0.1.0] - 2026-04-24
-------------------

Added
-----
- 初版リリース。本リリースで導入された主要機能・モジュール:
  - 実行系 / 監視系起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動するランタイムスクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite (data/paper_trading.db) を使用し、本番 DB と完全分離。
      - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler 等を組み立ててエンジンをスレッドで実行。
      - data/execution.pid、data/stop_requested.flag によるプロセス管理（停止フラグ検知で安全停止）。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
      - 監視は環境にかかわらず本番用 sqlite_path を使用（監視テーブルの初期化を行う）。
      - 停止フラグ（data/stop_requested.flag）検知でループ終了。
  - 環境設定・検証ツール
    - config_setup.py
      - 対話式ウィザードで .env を生成/更新する CLI を追加。J-Quants / kabuステーション / DB パス / ログレベル等の項目をサポート。
      - シークレット項目は表示をマスクして対話入力。
    - validate_config.py
      - .env および config/*.yaml の基本的な妥当性検証を行う CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや YAML ファイル存在・パース検証、KABUSYS_ENV=live 時の追加ガード等を実装。
      - --strict オプションで警告を FAIL 扱いにできる。
  - 環境設定読み込み・管理
    - config.py
      - .env 自動読み込み (プロジェクトルート自動検出: .git または pyproject.toml を基準) を実装。
      - export プレフィックスやクォート、インラインコメント等に対応した .env パーサを実装。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
      - Settings クラスを提供し、各種設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SQLITE_PATH / DUCKDB_PATH、PAPER_FILL_MODE 等）およびバリデーションを行うプロパティを提供。
      - PAPER_FILL_MODE の許容値 (instant, partial, never, reject) を検証。
  - ポートフォリオ構築ライブラリ（純粋関数群、DB非依存）
    - portfolio/portfolio_builder.py
      - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
      - スコア全てが 0 の場合は等金額にフォールバックして警告を出す。
    - portfolio/risk_adjustment.py
      - セクター集中上限の適用 (apply_sector_cap) と市場レジームに応じた乗数 (calc_regime_multiplier) を追加。
      - 不明セクターは上限適用対象外（"unknown" 扱い）。
      - reg ime が未知の場合は 1.0 でフォールバックし警告を出力。
    - portfolio/position_sizing.py
      - position sizing（リスクベース/等配分/スコア配分）を実装。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケーリング、cost_buffer（手数料/スリッページ見積り）を考慮。
      - 価格欠損時のスキップやログ出力を考慮。
  - ユーティリティ
    - utils/logging_setup.py
      - ルートロガーの設定ユーティリティを追加。stdout への StreamHandler と日次ローテート (TimedRotatingFileHandler) を設定。
      - ログディレクトリ自動作成、LOG_DIR/LOG_LEVEL の解決ルール、30日分のログ保持などを実装。ファイル出力失敗時はコンソールのみで継続。
    - utils/process_priority.py
      - psutil を用いたクロスプラットフォームのプロセス優先度設定を追加（Windows / POSIX に対応）。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。権限不足などの例外は警告でスキップ。
  - 分析・検証ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite の集計から検証レポートを生成する CLI を追加。
      - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し、閾値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）で PASS/FAIL を判定。
      - --from / --to / --db オプションを提供。
  - 研究用モジュール（基本骨格を追加）
    - research/factor_research.py
      - Momentum / Value / Volatility / Liquidity などを想定したファクター計算モジュールの骨格を追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する想定。
      - モメンタム計算関数 calc_momentum の実装開始（ファイル末尾で切れているため未完の可能性あり）。

Changed
-------
- なし（初回リリースのため既存の変更は無し）。

Fixed
-----
- なし（初回リリース）。

Security
--------
- なし

Notes / Implementation details
------------------------------
- process priority, logging 等は起動スクリプト内で起動直後に設定されるよう設計されています（例: set_process_priority("high"), setup_logging(app_name=...)）。
- run_execution は ExecutionEngine を別スレッドで実行し、停止フラグ検知で engine.stop() を呼ぶことで安全に停止を試みます。スレッド join のタイムアウト処理あり。
- .env パーサは export 接頭辞・クォート内のバックスラッシュエスケープ・インラインコメントの扱いなど、実用的な .env 形式をサポートするよう設計されています。
- validate_config は PyYAML が未インストールの場合に YAML 検証をスキップして警告を出す挙動です。
- Paper Trading と Live の DB を明確に分離しており、paper_trading 用 DB パスは環境変数 PAPER_TRADING_SQLITE_PATH により上書き可能です。
- logging_setup はコンソール出力に stdout を使用する点に注意してください（cron 等で stdout/stderr をまとめて扱う運用を想定）。

その他
-----
- パッケージのバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています。
- research/factor_research.py は概念実装が入っていますが、ファイル末尾が切れているため完全実装は次版での完了が必要です。
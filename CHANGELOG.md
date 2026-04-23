CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このファイルは "Keep a Changelog" の形式に準拠しています。

Unreleased
----------

- （現時点のコードスナップショットは v0.1.0 として初期リリースにまとめられています）

v0.1.0 - 2026-04-23
-------------------

Added
- 基本リリース: KabuSys 日本株自動売買システムの初期実装を追加。
  - パッケージバージョン: __version__ = "0.1.0"

- 実行／監視エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を経由して本物のブローカ/モックを切り替え可能。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による停止検出、execution.pid に PID を出力する仕組みを採用。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（既定: 60 秒）。不正な値は既定値にフォールバックして警告。
    - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db 呼び出し）。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。KeyboardInterrupt での終了に対応。
    - duckdb（分析用）への接続も確立して利用。

- 設定・環境管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
    - .env, .env.local の読み込み順と上書きルールを実装（OS 環境変数を保護）。
    - 複数の設定プロパティを持つ Settings クラスを提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 など）。
    - PAPER_FILL_MODE のバリデーション、有効値: "instant" | "partial" | "never" | "reject"。
    - KABUSYS_ENV の有効値検証: "development" | "paper_trading" | "live"。
    - settings インスタンスをデフォルトでエクスポート。

  - config_setup.py
    - 対話式 .env ウィザードを追加。初期 .env 作成・更新を支援。
    - シークレット項目は画面上でマスク表示（保存前に確認プロンプトあり）。
    - デフォルト値や選択肢、保存時のテンプレート出力を用意。

  - validate_config.py
    - 起動前チェック CLI を追加（.env および config/*.yaml の存在・基本チェック）。
    - 必須環境変数の検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ検査、PyYAML があれば YAML のパース検証を行う。
    - --strict オプションで警告を FAIL として扱える。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有比率が閾値を超える場合に新規候補を除外）。
    - 未知セクター ("unknown") は除外対象としない挙動。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームは 1.0 にフォールバックして警告）。

  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を実装。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、合計投資上限（available_cash に対する aggregate cap）、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングロジックを実装。
    - 不足価格データ・価格 <= 0 はスキップしてログにデバッグ出力。

  - portfolio パッケージの __all__ に主要関数をエクスポート。

- ユーティリティ
  - utils/logging_setup.py
    - すべての起動スクリプトから共通利用可能なログ設定ユーティリティを実装。
    - stdout への StreamHandler（stderr ではなく stdout を使用）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - ログレベル / ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。

  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度および CPU affinity 設定ユーティリティを実装（psutil を利用）。
    - Windows / POSIX（Linux, macOS, FreeBSD など）に対応した値を設定し、権限不足や未対応 OS の場合は警告を出してスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - SQLite (PAPER_TRADING_SQLITE_PATH / --db) から以下の指標を集計:
      - 稼働率 (system_status テーブル)
      - 注文成功率・送信率 (trade_logs)
      - リスク却下数 (risk_logs)
      - レイテンシ（平均、最大、P95）
    - P95 算出ユーティリティ、期間フィルタ (--from / --to) をサポート。
    - 既定の合格基準を定義（例: 稼働率 >= 99.0%、注文成功率 >= 90% など）と PASS/FAIL 判定ロジックを搭載。

- 研究モジュール
  - research/factor_research.py
    - DuckDB の prices_daily / raw_financials を用いたファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity 等を想定）。
    - モメンタム（1M/3M/6M）、MA200 乖離、ATR（20 日）等を計算する設計。DuckDB 接続を受け取り SQL と Python の組合せで計算。

Notes / ドキュメント的情報
- 環境変数と既定値
  - KABUSYS_ENV: "development"（既定）
  - DUCKDB_PATH: data/kabusys.duckdb（既定）
  - SQLITE_PATH: data/monitoring.db（既定）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（既定、paper_trading 専用）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、既定 60）
  - PAPER_FILL_MODE: "instant"（既定）等 — 有効値を厳密に検証
  - KILL_FLAG_CLEAR_ON_START: 本番での自動クリアは危険（validate_config で警告）

- 動作上の注意
  - run_monitoring は環境に関わらず monitoring 用の sqlite_path を使用して監視データを記録します（意図的な設計）。
  - run_execution は paper_trading 環境時に別 DB を使い、本番 DB とデータ分離されます。
  - プロセス優先度変更や CPU affinity の設定は環境や権限に依存し、失敗するとログに警告を出して継続します。
  - logging_setup はログディレクトリの作成に失敗した場合、ファイル出力を切り替えずに標準出力のみで動作します。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

License
-------
（ライセンス情報は省略。実際のプロジェクトでは適切なライセンスを明記してください。）
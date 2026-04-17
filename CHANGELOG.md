# Changelog

すべての重要な変更点をこのファイルで管理します。本ドキュメントは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-04-17

Added
- 基本パッケージ初期実装を追加（バージョン 0.1.0）。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。スレッドでエンジンを実行し、停止フラグ検知で安全に停止可能。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に完全分離して記録する動作をサポート。
    - 起動直後にプロセス優先度を "high" に設定する仕組みを導入。
    - PID ファイル（data/execution.pid）管理および停止フラグ（data/stop_requested.flag）による制御を実装。
- 監視用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出しデフォルトにフォールバック。
    - 監視は実行環境に関係なく本番の sqlite_path（data/monitoring.db）を使用する設計。
    - 停止フラグ検知でループを終了し、例外はログに記録して次ポーリングへ継続。
- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルートの .env, .env.local）を導入（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - プロジェクトルート検出は .git または pyproject.toml を探索して決定。CWD に依存しない動作を実現。
    - .env のパースロジックを強化（export プレフィックス対応、シングル/ダブルクォートのエスケープ、インラインコメント処理等）。
    - Settings クラスを導入し、各種環境変数をプロパティで提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）を実装。
    - KABUSYS_ENV / LOG_LEVEL の値検証、安全な既定値の提供。
- 設定関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を扱い、既存値の再利用やシークレットのマスク表示に対応。
    - .env ファイルの書式を定義して安全に保存。
  - validate_config.py
    - .env と config/*.yaml の起動前チェックを行う CLI を提供。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML があれば実行）を実装。
    - 本番 (KABUSYS_ENV=live) 向けの追加警告（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の危険性など）を実装。
    - --strict オプションで警告も失敗扱いにできる。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB を集計して検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数など。
    - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
    - 判定閾値を定義（例: 稼働率 >= 99.0%、注文成功率 >= 90%、P95 レイテンシ <= 200 ms 等）し、PASS/FAIL を出力。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレークは signal_rank）と candidate 選択を実装。
    - 等金額配分 calc_equal_weights と スコア加重 calc_score_weights（スコア合計が 0 の場合は等金額にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有のセクター比率が上限を超える場合、新規候補を除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピング、未知レジームはログ警告の上で 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算を実装（allocation_method: risk_based / equal / score）。
    - 単元株丸め、銘柄上限（max_position_pct）、aggregate cap（available_cash に基づくスケールダウン）、コストバッファの取り扱い、残余キャッシュを用いた端数配分ロジックを提供。
    - 価格欠損時のスキップや安全弁（_max_per_stock）を考慮した実装。
- 研究用ファクター計算
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加（prices_daily / raw_financials テーブル参照）。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）とボラティリティ（ATR20、20日平均売買代金、出来高比率）を計算する関数を実装。
    - データ不足時の None 返却やスキャン期間の調整などを考慮。
- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加。Windows と POSIX の差分を吸収して set_process_priority(level) を提供（high/normal/low）。
    - CPU affinity 固定機能 set_cpu_affinity(cpu_count) を追加。
    - 権限不足や未対応環境では警告を出して安全にスキップする挙動。
- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 既知の制約・今後の拡張候補
- position_sizing の lot_size は現在全銘柄共通（デフォルト 100）。将来的に銘柄別単元対応の拡張を想定（stocks マスタの導入）。
- apply_sector_cap は sector_map に存在しない銘柄を "unknown" と扱い、上限チェックの対象外にしている。price の欠損（0.0）があるとエクスポージャーが過少評価される可能性があり、将来的にフォールバック価格導入を検討。
- .env 自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml）。パッケージ配布後の特定ケースでは明示的に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して制御可能。
- research/factor_research は DuckDB 上のテーブル構造に依存するため、データ投入・スキーマ整合性に注意。

コマンド例
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine 実行:
  - python -m kabusys.run_execution
- 監視ループ実行:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上。
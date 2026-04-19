CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載します。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（今後の変更をここに記載）

[0.1.0] - 2026-04-19
-------------------

Added
- 全体
  - パッケージ初期リリース。モジュール群を追加。
  - バージョン: 0.1.0（src/kabusys/__init__.py）
- 起動スクリプト
  - run_monitoring.py を追加
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag を検出して安全にループを終了。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用。
    - duckdb を利用した接続を確立して監視 DB 初期化を行う。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py を追加
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用（data/paper_trading.db、設定で上書き可）し Mock ブローカーを利用可能。
    - エンジンは別スレッドで実行し、停止フラグ（data/stop_requested.flag）で停止処理を行う。
    - PID ファイル管理（data/execution.pid）対応、起動前に停止フラグが立っていれば起動を中止。
    - 起動時にプロセス優先度を "high" に設定。
- 設定関連
  - config.py を追加
    - .env 自動読み込み（プロジェクトルートの .env, .env.local、OS 環境優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .git または pyproject.toml を基準にプロジェクトルートを探索（__file__ を起点に探索）。
    - 複雑な .env のパース対応（export 形式、単/二重引用符内のバックスラッシュエスケープ、インラインコメントの取り扱い等）。
    - Settings クラスを提供（各種環境変数アクセス用プロパティ、バリデーション付き）。
    - データベースパス、Paper Trading 用設定（PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH）、監視・キル関連設定（PID/KILL フラグ）をサポート。
  - config_setup.py を追加
    - 対話式ウィザードで .env の初期作成 / 更新を支援。
    - 入力のデフォルト値、選択肢、シークレットマスク表示、保存確認を実装。
    - .env の既存読み込み・上書き処理、保存テンプレートを提供。
  - validate_config.py を追加
    - .env および config/*.yaml の設定不備を起動前に検出する CLI ツール。
    - 必須環境変数チェック、KABUSYS_ENV 値検証、ログレベル検証、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証（PyYAML 有無を考慮）。
    - --strict モードで警告を失敗として扱うオプションを提供。
- utils
  - utils/logging_setup.py を追加
    - 標準出力 (stdout) 用 StreamHandler と 日次ローテートする TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ自動作成、作成失敗時はファイルハンドラをスキップして stdout のみで継続。
    - LOG_LEVEL 環境変数や引数でログレベルを解決。
  - utils/process_priority.py を追加
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応したプロセス優先度設定ユーティリティ。
    - set_process_priority(level)（"high"/"normal"/"low"）を提供。権限不足や未対応 OS 時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定する機能を追加（未指定時は変更なし）。
- portfolio（ポートフォリオ構築）
  - portfolio/portfolio_builder.py を追加
    - select_candidates: スコア降順、タイブレークに signal_rank を用いる候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（全スコアが 0 の場合は等配分にフォールバックして WARNING）。
  - portfolio/risk_adjustment.py を追加
    - apply_sector_cap: セクター集中制限実装。既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知値は 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py を追加
    - calc_position_sizes: allocation_method に応じた株数算出（"risk_based" / "equal" / "score"）。
    - 単元株丸め、1銘柄上限・aggregate cap（利用可能現金を超える場合のスケールダウン）ロジック、手数料・スリッページを見積る cost_buffer を考慮した保守的算出。
    - lot_size 固定（現状は共通 lot_size=100 を想定。将来的な拡張をコメントで記載）。
- execution / monitoring / monitoring_db
  - 実行エンジンや監視に関連するコンポーネントの接続初期化を実装（ExecutionEngine / SystemMonitor の呼び出し箇所を配置）。
  - 監視 DB 初期化関数 init_monitoring_db を呼び出すよう統一（冪等に監視テーブルを保証）。
- tools
  - tools/paper_verification_report.py を追加
    - Paper Trading の検証レポート生成ツール。
    - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数を計算し PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタリング、SQLite DB パスの引数/環境変数指定をサポート。
    - デフォルトの閾値を定義（稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200 ms）。
- research
  - research/factor_research.py を追加（ファクター計算モジュール。DuckDB 経由で prices_daily / raw_financials を参照し Momentum / Value / Volatility / Liquidity 等を算出する設計。モジュールは部分実装が含まれる。）

Changed
- N/A（初回リリースのため既存からの変更なし）

Fixed
- N/A

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / 実運用上の注意
- .env は絶対に Git にコミットしないこと（config_setup.py のテンプレートにも明記）。
- 本番環境では KABUSYS_ENV=live の設定に注意（validate_config による追加警告あり）。特に KILL_FLAG_CLEAR_ON_START を 1 にすることは危険。
- process priority / CPU affinity の変更は権限に依存するため、失敗した場合は警告を出してスキップされる設計。
- Paper Trading 用 DB は本番 DB と分離して扱われる（settings.paper_sqlite_path を使用）。

開発者向け補足
- CLI エントリポイント:
  - python -m kabusys.config_setup  : .env ウィザード
  - python -m kabusys.validate_config : 設定検証
  - python -m kabusys.tools.paper_verification_report : Paper Trading レポート
  - 実運用:
    - python -m kabusys.run_monitoring
    - python -m kabusys.run_execution

（以上）
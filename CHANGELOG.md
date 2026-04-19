# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
現在のリリース: 0.1.0 — 2026-04-19

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-19

Added
- 起動スクリプトを追加 / 整備
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や整数でない値）はデフォルトにフォールバックして警告ログを出力。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する（監視データは本番 DB を参照）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループを終了。
    - プロセス優先度を起動時に "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し本番 DB と完全に分離。
    - BrokerClient の生成を BrokerClientFactory に委譲。
    - ExecutionEngine はスレッドで実行し、停止フラグ（data/stop_requested.flag）検知で engine.stop() を呼び安全にシャットダウン。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視テーブルが存在することを保証するため init_monitoring_db を呼ぶ（冪等）。

- 設定管理・ウィザード・検証機能を追加
  - config.py
    - .env 自動ロード機能（プロジェクトルートの検出ロジック付き）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースを細かく扱うロジック（export 形式対応、クォートとエスケープ対応、インラインコメント処理など）。
    - Settings クラスを実装。環境変数の必須チェック、型変換、妥当性検証を提供（KABUSYS_ENV / LOG_LEVEL 等の許容値チェック、paper_fill_mode の検証等）。
    - 各種パス（duckdb, sqlite, paper sqlite 等）や監視閾値のデフォルトをプロパティで提供。
  - config_setup.py
    - .env 作成・更新の対話式ウィザードを実装。
    - 既存 .env 読み込み、入力補助、シークレットマスク表示、保存前確認などの UX を提供。
    - 書き込みフォーマットは分かりやすいコメント付きヘッダを含む。
  - validate_config.py
    - .env と config/*.yaml を起動前に検証する CLI を実装。
    - 必須環境変数の未設定検出、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML がある場合）を実行。
    - --strict オプションで警告を FAIL 扱いするモードを提供。
    - 本番モード（KABUSYS_ENV=live）専用の安全チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START）を追加。

- ポートフォリオ構築・リスク調整・ポジションサイズ計算モジュールを追加
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で選出。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で重み付け。全スコアが 0 の場合は等金額配分にフォールバックして警告ログを出す。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 同一セクターの既存エクスポージャが閾値を超える場合、新規候補を除外（"unknown" セクターは上限適用しない）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に基づき投下資金乗数を返す（未知レジームは警告を出し 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた株数算出を実装。
    - lot_size（単元）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash によるスケーリング）、cost_buffer を用いた保守的見積り、端数補正ロジックを含む。
    - 価格欠損や不正価格時のスキップとログ出力、現有ポジションとの差分計算を実装。

- ユーティリティを追加・改善
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定。
    - LOG_DIR の自動作成、作成失敗時のフォールバック（ファイルハンドラ無効化）をサポート。
    - 既存ハンドラのクリア処理を実装（多重設定防止）。
  - utils/process_priority.py
    - プロセス優先度と CPU affinity 設定ユーティリティを追加（Windows / POSIX の差分を吸収）。
    - psutil を用いて nice 値や Windows priority を設定。アクセス権限不足時は警告ログを出してスキップ。
    - set_cpu_affinity を実装（最初の N コアにピン留め）。
    - 無効な引数での例外・境界値チェックを実装。

- 解析・検証ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、レイテンシ指標（平均/最大/P95）を集計。
    - P95 計算、期間フィルタ（--from / --to）、DB パスの指定（環境変数または --db）をサポート。
    - デフォルトの合格基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）を実装し、PASS/FAIL 判定を出力。

- 研究モジュール（部分実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨子を追加（モメンタム / MA200 / ATR / 出来高等の計算方針と定数を定義）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（実装は一部未完）。

Changed
- パッケージメタ情報
  - src/kabusys/__init__.py にバージョンを設定: __version__ = "0.1.0"

Fixed
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Security
- （該当なし）

注記
- 監視（run_monitoring）は意図的に環境変数 KABUSYS_ENV に依存せず本番用 SQLite パスを使用します。監視データを本番 DB に記録/参照する設計上の決定です。必要に応じて運用ルールで取り扱ってください。
- .env の自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml を探索）。プロジェクト配布環境での自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
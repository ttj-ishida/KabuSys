Keep a Changelog
=================

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

ルール:
- 重大な変更、機能追加、バグ修正、ドキュメント更新などはここに記載します。
- バージョン番号はパッケージの __version__ に合わせています（現時点: 0.1.0）。

Unreleased
---------

（なし）

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アプリケーションとユーティリティの初期実装を追加。
  - パッケージバージョンを `0.1.0` として設定。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。デーモンスレッドで run_session を実行し、停止フラグ（data/stop_requested.flag）を検知すると安全に停止する。
    - PID ファイル（data/execution.pid）を使用。

  - run_monitoring.py
    - SystemMonitor をポーリングで動作させるエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値や 0 以下はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path（デフォルト: data/monitoring.db）を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）を検出してループを終了。

- 設定管理
  - config.py
    - .env の自動読み込み機構を実装（プロジェクトルートの検出: .git または pyproject.toml を起点に親ディレクトリを探索）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは `export KEY=val` 形式、クォート文字列（シングル/ダブル、バックスラッシュエスケープ対応）、行内コメントの取り扱いなどに対応。
    - Settings クラスを提供し、各設定をプロパティで取得（例: duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode, pid_file_path, kill_flag_path, 各種閾値や env/log_level 判定ロジック）。
    - 環境値の検証（有効な KABUSYS_ENV 値、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。

  - validate_config.py
    - CLI ツール: .env と config/*.yaml（system_config.yaml 等）の存在・基本検証を行うスクリプトを追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）や KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML がない場合は警告でスキップ）などを実行。
    - --strict オプションで警告を FAIL 扱いにできる。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 項目: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LINE_* 等。シークレット入力、選択肢、デフォルト表示、確認プロンプトを備える。
    - .env を安全なテンプレート形式で書き出す機能を実装（.git にコミットしない旨のヘッダ付き）。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - setup_logging(app_name, log_dir, level) を実装。標準出力（stdout）用の StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - 既存ハンドラを一旦クリアして二重設定を防止。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。ログ出力は stdout を採用。

  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - Windows/Linux(Mac) の差分を吸収。psutil を利用して nice / priority class を設定し、例外（権限不足等）は警告でスキップ。

- ポートフォリオ構築モジュール（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分。全スコアが 0.0 の場合は等金額でフォールバックし警告。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 現在ポジションのセクター別時価を計算し、1 セクターが上限（デフォルト 30%）を超えている場合はそのセクターの新規候補を除外。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に応じて投下資金乗数を返す（デフォルト map、未知値は 1.0 でフォールバックし警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じて発注株数を計算。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）でスケールダウン、手数料・スリッページ見積りを考慮する cost_buffer、price 欠損時のスキップなどを実装。
    - risk_based では risk_pct と stop_loss_pct に基づく Position sizing を行う。
    - aggregate スケールダウン時に残差の扱い（fractional remainder）で再配分するロジックあり。

- リサーチ / ファクター計算（途中実装）
  - research/factor_research.py
    - Momentum、MA200乖離、ATR、出来高等の計算を行う設計を追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する意図で実装が開始（モジュールの一部は未完／続きあり）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ などを算出。
    - 基準値（閾値）を定義し PASS/FAIL 判定を行う（デフォルト閾値: uptime>=99.0%、fill_rate>=90.0%、send_rate>=95.0%、P95<=200 ms）。
    - SQLite（PAPER_TRADING_SQLITE_PATH または --db）に接続して集計し、期間フィルタ（--from/--to）に対応。

- パッケージ __init__
  - src/kabusys/__init__.py を追加し __version__ と __all__ を定義。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数（シークレット）を .env に保存する際に README へコミットしない注意喚起を .env ヘッダに含める。

Notes / Usage
- 自動 .env 読み込みはデフォルトで有効。テスト実行等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- 実行スクリプトはそれぞれ setup_logging() と set_process_priority("high") を最初に呼び出します。ログはデフォルトで logs/<app_name>.log に出力され日次ローテーションされます。
- run_monitoring は監視用 DB（SQLITE_PATH）を環境にかかわらず利用します。一方 run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使って本番 DB と分離します。
- validate_config と config_setup を使って事前に設定を作成・検証することを推奨します。

作者
- KabuSys チーム

-----
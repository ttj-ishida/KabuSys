Keep a Changelog
================

すべての変更は https://keepachangelog.com/ja/ の慣例に従って記載しています。

フォーマット
- バージョン見出しは [バージョン] - YYYY-MM-DD の形式
- 各バージョンは主に Added / Changed / Fixed / Removed セクションで構成

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-17
-------------------

Added
- 基本パッケージとバージョン情報を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境設定読み込み・管理
  - src/kabusys/config.py
    - プロジェクトルートを .git または pyproject.toml から自動検出するロジックを実装。
    - .env/.env.local の自動読み込み（OS 環境変数を保護する機構付き）。
    - 複雑な .env 行のパースを実装（export プレフィックス、クォート／エスケープ、インラインコメントの考慮）。
    - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB / 監視閾値 / 実行環境 等の設定プロパティを提供。
    - PAPER_FILL_MODE の有効値チェックや KABUSYS_ENV / LOG_LEVEL の検証を実装。

- 対話式設定ウィザード CLI
  - src/kabusys/config_setup.py
    - .env の対話式作成・更新ウィザードを追加。主要な設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を用意。
    - 既存 .env 読み込み、シークレット値のマスキング、保存確認、ファイル出力ロジックを実装。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 起動前チェックツールを追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの存在確認、config/*.yaml の検査（PyYAML が無い場合はスキップ）などを実装。
    - --strict モード（警告を FAIL 扱い）をサポート。
    - 結果を INFO/WARNING/ERROR に分類して出力。

- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_sqlite_path（data/paper_trading.db）を使用し本番 DB と分離。
    - BrokerClientFactory からブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで起動。
    - data/stop_requested.flag による停止フラグ検知・安全停止処理を実装。
    - PID ファイル（data/execution.pid）を扱う仕組みを用意。

- 監視ループ起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値入力時はデフォルトにフォールバックして警告を出力。
    - 監視は実行環境にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）検出・例外捕捉・リソースクリーンアップを実装。

- プロセス優先度 / CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - Windows / POSIX (Linux/Mac/FreeBSD) を吸収するクロスプラットフォーム実装。psutil を利用。
    - 権限不足や未対応プラットフォーム時は警告を出して安全にフォールバック。

- ポートフォリオ構築関連モジュール（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（タイブレークロジック含む）。
    - calc_equal_weights / calc_score_weights: 等価配分およびスコア加重配分（スコア合計 0 の場合のフォールバックを実装）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存ポジションと当日売却予定の考慮含む）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック挙動）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応した発注株数算出。単元株丸め、per-stock 上限、aggregate cap（スケールダウン）処理、cost_buffer を用いた保守的見積り、残余キャッシュによる再配分ロジック等を実装。
  - src/kabusys/portfolio/__init__.py で上記関数を公開。

- リサーチ（ファクター計算）
  - src/kabusys/research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加。
    - Momentum（1M/3M/6M、MA200乖離）や Volatility（ATR20、平均売買代金、出来高比）等を計算する関数を実装。
    - 計算に必要なスキャン幅やウィンドウ長は定数化。

- Paper Trading 検証レポートツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からレポートを生成する CLI を追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出し、閾値に基づく PASS/FAIL 判定を出力。
    - P95 計算と日付フィルタ（--from / --to）をサポート。

Changed
- なし（初回リリース）

Fixed
- 環境変数パーサの堅牢化
  - export 挙動、クォート内のバックスラッシュエスケープ、行内コメントの扱いなどを正しく処理するよう改善（src/kabusys/config.py）。
- 環境変数の妥当性チェックとわかりやすい警告メッセージを追加（PAPER_FILL_MODE, MONITOR_POLL_INTERVAL の不正値時のフォールバックなど）。

Removed
- なし

Notes / Required setup
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（validate_config にも同様のチェックを実装）
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
- .env ファイルは config_setup.py で生成・更新可能。生成後は validate_config で検証することを推奨。

開発者向け補足
- 実行スクリプトは直接実行可能（python -m kabusys.run_execution / python -m kabusys.run_monitoring）および CLI ツール（python -m kabusys.config_setup, python -m kabusys.validate_config, python -m kabusys.tools.paper_verification_report）が利用可能。
- psutil と duckdb、（オプションで PyYAML）が依存関係として必要。PyYAML が無い場合は config/*.yaml の内容検査はスキップされます。
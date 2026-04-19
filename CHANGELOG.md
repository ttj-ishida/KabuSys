# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
（この履歴はソースコードの内容から推測して作成しています）

現在のパッケージバージョン: 0.1.0

## [Unreleased]
- 今後の変更・予定をここに記載します。

## [0.1.0] - 2026-04-19
初回公開リリース（ソースコードから推測した機能一覧と主要実装点）。

### Added
- 基本アプリケーション構成
  - パッケージ名: `kabusys`（__version__ = "0.1.0"）。
  - モジュール群: execution, monitoring, portfolio, research, utils, tools, config 関連 CLI など。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は本番 DB と切り離して paper_trading 用 DB（デフォルト: data/paper_trading.db）を使用。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンド実行（スレッド）。
    - 停止制御: data/stop_requested.flag と data/execution.pid を利用。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB（SQLite）は実行環境にかかわらず本番 sqlite_path を使用する設計。

- 設定管理
  - config.py
    - .env 自動ロード（プロジェクトルートを .git または pyproject.toml から検出）。
    - OS環境変数優先、.env.local は .env を上書きする挙動。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須 env 取得用 `_require()`、各種設定プロパティ（DB パス、PID ファイル、各種しきい値、env 判定など）を提供。
    - PAPER_FILL_MODE の検証、有効値（instant/partial/never/reject）チェック。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - J-Quants / kabu API / DB パス / LINE 通知 / ログレベル / Kill Switch 設定など主要項目を対話的に入力・保存。
  - validate_config.py
    - 起動前に .env と config/*.yaml（存在する場合）を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、YAML のパース検証（PyYAML があれば実施）。
    - `--strict` フラグで警告をエラー扱いにするオプションを提供。

- ロギング／プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティ。
    - LOG_LEVEL / LOG_DIR / app_name による柔軟な解決。
    - ログディレクトリ作成に失敗してもコンソール出力でフォールバック。
  - utils/process_priority.py
    - Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（プラットフォーム依存の例外処理あり）。
    - アクセス権限エラーや未対応 OS は警告ログを出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順・タイブレーク）select_candidates。
    - 等分配/スコア加重配分 calc_equal_weights / calc_score_weights（全スコアが 0 の場合は等分配へフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存ポジション・価格を考慮して候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知のレジームは警告の上 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各種配分方法（risk_based / equal / score）に基づく発注株数算出。
    - 単元株丸め（lot_size）、1銘柄上限、aggregate cap によるスケーリング、コストバッファ考慮、端数調整ロジックを実装。

- Research（ファクター計算）設計（部分実装）
  - research/factor_research.py
    - DuckDB を使用して prices_daily / raw_financials を参照し、Momentum/Value/Volatility/Liquidity の計算を行う設計。
    - モメンタム計算 calc_momentum の仕様（1M/3M/6M、MA200 乖離など）とスキャン期間の定義が含まれる（関数実装は途中まで、設計方針を明示）。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH 指定可）からレポートを生成する CLI。
    - 稼働率、注文成功率（fill_rate）、送信率、P95 レイテンシ 等の取得、閾値判定（デフォルト基準値をソース中に定義）を行い PASS/FAIL を出力。
    - 日付フィルタ（--from/--to）、--db オプション対応、SQL クエリの堅牢化（テーブル未存在時の例外回避）。

- DB 関連
  - DuckDB/SQLite を併用する設計（duckdb_path / sqlite_path）。
  - 監視 DB の初期化 init_monitoring_db 呼び出しにより必要テーブルの存在を保証（冪等）。

### Changed
- （初回リリースのため該当無し。将来のリリースでここに変更点を追加予定）

### Fixed
- （初回リリースのため該当無し）

### Deprecated
- （初回リリースのため該当無し）

### Security
- （初回リリースのため該当無し）

---

注意:
- この CHANGELOG はソースコードを読んで推測して作成しています。実際のリリースノートや公開日、細かな実装差分はリポジトリの公式履歴（git commit / リリースタグ）に基づいて更新してください。
# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-04-23
初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。主な追加・設計方針は以下の通りです。

### Added
- 全体
  - パッケージ初期バージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を基準）。CWD に依存しない .env 自動読み込みを導入（src/kabusys/config.py）。

- 実行系
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine をバックグラウンドスレッドで起動し、stop フラグ検出で安全に停止可能。
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用して環境に応じたブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の依存コンポーネントを組み立てて起動。
    - 実行用 PID ファイルのサポート（data/execution.pid）。
  - 実行エンジンのリスク制御設定（RiskConfig）に初期化パラメータを導入（例: max_position_pct, max_drawdown, rate_limit_per_sec 等）。

- 監視系
  - システム監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）によるループ終了処理を実装。
    - 監視用 DB（monitoring.db）は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 監視開始時にプロセス優先度を High に設定（set_process_priority 呼び出し）。

- 設定管理 / CLI
  - Settings クラスを実装（src/kabusys/config.py）。
    - 多数の設定プロパティを提供（J-Quants トークン、kabu API、DuckDB/SQLite パス、ペーパー取引用 DB、PID/kill flag パス、しきい値、環境判定等）。
    - PAPER_FILL_MODE の検証（"instant"/"partial"/"never"/"reject" のみ許可）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - 自動 .env 読み込み（.env → .env.local、OS 環境変数優先）と無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を実装。
  - 設定検証ツールを追加（src/kabusys/validate_config.py）。
    - CLI で .env と config/*.yaml の基本チェックを実行。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース（PyYAML がある場合）を実施。
    - --strict オプションで警告を失敗扱いにできるモードを追加。
    - 本番環境時の「ライブガード」チェック（LINE 通知の未設定や Kill Switch の自動クリア設定の警告）。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env の初期作成・更新を支援。シークレット値はマスク表示、選択肢/デフォルト/任意項目に対応。
    - 既存 .env の読み込みと Enter キーによる再利用をサポート。
    - .env をテンプレート形式で書き出すユーティリティを提供。

- ロギング / プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Posix の差分を吸収してプロセス優先度 (high/normal/low) を設定。
    - CPU affinity を最初 N コアに固定する機能を追加。
    - psutil による権限不足や未対応 OS でのフォールバック・警告を実装。

- ポートフォリオ構築（ポートフォリオモジュール）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で候補を選択（タイブレークに signal_rank を利用）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア全体が 0 の場合は等分にフォールバック）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクターエクスポージャーが上限を超える場合、新規候補を除外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は警告して 1.0 にフォールバック）。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - risk_based, equal, score の配分方式をサポート。
    - 損切り率・リスク割合・最大保有比率・利用率・単元株（lot_size）を考慮した計算。
    - aggregate cap（利用可能現金を超えた場合のスケーリング）を実装。端数処理で lot_size 単位の再配分を行う。
    - price 欠損時のログ出力およびスキップ挙動を明記。

- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite の paper_trading DB を参照して稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計・判定。
    - P95 計算、日付フィルタ（--from/--to）、閾値による PASS/FAIL 判定を実装。
    - DB ファイルが存在しない場合のエラーメッセージを提供。

- リサーチ（開発中）
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム / Value / Volatility / Liquidity の構想と定数定義を実装。DuckDB 接続を受け取り prices_daily / raw_financials テーブルからファクターを算出する設計（実装の続きあり、ファイル末尾は途中で切れている）。

### Changed
- 初期設計として以下の運用上の決定を明記
  - 監視プロセス（monitoring）は環境変数 KABUSYS_ENV に依存せず、本番 sqlite_path（settings.sqlite_path）を使用する仕様とした（設計上の注意点・意図的挙動）。

### Fixed
- .env 読み込みの堅牢化（src/kabusys/config.py）
  - export KEY=val 形式、クォート文字列中のバックスラッシュエスケープ、インラインコメント扱い、コメントの境界判定などを細かく処理。
  - .env ファイル読み込みで例外が発生した場合は警告を出してスキップする挙動を追加。

### Security
- .env の取り扱いに関する注意喚起を config_setup の出力に明記（.env を絶対に Git にコミットしないこと）。

### Notes / Known issues
- research/factor_research.py は計算ロジックの実装途中でファイル末尾が未完の状態です（今後の追加実装予定）。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価など）は TODO コメントとして残してあります。
- process_priority / cpu_affinity 設定は権限や OS に依存するため、失敗時は警告を出してスキップする設計になっています。

---

この CHANGELOG はソースコードからの推測に基づいて作成しています。実際のリリースノートや変更履歴は運用方針に合わせて適宜調整してください。
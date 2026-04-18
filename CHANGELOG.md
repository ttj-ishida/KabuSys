# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

最新の変更は一番上に記載します。

Unreleased
----------
- （今後のリリースに向けた空のセクション。現在のコードベースは以下の初期リリースとして記録されています）

[0.1.0] - 2026-04-18
-------------------
初回公開リリース。本リポジトリは日本株自動売買システム「KabuSys」のコアユーティリティ群、実行/監視スクリプト、ポートフォリオ構築ロジック、設定周りの CLI、検証ツール等を含みます。

Added
- 基本的なパッケージメタ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として定義。

- 実行エンジン起動スクリプト
  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動・監視する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を利用して `data/paper_trading.db` を使う（本番 DB と完全分離）。
    - 停止制御にファイルベースのフラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を採用。
    - 起動時にプロセス優先度を "high" に設定（`set_process_priority` を利用）。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler 等）の組み立てロジックを含む。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit など）を指定。

- 監視ループ起動スクリプト
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き機能（不正値はデフォルト 60 秒にフォールバック）。
    - 監視 DB（SQLite）は環境に関わらず本番用 `sqlite_path` を使用（監視は本番設定で動作させる設計）。
    - stop フラグ検出・例外捕捉・正常終了処理を実装。

- 設定管理
  - `src/kabusys/config.py`
    - .env 自動読み込み（`.env` → `.env.local` の順、既存 OS 環境変数は保護）。
    - `.env` のパース実装（export プレフィックス、クォートとバックスラッシュエスケープ対応、インラインコメント処理）。
    - 必須環境変数チェック（`_require`）と各種設定プロパティ（DB パス、PID / kill flag パス、閾値など）。
    - `KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` の値検証を実装。

- 設定ウィザード CLI
  - `src/kabusys/config_setup.py`
    - .env の対話式生成/更新ウィザード。
    - シークレット入力/マスク表示、選択肢、デフォルト値、保存の確認までの対話フローを提供。
    - `.env` の書き出しテンプレートを実装（注意書き付き）。

- 設定検証 CLI
  - `src/kabusys/validate_config.py`
    - 起動前に .env と `config/*.yaml` の不備を検出する CLI。
    - 必須/任意環境変数チェック、KABUSYS_ENV の整合性、DB パスの親ディレクトリ確認、YAML ファイルの存在と（PyYAML インストール時は）パース検証、`live` 時の追加ガード（LINE 設定未設定や Kill Switch 自動クリア設定の警告）を実装。
    - `--strict` オプションで警告も失敗扱い（exit 1）にできる。

- ポートフォリオ構築・リスク調整・ポジション決定アルゴリズム（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選定（スコア降順、タイブレーク: signal_rank）`select_candidates`
    - 等金額配分 `calc_equal_weights`
    - スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等金額にフォールバック）
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限 `apply_sector_cap`（既存保有を考慮して同一セクターの新規候補を除外）
    - レジーム乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" -> 1.0/0.7/0.3、未知レジームは警告して 1.0 フォールバック）
  - `src/kabusys/portfolio/position_sizing.py`
    - ポジションサイズ計算 `calc_position_sizes`
      - 複数の allocation_method ("risk_based", "equal", "score") をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケーリング、端数処理（fractional remainder に基づく追加配分）を実装。
      - cost_buffer による保守的見積りをサポート。
      - risk_based における (portfolio_value * risk_pct) / (price * stop_loss_pct) の算出ロジックを採用。

- 研究 / ファクター計算（部分実装）
  - `src/kabusys/research/factor_research.py`
    - ファクター定義・設計方針を記述（Momentum, Value, Volatility, Liquidity）。
    - DuckDB 接続で prices_daily / raw_financials を参照し、日付基準のモメンタム等を計算する方針。注: ファイル末尾に実装途中の痕跡あり（関数実装は継続を想定）。

- ロギング / プロセスユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - 統一的なログ初期化関数 `setup_logging(app_name, log_dir, level)` を提供。
    - stdout（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラのクリーンアップ処理を実装（重複設定防止）。
  - `src/kabusys/utils/process_priority.py`
    - クロスプラットフォームのプロセス優先度設定 `set_process_priority(level)`（Windows の priority class / POSIX の nice 値を吸収）。
    - CPU affinity 設定補助 `set_cpu_affinity(cpu_count)`（利用不可時は警告してスキップ）。
    - 権限不足や未対応 OS の場合に安全にフォールバックしログ出力。

- 監視関連 DB 初期化ユーティリティ
  - `src/kabusys/monitoring/monitoring_db.py` への依存を用いて、監視テーブルの初期化を冪等に行う（run_monitoring/run_execution から呼び出し）。

- Paper Trading 検証レポート
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite DB を解析してレポートを生成する CLI ツール。
    - システム稼働率、注文成功率（Fill/Created）、送信率、リスク却下数、レイテンシ統計（avg/max/P95）を集計。
    - PASS/FAIL 基準（稼働率 ≥ 99%、Fill ≥ 90%、Send ≥ 95%、P95 latency ≤ 200ms）を定義して判定。
    - DB 存在チェック・範囲フィルタ（--from / --to）をサポート。

Changed
- （初回リリースのため該当なし）

Fixed / Behavior improvements
- 環境変数・設定の堅牢化
  - `.env` の読み込みで export プレフィックス・クォート・エスケープ・インラインコメント等に対応。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意（テスト時などに便利）。
  - `MONITOR_POLL_INTERVAL` の検証（1 未満や非数値は警告してデフォルト 60 秒にフォールバック）。
  - `PAPER_FILL_MODE` の妥当性チェック（許容値以外は ValueError）。
  - `KABUSYS_ENV` / `LOG_LEVEL` 等の不正値に対する早期エラー報告。

- 安全性 / 運用性
  - 監視・実行プロセスの停止にファイルフラグ方式を採用（stop_requested.flag）、長時間のデーモン実行に対応。
  - ログディレクトリ作成失敗時もコンソールログによる最低限の可観測性を確保。
  - プロセス優先度や CPU affinity の設定失敗は警告ログ出力でフォールバックし、起動失敗にはしない。

Known issues / Notes
- research/factor_research.py は設計が詳細に記述されているが、一部実装が未完（ファイル末尾に中断した実装の痕跡あり）。
- apply_sector_cap の価格欠損（price が 0.0 の場合）によりエクスポージャーが過少見積りされ得る旨の TODO コメントあり。将来的に価格フォールバック（前日終値等）を検討する必要あり。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別単元対応を計画）。
- run_monitoring は監視用 DB に "本番 sqlite_path" を常に使用する設計のため、開発環境での監視データ分離には注意が必要。
- DuckDB を分析用に利用するが、DuckDB ファイルパスの親ディレクトリが存在しない場合は警告（自動作成される旨）となる。PyYAML が未インストールだと config YAML の内容検証はスキップされる。

Migration
- なし（初回リリース）

Authors
- KabuSys 開発チーム（コード内コメント・ドキュメントに基づく自動生成的まとめ）

License
- ソース内に明示的なライセンス記載がない場合はリポジトリのルートにある LICENSE を参照してください（本 CHANGELOG はコード差分から推測して作成したドキュメントです）。

---- 

補足:
- 本 CHANGELOG は与えられたソースコードから機能・振る舞いを推測して作成したものです。実際のリリースノートや変更履歴はリポジトリのコミット履歴や開発者の意図に基づいて調整してください。
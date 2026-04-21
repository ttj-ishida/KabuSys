# Changelog

すべての非互換な変更はメジャーリリースに記載します。
このファイルは "Keep a Changelog" の形式に準拠しています。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 基本パッケージ情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。

- 環境設定 / 設定管理
  - Settings クラスを実装して環境変数／設定値を集中管理（src/kabusys/config.py）。
    - J-Quants / kabuステーション / LINE / DB / 監視閾値等のプロパティを提供。
    - KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL 等の妥当性チェック機能を持つ。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE の検証を実装。
    - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

- .env 対応ユーティリティ
  - .env のパース実装（クォート、export prefix、インラインコメント、エスケープをサポート）（src/kabusys/config.py）。
  - 対話式ウィザードで .env を生成／更新する CLI（src/kabusys/config_setup.py）。
    - ウィザードは既存 .env の読み込み・既存値再利用・シークレット表示（マスク）をサポート。
    - 出力テンプレートは説明付きで .env に保存（デフォルト path: プロジェクトルートの .env）。

- 設定検証 CLI
  - 起動前に環境変数や config/*.yaml を検証する `validate_config` CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DBパスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML あれば実行）、本番時の追加ガードを実装。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行エンジン起動スクリプト
  - 実売買／ペーパートレードの ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（Mock / 実装を透過）。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動を実装。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）を扱い、外部からの停止要求に対応。
    - デフォルトのプロセス優先度を "high" に設定。

- 監視（Monitoring）起動スクリプト
  - SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境にかかわらず監視は本番 sqlite_path を使用（監視データは本番 DB に記録）。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検知でループ安全終了。
    - プロセス優先度を "high" に設定。

- ロギング関連ユーティリティ
  - 統一的ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力用 StreamHandler と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 既存ハンドラの二重設定を防止してクリア後に再設定。
    - LOG_LEVEL / LOG_DIR の優先解決ロジックを実装。ファイル出力ディレクトリ作成失敗時はコンソールのみで継続。

- プロセス優先度 / CPU affinity ユーティリティ
  - 複数 OS (Windows / POSIX) に対応するプロセス優先度設定と CPU affinity 設定を実装（src/kabusys/utils/process_priority.py）。
    - set_process_priority(level: "high"|"normal"|"low")：psutil を用いて優先度を設定（失敗時は警告でスキップ）。
    - set_cpu_affinity(cpu_count: int | None)：最初の N コアにピン留め（未対応環境は警告でスキップ）。

- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み付け（portfolio_builder）（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates / calc_equal_weights / calc_score_weights を実装。
    - スコア合計が 0 の場合は等配分にフォールバックし警告を出力。
  - セクター上限・レジーム乗数（risk_adjustment）（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap：セクター集中上限を評価し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier：市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返却（未知レジームは警告して 1.0 にフォールバック）。
    - 既知の TODO: price 欠損時のフォールバック戦略に関する注記を実装（将来対応予定）。
  - 株数決定（position_sizing）（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes を実装：allocation_method ("risk_based" / "equal" / "score") に基づく株数計算、単元株（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer（手数料・スリッページ見積り）による保守的見積り、スケーリング後の端数再配分ロジックをサポート。

- 研究／ファクター計算（骨格実装）
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム、MA200乖離、ATR、流動性等の計算方針と定数を定義。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針を記載。
    - モメンタム計算関数 calc_momentum のインターフェースと説明を実装（実装途中の箇所あり）。

- Paper Trading 検証レポート
  - ペーパートレーディング用検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - システム稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどを集計し、PASS/FAIL 判定を出力。
    - 判定閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）を定義。
    - レポートは期間フィルタ（--from/--to）に対応。

- その他ユーティリティ / 初期化
  - monitoring DB 初期化 helper（init_monitoring_db）や SystemMonitor / ExecutionEngine 等の呼び出し箇所を起動スクリプトに組み込み。
  - 停止フラグ／kill フラグ／pid ファイルを用いた外部制御（data ディレクトリ内ファイル）に対応。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の問題 / TODO
- src/kabusys/research/factor_research.py の calc_momentum 実装が途中で切れている（ファイル末尾で未完）。完全な時系列計算ロジックの実装が必要。
- risk_adjustment.apply_sector_cap で price が欠損（0.0）の場合のエクスポージャ評価に関する TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討。
- 一部機能は外部依存（psutil, duckdb, PyYAML 等）が必要。依存が満たされない環境では該当機能がスキップまたは警告となる挙動をとる。

### セキュリティ (Security)
- 初回リリースのため該当なし。

----------

注:
- この CHANGELOG はリポジトリ内のソースコードから推測して作成しています。実装意図や外部仕様に関する詳細はドキュメントや変更履歴を別途参照してください。
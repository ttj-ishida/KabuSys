# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-18

### 追加
- 基本アプリケーション情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として設定。

- 環境設定関連
  - Settings クラスを src/kabusys/config.py に実装。.env / 環境変数から各種設定（J-Quants、kabuAPI、DB パス、Paper Trading 設定、監視閾値、ログ設定など）を取得可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を利用した自動 .env 読み込みの無効化機能。
    - PAPER_FILL_MODE の入力検証（"instant" / "partial" / "never" / "reject"）。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - 各種デフォルトパス（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）をサポート。
  - .env ファイルの読み込みロジック（_load_env_file）を実装。export 形式とクォート、エスケープ、インラインコメント処理に対応。既存 OS 環境変数を保護する protected オプションを用意。

- 環境構築・検証 CLI
  - 対話式設定ウィザード（src/kabusys/config_setup.py）を追加。
    - .env の初期作成・更新を対話式で支援。シークレット項目のマスク表示、デフォルト値、選択肢サポート、保存確認を実装。
    - .env 書き出しフォーマットを定義（コメントヘッダ付き）し、保存後の次ステップ案内を出力。
  - 設定検証ツール（src/kabusys/validate_config.py）を追加。
    - 必須環境変数の検出、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がインストールされている場合）。
    - KABUSYS_ENV=live の際の本番ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を失敗扱いにするモードをサポート。

- 実行・監視起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - 起動時にプロセス優先度を high に設定。
    - Paper Trading 環境では専用の SQLite（data/paper_trading.db）を利用して本番 DB と完全に分離。
    - BrokerClientFactory を通じたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の起動を実装。
    - 停止フラグ（data/stop_requested.flag）や PID ファイルの取り扱い、スレッドでの実行・停止処理を実装。
    - RiskManager のデフォルト設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 系、max_drawdown 等）を設定し、初期 available_cash を broker.get_available_cash() から取得。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効な値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視用 DB 初期化を行う）。
    - 停止フラグ検知により安全にループを終了する処理を実装。
    - check_once() の例外を捕捉してループ継続する堅牢化。

- ロギング・プロセスユーティリティ
  - ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定。既存ハンドラのクリア、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR を環境変数から解決、app_name によるログファイル（logs/<app_name>.log）命名。
  - プロセス優先度・CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収。nice 値や Windows の priority クラスを用いて優先度設定を試みる。失敗した場合は警告してスキップ。
    - set_cpu_affinity により最初の N コアへプロセスを固定する機能を備える。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・同点タイブレークで上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。全スコアが 0 の場合は等配分にフォールバックして警告。
  - セクターリスク制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター比率に基づき新規候補を除外（"unknown" セクターは除外対象にしない）。sell_codes（当日売却予定）を除外してエクスポージャー計算。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは警告の上 1.0 をフォールバック。
  - 発注株数計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応。lot_size（単元）で丸め、per-position 上限・aggregate cap（available_cash）を実装。コストバッファを考慮した保守的見積りと、スケールダウン後の端数配分ロジック（残差ソート）を導入。

- リサーチ / ファクター計算（骨格）
  - src/kabusys/research/factor_research.py にモメンタム等ファクター計算の設計・一部実装を追加（DuckDB 経由で prices_daily / raw_financials を参照し、mom_1m/3m/6m、MA200 乖離、ATR、出来高系等を計算する設計方針を含む）。（ファイルは途中までの実装）

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py を追加。
    - Paper Trading の SQLite DB を解析して稼働率（uptime）、注文成功率（fill_rate）、送信率、レイテンシ（avg/max/P95）、リスク却下数等を集計するレポートを生成。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）し、Pass/Fail 判定を出力。
    - --from / --to / --db コマンドラインオプションをサポートし、PAPER_TRADING_SQLITE_PATH 環境変数を優先した DB パス解決を行う。

- 監視 DB 初期化
  - monitoring 用 DB 初期化関数 init_monitoring_db がスクリプトから呼び出され、監視テーブルの存在を冪等に保証。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 注意事項 / マイグレーションノート
- .env ファイルは絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも注記）。
- 実行時のログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗するとコンソール出力のみになります。
- Paper Trading 実行時は本番用 SQLite と分離された PAPER_TRADING_SQLITE_PATH を使用するため、誤って本番 DB を上書きするリスクは低減されていますが、.env の設定は慎重に行ってください。
- KABUSYS_ENV=live の場合は validate_config による事前チェックを強く推奨します。特に LINE 通知の設定と KILL_FLAG_CLEAR_ON_START の値を確認してください。

--- 

今後のリリースでは、research/factor_research の完全実装、ExecutionEngine / Monitoring の詳細なテスト追加、エラーハンドリング強化などを予定しています。
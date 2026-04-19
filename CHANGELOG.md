CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。
リリース日: 2026-04-19

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-19
------------------

Added
- 初回リリース（バージョン 0.1.0）。
- 基本 CLI/サービス起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用の SQLite (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用して本番 DB と分離。  
    - BrokerClientFactory からブローカークライアントを生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立て、ExecutionEngine を別スレッドで実行。  
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid） に対応し、安全停止処理を実装。  
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。  
    - 停止フラグの検知、check_once() 実行時の例外ハンドリング、終了時の DB クローズを実装。
- 設定管理・セットアップ・検証
  - config.py: Settings クラスを導入し、環境変数から各種設定を取得（バリデーション付き）。  
    - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml ベース）を特定して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。  
    - 環境値検証: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の妥当性チェックを実装。  
  - config_setup.py: 対話式ウィザードで .env を生成/更新するツールを追加。秘密情報はマスク表示、保存前の確認あり。  
  - validate_config.py: 起動前に .env と config/*.yaml の基本的な妥当性を検証する CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、PyYAML がない場合は YAML チェックをスキップする挙動を実装。  
    - --strict オプションで警告を失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティを追加。  
    - stdout への StreamHandler + 日次ローテート（TimedRotatingFileHandler）でファイル出力（logs/<app_name>.log）、30 日のバックアップ保持。  
    - ログレベル・ログディレクトリは引数／環境変数で指定可能。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。  
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティを追加。  
    - Windows/Linux/macOS に対応する nice / priority クラスの設定、アクセス権限不足等のフォールバックと警告出力を実装。  
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を提供（存在しない場合はスキップ）。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py: シグナル選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。  
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告を出力。  
  - portfolio/risk_adjustment.py: セクター集中制限とレジーム乗数。  
    - apply_sector_cap: セクターごとの既存エクスポージャー算出（売却予定銘柄を除外可）。"unknown" セクターは制限対象外。  
    - calc_regime_multiplier: regime ラベル（"bull"/"neutral"/"bear"）に応じた乗数を返す（未知のレジームは警告して 1.0 にフォールバック）。  
  - portfolio/position_sizing.py: 株数算出ロジック（allocation_method: "risk_based"/"equal"/"score"）を追加。  
    - lot_size（単元株）で丸め、1 銘柄上限・aggregate cap（available_cash）に応じたスケーリング、cost_buffer を考慮した保守的見積り、残差を再配分するアルゴリズムを実装。
  - portfolio/__init__.py で上記関数群を公開。
- リサーチユーティリティ（基盤）
  - research/factor_research.py（ファクター計算の骨格）を追加。モメンタム・MA・ATR・出来高等のファクター算出を想定した設計（DuckDB 経由で prices_daily / raw_financials を参照）。※ ファイルは途中まで実装（継続予定）。
- Paper Trading 関連ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成スクリプトを追加。  
    - 稼働率、注文成功率（fill_rate）、送信率、レイテンシ（avg / max / P95）、リスク却下数等を集計し PASS/FAIL 判定を出力。  
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。コマンドラインで日付範囲指定可能。
- 監視 DB 初期化
  - monitoring/monitoring_db.py（参照されている init_monitoring_db）を用いて起動時に監視テーブルが存在することを保証する（冪等処理を想定）。
- パッケージメタ
  - __init__.py によるバージョン管理（__version__ = "0.1.0"）と公開モジュール一覧を追加。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- 環境変数設定ファイル (.env) の生成時に注意喚起を出力（.env を Git にコミットしないよう明記）。

Notes / TODO
- research/factor_research.py は未完（ファクター計算ロジックの続きが残っている）。  
- 一部 TODO コメントあり（例: position_sizing で銘柄別 lot_size 対応、risk_adjustment の price フォールバックなど）。  
- 実運用時の環境（KABUSYS_ENV=live）では LINE 通知設定や Kill Switch の挙動を validate_config で必ず確認することを推奨。

お問い合わせ
- リポジトリ内の各モジュール（config_setup.py, validate_config.py, run_execution.py, run_monitoring.py, utils/*, portfolio/*, tools/*）を参照してください。
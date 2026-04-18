CHANGELOG
=========

すべての重要な変更点を Keep a Changelog の形式に従って日本語で記載します。

フォーマットについては https://keepachangelog.com/ja/ を参照してください。

Unreleased
----------

（なし）

0.1.0 - 2026-04-18
------------------

Added
- 初期リリースを追加。
- 設定・環境周り
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 実装: src/kabusys/config.py
  - 高機能な .env パーサを実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - 実装: src/kabusys/config.py::_parse_env_line、_load_env_file
  - Settings クラスを提供し、環境変数からアプリ設定を取得するラッパーを実装。各種プロパティ（DB パス、KABUSYS_ENV 判定、PAPER_FILL_MODE のバリデーションなど）を定義。
    - 実装: src/kabusys/config.py::Settings
  - 環境設定ウィザード CLI を追加（.env の対話式生成／更新）。
    - 実装: src/kabusys/config_setup.py
  - 設定検証 CLI を追加（必須環境変数、パス、YAML ファイルの存在／パース、live 環境用ガード等をチェック）。--strict モードをサポート。
    - 実装: src/kabusys/validate_config.py
- 実行／監視ランナー
  - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し本番 DB と分離。停止フラグ・PID 管理・スレッド起動処理を実装。
    - 実装: src/kabusys/run_execution.py
  - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知でループ終了。
    - 実装: src/kabusys/run_monitoring.py
- ロギング & プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティを追加。コンソール（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler、30日保持）をルートロガーへ設定、既存ハンドラのクリアを行う。
    - 実装: src/kabusys/utils/logging_setup.py
  - プラットフォーム非依存のプロセス優先度および CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収しアクセス権限失敗時は警告でスキップ。
    - 実装: src/kabusys/utils/process_priority.py
- Execution エコシステム
  - ブローカークライアントファクトリ（BrokerClientFactory）経由で broker を生成する仕組みを組み込む設計。
  - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てフローを run_execution に実装。RiskManager のデフォルト設定（max_position_pct 等）および初期ポートフォリオ値を broker.get_available_cash() から取得する動作を導入。
    - 実装（参照）: src/kabusys/run_execution.py
- 監視・モニタリング DB 初期化
  - 監視用テーブルの初期化処理を idempotent に行う init_monitoring_db を利用する仕組みを導入（Execution / Monitoring 両スクリプトで実行）。
    - 実装: src/kabusys/run_monitoring.py、src/kabusys/run_execution.py（init_monitoring_db 呼び出し）
- Portfolio モジュール（銘柄選定・配分・株数算出・リスク調整）
  - 銘柄選定ロジック（select_candidates）を実装。スコア降順・signal_rank によるタイブレーク。
    - 実装: src/kabusys/portfolio/portfolio_builder.py
  - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）を実装。全スコアが 0 の場合は等金額配分へフォールバックし警告を出す。
    - 実装: src/kabusys/portfolio/portfolio_builder.py
  - セクター集中制限（apply_sector_cap）を実装。既存保有を元にセクター別エクスポージャーを計算し上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - 実装: src/kabusys/portfolio/risk_adjustment.py
  - レジーム乗数（calc_regime_multiplier）を実装。regime による投下資金の乗数を返す（bull/neutral/bear、未知値はフォールバックと警告）。
    - 実装: src/kabusys/portfolio/risk_adjustment.py
  - ポジションサイズ計算（calc_position_sizes）を実装。allocation_method に応じて risk_based / equal / score をサポート。単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap とスケーリングロジック（残差処理）を搭載。
    - 実装: src/kabusys/portfolio/position_sizing.py
  - portfolio パッケージのエクスポートを整備。
    - 実装: src/kabusys/portfolio/__init__.py
- 研究用（research）
  - ファクター計算モジュール（factor_research）の雛形を追加。モメンタム（1M/3M/6M）、MA200 乖離、ATR、出来高指標などの実装方針と定数を定義。DuckDB 経由で prices_daily / raw_financials を参照する設計。
    - 実装（部分）: src/kabusys/research/factor_research.py
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加。SQLite（paper_trading.db）を参照して稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均／最大／P95）を集計し PASS/FAIL を判定。P95 計算ユーティリティを含む。
    - 実装: src/kabusys/tools/paper_verification_report.py

Changed
- run_monitoring の設計決定: Monitoring は KABUSYS_ENV に依存せず「本番」用 sqlite_path を使用するよう明記（監視は本番データを参照）。
  - 実装: src/kabusys/run_monitoring.py（ドキュメントと接続先の扱い）
- ロギング設定の標準化: 全起動スクリプトは setup_logging を呼び出すことを推奨し、ログ表示／ファイルローテーションを統一。
  - 実装: src/kabusys/utils/logging_setup.py

Fixed
- .env 読み込み時のエラーハンドリングを改善。ファイル読み込み失敗時は警告を出して処理を継続。
  - 実装: src/kabusys/config.py::_load_env_file
- MONITOR_POLL_INTERVAL の不正値に対してフォールバック（デフォルト 60 秒）し、ログに警告を出すことで ValueError を回避。
  - 実装: src/kabusys/run_monitoring.py::_get_poll_interval
- process_priority / set_cpu_affinity の権限エラーや未対応 OS に対し安全にスキップする挙動を追加（警告ログ）。

Notes / その他の設計上の注意
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離されるよう paper_sqlite_path を利用。
- RiskManager 初期設定では initial_portfolio_value をブローカーから取得するため、BrokerClient 実装側で get_available_cash() を提供する必要がある。
- portfolio の価格データ欠損時の挙動について TODO コメントあり（将来的にフォールバック価格の導入を検討）。
- validate_config は PyYAML が未インストールの場合に YAML 検証をスキップし警告を出す。

開発者向けヒント
- ログの出力先は環境変数 LOG_DIR で切替可能。ログレベルは LOG_LEVEL 環境変数で調整。
- .env の生成は python -m kabusys.config_setup で対話式に行い、その後 python -m kabusys.validate_config で検証するワークフローを推奨。
- Paper Trading の検証レポートは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能。

今後の予定（提案）
- factor_research の各ファクター計算を完実装（現在はモメンタム等の雛形）。
- 銘柄別 lot_size のサポート（stocks マスタへの拡張）を position_sizing に追加。
- 監視・実行のユニットテストと E2E テストを追加して運用安全性を向上。
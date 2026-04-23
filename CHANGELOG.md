CHANGELOG
=========
All notable changes to this project will be documented in this file.

この CHANGELOG は "Keep a Changelog" のフォーマットに準拠しています。  
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 初回リリース。基本的な自動売買フレームワークを追加。
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"
- 環境設定 / 設定管理
  - .env 自動ロード機能を実装（プロジェクトルートの .env と .env.local を読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（src/kabusys/config.py）。
  - Settings クラスを追加し、アプリ内から型付きで環境変数へアクセスできるようにした（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 用設定等を含む）。
  - 環境変数パースの堅牢化（export プレフィックス、クォートやコメント処理対応）。
- 環境設定 CLI（ウィザード）
  - .env の初期作成・更新を対話式で支援する config_setup CLI を追加（src/kabusys/config_setup.py）。
  - 各設定項目の説明・デフォルト・マスク表示（シークレット項目）に対応。
- 設定検証 CLI
  - 起動前に .env / config/*.yaml 等の整合性をチェックする validate_config CLI を追加（--strict オプションで警告を FAIL 扱いにできる）（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML が存在する場合）等を行う。
- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の起動/停止制御を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル処理に対応。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor を用いた定期チェックループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計。
    - 停止フラグ検知時に安全にループを終了。
- モニタリング DB 初期化
  - 監視用テーブルの冪等な初期化処理を提供（init_monitoring_db を各起動スクリプトで呼び出す）。
- ロギング・プロセス管理ユーティリティ
  - 一貫したログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout StreamHandler と 日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップする安全処理。
    - LOG_LEVEL/LOG_DIR の優先順位で解決。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS の差分を吸収して nice/HIGH_PRIORITY_CLASS 等を設定。アクセス権限不足等は警告を出してスキップ。
    - set_cpu_affinity で最初の N コアに固定可能（権限や OS に依存）。
- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates / calc_equal_weights / calc_score_weights を提供。スコアが全て 0 の場合は等分配にフォールバック。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap によるセクター上限フィルタリング、calc_regime_multiplier によるレジーム別投下資金乗数（bull/neutral/bear）を実装。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の配分方式に対応。lot_size（単元）で丸め、max_position_pct や aggregate cap（available_cash）を考慮したスケーリングロジックを実装。
    - cost_buffer による手数料・スリッページ見積りをサポート。
- ペーパートレード検証ツール
  - Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出してレポート出力。
    - デフォルト基準値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。
    - --from/--to/--db オプションに対応。PAPER_TRADING_SQLITE_PATH 環境変数をサポート。
- リサーチ（実装途中含む）
  - ファクター計算モジュールの雛形を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の設計に基づく実装方針と一部関数（P95 計算等）。（注: 一部実装が継続中）

Changed
- （初回リリースのため無し）

Fixed
- （初回リリースのため無し）

Security
- 機密情報（API トークン等）は .env に保持する前提。config_setup は .env の生成を行うが、.env を Git にコミットしないよう注意喚起を出力。

Notes / 動作上の重要ポイント
- Paper Trading と Live の DB 分離
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番監視 DB と分離する設計。
- 監視コンポーネントは常に sqlite_path（デフォルト data/monitoring.db）を参照する点に注意。
- process priority / cpu affinity の設定は OS 権限やプラットフォームに依存し、失敗した場合はログ警告の上で安全にスキップされる。
- .env パースは export 付き行、クォート内エスケープ、インラインコメントの扱いなどに対応。OS 環境変数は既定で保護され、.env.local で上書き可能。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存される。ログディレクトリ作成に失敗した場合はコンソール出力のみになる。

今後の予定（例）
- research.factor_research の完全実装（ファクター計算ロジックと DuckDB クエリ最適化）
- ExecutionEngine / Broker の追加テストと e2e シナリオ（paper_trading の振る舞い検証）
- 安全性向上のための更なるガード（kill/stop フラグの運用改善、PID 管理）

-----------------------------------------------------------------------------
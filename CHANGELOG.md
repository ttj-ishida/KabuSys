# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース。

### Added
- 基本パッケージ情報を追加
  - src/kabusys/__init__.py にバージョン情報 (__version__ = 0.1.0)。

- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッド起動によるセッション実行、停止フラグ（data/stop_requested.flag）検知による安全停止、実行 PID 管理（data/execution.pid）を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番 sqlite_path を使用し、duckdb も併用。停止フラグ検知でループ終了。

- 設定・環境関連
  - config.py: 環境変数・設定管理モジュールを追加。  
    - .env/.env.local の自動読み込み（プロジェクトルート検出ロジックを含む）。  
    - .env パースの堅牢化（export プレフィックス、クォート／エスケープ、インラインコメント取り扱い）。  
    - Settings クラスで各種設定値（DB パス、KABUSYS_ENV、ログレベル、paper_trading 関連設定、監視閾値等）をプロパティとして提供し妥当性チェックを実装。  
    - PAPER_FILL_MODE の検証、有効値制約を実装。
  - config_setup.py: 対話式 .env 設定ウィザードを追加。既存 .env 読み込み、項目ごとのプロンプト、保存機能を提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在・パース検証、live 環境向けガード等を実装。--strict オプションにより警告を失敗扱いにできる。

- ロギング・運用ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定、ログディレクトリ自動作成・フォールバック処理、ログレベル解決ロジックを実装。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。  
    - Windows と POSIX（Linux/Mac 等）の差を吸収する実装。set_process_priority("high"|"normal"|"low")、set_cpu_affinity() を提供。権限不足などの失敗は警告として扱う。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）を追加。スコア降順ソート、スコアが全て 0 の場合のフォールバック等を実装。
  - portfolio/risk_adjustment.py: セクター集中上限適用とレジーム乗数（apply_sector_cap, calc_regime_multiplier）を追加。既存ポジションに対するセクター別エクスポージャー計算やレジームに基づく資金乗数を実装。
  - portfolio/position_sizing.py: 株数決定ロジック（calc_position_sizes）を追加。  
    - risk_based / equal / score の割当方式をサポート。  
    - 単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングと残余処理を実装。  
    - aggregate cap（利用可能現金を超えた場合のスケールダウン）や per-stock 上限処理を含む。

- 研究・ファクター計算
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム、MA、ATR、流動性などの計算を設計）。DuckDB 接続を受け prices_daily / raw_financials を参照する方針を反映。モジュールは計算対象日ベースで結果を返す設計（calc_momentum 等の実装が開始）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。  
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計し、Pass/Fail 判定を行う。  
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義しレポート出力。

- モニタリング DB ユーティリティ
  - monitoring/monitoring_db.py へ init_monitoring_db を使用するコード参照（run_* スクリプトで初期化を行い、監視テーブル存在を保証）。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- なし。

Notes:
- 起動スクリプトはすべて設定やファイルパスを環境変数経由で上書き可能にしており、開発・ペーパートレード・本番を想定した動作分離が行われています。
- この CHANGELOG はソースコードから推定して作成しています。実際のリリースノートに反映する際は、実装済みの細部（未完成の関数や将来的な CLI オプション等）を確認の上、適宜修正してください。
# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-21

初期公開リリース。

### Added
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度を上げ、スレッドでエンジンを実行、停止フラグ（data/stop_requested.flag）を監視して安全に停止する仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番用の sqlite_path を常に使用する挙動。
- 設定管理
  - config.py: 環境変数/.env の自動読み込み機能を追加（.env, .env.local の読み込み順、OS 環境変数の保護）。プロジェクトルート検出ロジック（.git または pyproject.toml）を実装。Settings クラスを提供して環境設定を型付きに取得可能に。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（シークレットマスキング・デフォルト・選択肢対応）。.env の読み書きロジックを実装。
  - validate_config.py: 起動前に .env や config/*.yaml の設定を検証する CLI を追加。--strict オプションで警告を FAIL 扱いにできる。PyYAML が無い場合のフォールバック警告を実装。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。ログディレクトリの自動作成と失敗時のフォールバックを実装。
  - utils/process_priority.py: psutil を使って Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定を追加。プラットフォーム非対応時や権限不足時は安全にスキップし警告を出力。
- データベース連携
  - duckdb と sqlite3 を併用するアーキテクチャを導入（分析用に DuckDB、監視/履歴に SQLite を使用）。
  - monitoring.monitoring_db.init_monitoring_db の呼び出しで監視用テーブルの初期化を保証（冪等）。
- Execution 周りの構成要素（参照実装）
  - run_execution から組み立てるコンポーネントのインターフェース利用を追加（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine 等）。RiskManager のデフォルト RiskConfig 値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）を設定し、初期化時に broker.get_available_cash() を初期ポートフォリオ値として使用。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を解析し、稼働率（uptime）、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出するレポートツールを追加。閾値を元に PASS/FAIL 判定を行う。コマンドライン引数で日付範囲や DB パス指定が可能。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を追加。スコアが全て 0 の場合のフォールバック動作を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。未知レジームは警告を出してフォールバック。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元（lot_size）丸め、per-stock 上限・aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差に基づく追加配分ロジックを実装。
  - portfolio/__init__.py で公開 API を整理。
- 研究用ファクター計算（初期実装の骨組み）
  - research/factor_research.py: DuckDB 接続を受け取りモメンタム等のファクターを計算する設計を追加。モメンタム計算（calc_momentum）の関数スケルトンと定数を定義（1M/3M/6M リターン、MA200 乖離など）。（注: 実装は一部未完。）
- パッケージ情報
  - __init__.py にパッケージバージョン __version__ = "0.1.0" を追加。

### Changed
- .env 読み込みの振る舞いを明確化
  - 自動読み込みはデフォルトで有効。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env.local は .env の上書きとして優先的に読み込む（ただし OS 環境変数は保護）。
  - .env のパーサは export プレフィックス、クォート（エスケープ対応）、インラインコメントの扱いをサポート。
- ログ出力
  - コンソール出力は stdout を利用（stderr ではない） — cron/スケジューラとのリダイレクト運用を考慮。
- DB 接続の方針
  - 監視（monitoring）は環境にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用する仕様を明示。
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離。

### Fixed
- MONITOR_POLL_INTERVAL の取り扱いを強化
  - 環境変数を整数にパースし、1 未満の値や不正な値はデフォルト値（60 秒）にフォールバックして警告を出力するように修正。time.sleep に渡す不正値を防止。
- process_priority の堅牢性向上
  - 未対応 OS や権限不足時に例外で落ちないよう捕捉し、警告ログで処理を継続するように修正。
- 各モジュールでのリソースクローズを確実化
  - run_monitoring / run_execution で各 DB コネクション（sqlite / duckdb）を finally ブロックでクローズするように修正し、リソースリークを防止。

### Security
- .env を生成する config_setup.py の出力に対し「.env を決して Git にコミットしない」旨の注意書きを追加。

### Notes / Known limitations
- research/factor_research.py の calc_momentum 関数以下は未完の箇所が残っており、実データでの完全なファクター計算は今後の実装が必要です。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別単元対応（stocks マスタ参照）を想定した拡張予定がコメントで残されています。
- apply_sector_cap は price_map に 0.0（価格欠損）が入る場合に過少見積りとなる可能性がある旨の TODO コメントあり。フォールバック価格の導入が検討課題。
- validate_config の YAML 検証は PyYAML に依存。未インストール時はパース検証をスキップするが警告を出す。

---

今後の改善候補（抜粋）:
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の算出）とユニットテスト追加。
- ExecutionEngine / BrokerClient のモック群と統合テストによるペーパートレード検証の自動化。
- 各 CLI に対するユニットテスト・E2E テストの整備。
- ログや DB 初期化のエラーに対する監視アラート（LINE 通知連携など）の実装強化。
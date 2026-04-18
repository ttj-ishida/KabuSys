CHANGELOG
=========

すべての変更は Keep a Changelog の方針に従って記載しています。
リリース日: 2026-04-18

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-04-18
-------------------

Added
- プロジェクト初回公開（バージョン 0.1.0）。
- 起動スクリプト:
  - run_execution.py — ExecutionEngine 起動用。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db をデフォルト）と MockBrokerClient を利用する動作をサポート。スレッドでエンジンを起動し、data/stop_requested.flag による外部停止をサポート。プロセス優先度（high）設定、PID ファイル指定をサポート。
  - run_monitoring.py — SystemMonitor ポーリングループ起動用。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用し、停止フラグ file の検出でループを終了。
- 設定管理:
  - config.py — 環境変数/.env 読み込みロジックと Settings クラスを実装。プロジェクトルート検出（.git または pyproject.toml による）を行い、自動で .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。.env のパースでは export 形式、クォート・エスケープ、インラインコメント等に対応。各種設定プロパティ（DBパス、PIDパス、Kill Switch、閾値、PAPER_FILL_MODE の有効値チェック等）を提供。
- 設定支援ツール:
  - config_setup.py — 対話式の .env ウィザード。デフォルト値、シークレット項目マスク表示、.env の読み書きを行う。
  - validate_config.py — 起動前の設定検証 CLI。必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードなどを実行。--strict モードで警告も失敗扱いに可能。
- ポートフォリオ構築（純粋関数群: DB 参照なし）:
  - portfolio.portfolio_builder: select_candidates（スコア降順で候補選別）、calc_equal_weights（等分配）、calc_score_weights（スコア正規化、全スコアが 0 の場合は等分配にフォールバック）。
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中上限の適用、売却予定銘柄をエクスポージャー計算から除外）、calc_regime_multiplier（市場レジームに基づく投下資金乗数。bull/neutral/bear のマップ、未知レジームは警告後にフォールバック 1.0）。
  - portfolio.position_sizing: calc_position_sizes（等配分/スコア/リスクベースの発注株数決定、単元株丸め、per-stock と aggregate の上限、cost_buffer による保守的見積り、available_cash に対するスケーリング処理）。
- ユーティリティ:
  - utils/logging_setup.py — 統一ログ設定ユーティリティ。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を root ロガーに設定。ログディレクトリ自動作成、既存ハンドラのクリーンアップ、ログレベル解決順（引数 > 環境変数 > デフォルト）を実装。ファイル出力に失敗してもコンソール出力は継続。
  - utils/process_priority.py — Windows と POSIX の差分を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定（最初 N コアに固定）。権限不足や未対応プラットフォームは警告してスキップ。
- 監視関連:
  - monitoring モジュールに対して起動スクリプトからの DB 初期化呼び出し（init_monitoring_db）を実装（監視テーブルが存在することを保証し冪等性を確保）。
- 実行/リスク管理のデフォルト設定:
  - Execution 側の依存組み立てで OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を構成。RiskManager のデフォルト RiskConfig 値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値を broker.get_available_cash() から取得して設定。
- データ分析 / 研究:
  - research.factor_research.py — ファクター計算モジュール（Momentum/Value/Volatility/Liquidity）を計画・実装。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを用いて計算する設計（このコミット内ではモメンタム計算の骨子を含む）。
- ツール:
  - tools.paper_verification_report.py — Paper Trading 用検証レポート生成 CLI。指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等を算出し、閾値に基づく PASS/FAIL を出力。デフォルト閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）を定義。DB パスは環境変数 PAPER_TRADING_SQLITE_PATH や --db オプションで指定可能。
- パッケージ公開情報:
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- N/A（初回リリースのため既存からの変更はなし）。

Fixed
- N/A（初回リリースのため既存バグ修正はなし）。

Deprecated
- N/A。

Removed
- N/A。

Security
- N/A。

Notes / 動作上の重要な点
- .env 自動ロード:
  - 起動時にプロジェクトルートが検出できる場合、.env（既存 OS 環境変数を上書きしない）→ .env.local（OS 環境変数を保護しつつ上書き）を自動的にロードする。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- PAPER/TRADING 分離:
  - 実行エンジンは KABUSYS_ENV に応じて本番 DB とペーパートレード用 DB を分離して使用。ペーパートレードでは MockBrokerClient（BrokerClientFactory による生成）を利用して発注や約定の振る舞いを模擬する。
- 監視用 DB:
  - run_monitoring は KABUSYS_ENV にかかわらず sqlite_path（通常は data/monitoring.db）を使用して監視データを記録する設計。
- プロセス制御:
  - run_execution/run_monitoring ともに data/stop_requested.flag による外部停止をサポート。実行エンジンは PID ファイルを扱い、外部停止時に安全に停止するための処理を備える。
- ロギング:
  - スクリプトは共通の setup_logging を用いてログを整えます。ログディレクトリ作成に失敗しても stdout へのログは継続されます。
- 互換性:
  - process_priority, cpu_affinity の操作は権限やプラットフォームに依存するため、失敗時は警告ログを出して処理を継続します。

今後の予定（例）
- factor_research の各ファクター計算（Momentum の実装完遂、Value/Volatility/Liquidity の SQL 実装）を完成させる。
- strategy/engine 側の統合テスト、Broker クライアントの詳細な Mock モデルの追加。
- 単体テスト（ユニットテスト）と CI の整備。

----------------------------------------
（この CHANGELOG はコードベースの内容から推測して作成しています。）
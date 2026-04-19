CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
形式は「Keep a Changelog」に従います（日本語）。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
------------------

Added
- 基本アーキテクチャと初期機能を実装し、0.1.0 を公開。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを生成。スレッドで engine.run_session をデーモン実行し、 data/stop_requested.flag による停止検知を実装。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立てる。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入し、initial_portfolio_value に broker.get_available_cash() を使用。
- 監視スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視データは本番 DB を参照）。
    - data/stop_requested.flag による停止検知、KeyboardInterrupt による終了処理を実装。
- 設定・環境管理
  - config.py
    - Settings クラスを導入し、環境変数から各種設定（J-Quants, kabu API, DB パス, PID パス, 監視閾値, KABUSYS_ENV 等）を取得する API を提供。
    - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。.env と .env.local の優先順位処理、OS 環境変数を保護する仕組みを導入。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path（ペーパートレード用 DB）の指定をサポート。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を追加。シークレット入力や選択肢表示、既存 .env の読み込みに対応。
  - validate_config.py
    - 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ確認、config/*.yaml の存在チェック（PyYAML がインストールされていればパース検証）等を実装。
    - --strict モードで警告を FAIL 扱いにできる。KABUSYS_ENV=live 時の追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決順をサポートし、ディレクトリ作成失敗時はファイル出力を安全にスキップ。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度の設定を行うユーティリティを追加。set_cpu_affinity による CPU ピン留め機能も提供。権限不足や未サポート OS での失敗は警告でスキップ。
- ポートフォリオ構成モジュール
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank によるタイブレーク）、等ウェイト / スコア加重の重み計算を提供。スコア全てが 0 の場合は等金額配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別時価を算出し、上限を超えるセクターの新規候補を除外するロジックを導入（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear をサポート、未知の場合はフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジックを実装。allocation_method="risk_based" と "equal"/"score" をサポート。
    - 単元株丸め（lot_size）、1 銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer（手数料・スリッページ見積）を実装。スケーリング後の残余を fractional remainder によって再配分するロジックを実装。
- データ解析・ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づいて PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）をサポートし、P95 計算ユーティリティを実装。
- 研究モジュール（ファクター計算）
  - research/factor_research.py
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity などの定量ファクター計算インターフェース設計を追加。モメンタム計算 calc_momentum の骨格（仕様、定数）を実装（実装途中でファイル末尾が未完）。
- パッケージ情報
  - __init__.py によりパッケージバージョンを 0.1.0 として定義。

Changed
- （初期リリースのため該当なし）

Fixed
- 設定読み込みやポーリング間隔の不正値に対するフォールバック処理を追加（堅牢性向上）。

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- （該当なし）

Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる懸念あり。将来的に前日終値や取得原価などをフォールバック価格として使用する検討が記載されている（TODO）。
- portfolio/position_sizing:
  - 将来的には銘柄別の lot_size を導入する設計拡張を検討中（TODO）。
- research/factor_research.py:
  - ファイル末尾が途中で切れており、calc_momentum の続き・他ファクターの実装が未完。今後の実装が必要。
- ExecutionEngine / SystemMonitor 内部の詳細実装（PID ファイルの実際の書込みや細かな shutdown 手順等）は該当ファイル外にあり、統合テストでの確認が必要。

補足
- 環境変数関連:
  - .env の自動読み込みはプロジェクトルートを検出できない場合はスキップされ、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env の読み込みロジックはシングル/ダブルクォート、export プレフィックス、インラインコメントなどの柔軟なパースに対応。
- ログ:
  - コンソールへの出力は stdout を使用（stderr ではない）ため、cron 等の出力リダイレクト運用に配慮。

----
今後のリリースでは、research モジュールの完成、Engine/Monitor の統合テスト、銘柄別単元対応、価格フォールバックロジック、monitoring/traceability（監査ログ拡充）などを優先して対応することをお勧めします。
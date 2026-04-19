Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に準拠しています。

[Unreleased]

[0.1.0] - 2026-04-11
--------------------

Added
- 初期リリース: KabuSys v0.1.0 を追加。
- 起動スクリプト / デーモン類を追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。プロジェクトルートの data/stop_requested.flag による停止制御をサポート。監視は環境にかかわらず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db デフォルト）を使用し、MockBrokerClient を利用して本番 DB と完全に分離。実行中は data/execution.pid に PID を保存（pid_file を使用）。停止フラグ（data/stop_requested.flag）でエンジンを安全に停止可能。
- 設定管理・ウィザード・検証ツールを追加
  - config.py: Settings クラスを実装。環境変数・.env/.env.local の自動読み込み（プロジェクトルートの検出による）を行い、各種設定プロパティ（DB パス、API トークン、閾値、環境判定など）を提供。PAPER_FILL_MODE 等の妥当性チェックを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加（secret マスク、選択肢、既存値の再利用、保存確認など）。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在・本番向けガードなどをチェック。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築関連モジュールを追加（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等金額配分、スコア加重配分（スコア全て 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターの扱いやフォールバック動作を明記。
  - portfolio/position_sizing.py: position sizing 実装（allocation_method による分岐: "risk_based" / "equal" / "score"）。単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer を考慮した保守的見積りを実装。資金不足時のスケーリング＆端数分配ロジックあり。
  - portfolio/__init__.py: 上記 API を公開。
- 実行エンジン周辺の基盤（参照）
  - run_execution が ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager, BrokerClientFactory 等を組み合わせて起動する流れを実装（詳細実装は各モジュールに委譲）。
  - RiskConfig にデフォルト値を設定し、起動時に broker.get_available_cash() を初期値として利用する流れを追加。
- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: コンソール（stdout）と日次ローテーションファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR の解決順を実装。ファイル出力失敗時はコンソール出力にフォールバック。
  - utils/process_priority.py: set_process_priority(level)、set_cpu_affinity(cpu_count) を追加。Windows / POSIX の差分を吸収し、安全に失敗（アクセス権限等）した場合は警告でスキップ。
- 監視・検証ツールを追加
  - monitoring.monitoring_db との連携呼び出し（init_monitoring_db）を run_monitoring/run_execution で行い、監視テーブルが存在することを保証（冪等）。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出し、閾値に基づく PASS/FAIL 判定を行う。コマンドラインで期間指定（--from/--to）と DB パス指定（--db）をサポート。P95 計算や各種 NULL/データ欠損時の扱いを考慮。
- 研究用モジュールを追加（部分実装）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨子を追加。モメンタム／MA200乖離／ATR／出来高等を計算する設計方針と定数を実装。calc_momentum() 等の関数実装を開始（未完の箇所あり、今後実装継続を想定）。
- パッケージメタ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- （初期リリースのため該当なし）

Notes / 備考
- 環境分離: paper_trading モードは paper_sqlite_path を使って本番 SQLite と明確に分離する設計。監視（SystemMonitor）は環境にかかわらず本番 sqlite_path を参照する点に注意。
- 自動 .env 読み込み: プロジェクトルートの検出により .env/.env.local を自動ロードするが、テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することでスキップ可能。
- ログ出力: デフォルトでは logs/ にファイル出力。ファイルハンドラ作成に失敗した場合でもコンソール出力で情報を失わないよう設計。
- PID / Stop フラグ: 実行系は PID ファイル・停止フラグ（data/stop_requested.flag）を使って外部からの制御をサポート。
- TODO / 留意点: portfolio/risk_adjustment.apply_sector_cap は price_map の欠損（0.0）時にエクスポージャーが過少見積りされる可能性がある旨の注釈があり、将来的にフォールバック価格の導入を検討するコメントが残されている。research/factor_research.py は実装途中の箇所があり、完全なファクター群の出力には追加実装が必要。

ファイル一覧（主な追加）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/portfolio/portfolio_builder.py
- src/kabusys/portfolio/risk_adjustment.py
- src/kabusys/portfolio/position_sizing.py
- src/kabusys/portfolio/__init__.py
- src/kabusys/utils/logging_setup.py
- src/kabusys/utils/process_priority.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py

今後の提案（参考）
- research/factor_research の未完箇所の実装完了とユニットテスト追加。
- ExecutionEngine / Broker 周りのエンドツーエンドテスト（paper_trading モードの検証を含む）。
- ログローテーション設定やディスク使用量監視の追加（長期運用向け）。
- portfolio モジュールの詳細ユニットテストと境界ケースの追加検証（cost_buffer、lot_size、price 欠損時の挙動など）。
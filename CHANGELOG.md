CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

Unreleased
----------

- （なし）

0.1.0 - 2026-04-22
-----------------

Added
- 初期リリースを追加。
- 実行スクリプト／デーモン化・監視
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。環境に応じて本番/ペーパートレードを分離して SQLite を選択、DuckDB 接続、BrokerClientFactory 経由でブローカーを生成し Engine をスレッドで実行する。停止フラグ（data/stop_requested.flag）による安全停止、PID ファイル管理をサポート。ファイル: src/kabusys/run_execution.py
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用。停止フラグ検知でループ終了。ファイル: src/kabusys/run_monitoring.py
- 環境設定 / 検証 CLI
  - config_setup.py: 対話式ウィザードで .env を作成・更新する機能を追加。既存値の読み込み、シークレットマスキング、保存確認などを実装。ファイル: src/kabusys/config_setup.py
  - validate_config.py: .env と config/*.yaml の構成検証ツールを追加。必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、YAML パースチェック、live 環境向けガードを実装。--strict オプションで警告をエラー扱いに可能。ファイル: src/kabusys/validate_config.py
- 設定管理
  - config.py: プロジェクトルート検出 (.git / pyproject.toml ベース)、.env ファイルの自動読込（.env → .env.local、OS 環境変数保護）、環境変数パーサ（クォート・エスケープ・インラインコメント処理）を実装。Settings クラスで型付きプロパティを提供（パス、閾値、Paper Trading 用設定等）。ファイル: src/kabusys/config.py
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。ファイル: src/kabusys/utils/logging_setup.py
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows の優先度クラス / POSIX の nice 値）と CPU affinity 設定を実装。例外や権限不足時は警告を出してスキップ。ファイル: src/kabusys/utils/process_priority.py
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順、タイブレークは signal_rank）と等金額 & スコア重み算出を実装。全スコアが 0 の場合は等金額にフォールバック。ファイル: src/kabusys/portfolio/portfolio_builder.py
  - portfolio/risk_adjustment.py: セクター集中制限（既存保有を考慮して新規候補をフィルタ）とレジーム乗数（bull/neutral/bear の multiplier）を実装。ファイル: src/kabusys/portfolio/risk_adjustment.py
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、1 銘柄上限・集計上限（available_cash）によるスケールダウン、cost_buffer（手数料/スリッページ見積）対応、残余配分ロジックを実装。ファイル: src/kabusys/portfolio/position_sizing.py
  - portfolio/__init__.py: 上記関数を公開 API としてエクスポート。
- 分析 / 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、P95 レイテンシなどを算出し、閾値（稼働率 99%、成立率 90% 等）に基づいて PASS/FAIL を判定。日付フィルタ、DB パスの上書きオプションをサポート。ファイル: src/kabusys/tools/paper_verification_report.py
- 研究・ファクター計算基盤
  - research/factor_research.py: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計を導入。モメンタム計算（1M/3M/6M、MA200 乖離）等の定数・方針を定義。ファイル: src/kabusys/research/factor_research.py
- パッケージ情報
  - __init__.py にてパッケージバージョンを 0.1.0 として定義。ファイル: src/kabusys/__init__.py

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Notes / Known limitations
- .env 読み込みはプロジェクトルートが検出できない場合はスキップされる（配布後の挙動を考慮）。
- process_priority の適用は OS/権限に依存し、失敗時は警告ログを出してスキップする設計。
- portfolio.position_sizing の価格欠損時の扱い（price が 0.0 の場合はスキップ）に関しては将来的にフォールバック価格導入の検討がコメントとして残されている。
- research/factor_research は DuckDB の prices_daily / raw_financials を前提とした実装設計。実データフォーマットに依存するため、実運用前のテストを推奨。

Acknowledgements
- 初期実装の各モジュールは設計ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）に基づいて構築されています。README やドキュメントを参照して実運用前に各設定（.env、config/*.yaml、DB パス）を整えてください。
CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

フォーマット:
- 「Added」「Changed」「Fixed」などのセクションで変更点を分類しています。  
- 日付はリリース日を示します。

Unreleased
----------

（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-23
-----------------

Added
- 基本アプリケーションの初期実装を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。
- 起動スクリプト / CLI を追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ実装。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクトの data/stop_requested.flag によるフラグ検知で行う。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動用スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止フラグ検知でエンジンを停止、実行はバックグラウンドスレッドで行う。
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI を提供。
    - --strict オプションで警告も失敗扱いにできる。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI。
    - デフォルト/既存値の利用、シークレット項目のマスク表示、保存テンプレートを提供。
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を解析して検証レポートを生成するユーティリティ。
    - 稼働率、注文成功率、送信率、API レイテンシ（P95 含む）などを算出し PASS/FAIL を判定する閾値を定義。
- 設定管理・自動読み込み
  - config.py: 環境変数アクセス用 Settings クラスを追加。プロジェクトルート（.git または pyproject.toml）に基づく .env 自動読み込み機構を実装。
  - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - .env パーサは export プレフィックス、引用符付き値（バックスラッシュエスケープ対応）、インラインコメント処理などに対応。
  - Settings に各種プロパティを実装（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / KABUSYS_ENV / LOG_LEVEL 等）。値検証（有効値チェック）を行う。
  - PAPER_FILL_MODE の妥当性チェック（instant|partial|never|reject）。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順にソートして上位 N を選択（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限ロジック。既存ポジションからセクター別エクスポージャを算出し、上限超過セクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告して 1.0 フォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した発注株数決定。
      - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り。
      - risk_based: risk_pct / stop_loss_pct ベースの株数算出。
      - aggregate スケール時の端数調整（lot 単位）を行い、再現性のある割当てを実施。
- DB / 分析関連
  - DuckDB 統合: duckdb 接続を受け取る実装（実行・監視スクリプト、rresearch/factor_research 等）。
  - 監視用 DB 初期化ユーティリティ init_monitoring_db の利用により監視テーブルの存在を保証（冪等処理）。
- ユーティリティ
  - utils.logging_setup.setup_logging
    - ルートロガーを一元的に設定。stdout へ StreamHandler、日次ローテーションのファイルハンドラ（logs/<app_name>.log）を追加。
    - ログディレクトリ作成失敗時はファイル出力を無効化し stdout のみで継続。
  - utils.process_priority
    - psutil を使ったプロセス優先度設定（Windows / POSIX を吸収）。
    - set_process_priority("high" 等) と set_cpu_affinity を提供。権限不足や未対応環境では警告を出してスキップ。
- 監視・停止・プロセス管理
  - PID / フラグファイルのパスをデフォルト data/ に配置（execution.pid, stop_requested.flag, kill.flag 等）。
  - 起動時にプロセス優先度を "high" に設定するパターンを採用（実行スクリプト内で最初に呼び出し）。
- リサーチ
  - research.factor_research: DuckDB の prices_daily / raw_financials を用いて Momentum / Value / Volatility / Liquidity 系のファクター計算を行う設計（Zスコア正規化等を想定）。（ファクター計算ロジックを備えたモジュールを追加）

Changed
- （初回リリースのため履歴的変更はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Notes / 実運用に関する注意
- run_monitoring は監視指標記録のために常に production 相当の sqlite_path を参照する設計になっている点に注意（意図的な隔離を行いたい場合は環境変数でパスを変更してください）。
- run_execution は paper_trading モードのとき DB を分離することで本番 DB への書き込みを防止します。ペーパートレードでの完全分離が必須な場合は KABUSYS_ENV を適切に設定してください。
- .env は機密情報を含むため Git にコミットしないことを README やテンプレートで徹底してください（config_setup にも注意書きを出力）。
- process_priority / cpu_affinity の設定は OS や権限に依存します。設定に失敗した場合は警告ログのみで処理を継続します。

Acknowledgements / Dependencies
- psutil: process 優先度 / CPU affinity の実装に利用。
- duckdb: 分析・ファクター計算・ログ集計に利用。
- PyYAML（任意）: validate_config は PyYAML があれば config/*.yaml のパース検証を行う。未インストール時は YAML 検証をスキップする旨の警告を出す。

今後の見込み（非網羅）
- factor_research の完成・最終テスト、サンプルデータ用のスクリプト追加
- 単体テストの追加（特にポートフォリオ計算／position sizing の境界条件）
- 静的型チェック・CI ワークフロー整備
- ロギング / メトリクスの強化（Prometheus / Grafana など）

---  
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は運用上の意図やドキュメント（README / リリースノート）を参考に必要に応じて調整してください。
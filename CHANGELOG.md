CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」準拠です。

v0.1.0 - 2026-04-18
------------------

Added
- パッケージ初回リリース相当の機能群を追加。
- 環境設定・読み込み
  - .env 自動読み込みを実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - 複雑な .env 行パースに対応（export プレフィックス、クォート、エスケープ、インラインコメントの扱い）。
  - Settings クラスを提供し、環境変数の取得・検証・デフォルト解決を集中管理（J-Quants / kabu API, DB パス, PAPER_TRADING, ログ設定など）。
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等の Paper Trading 固有設定をサポート。
- 対話式セットアップ / 検証ツール
  - config_setup ウィザード（python -m kabusys.config_setup）を追加し、.env の初期作成・更新を対話式で支援。
  - validate_config CLI（python -m kabusys.validate_config）を追加し、必須環境変数や config/*.yaml の存在・パース検証、--strict モードを提供。
- 実行・監視ランナー
  - run_execution（ExecutionEngine 起動スクリプト）を追加。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用 DB を使用して本番 DB と分離する動作を実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine のスレッド実行と停止フラグ監視を実装。
    - PID ファイル書き込み用 path と停止フラグ（data/stop_requested.flag）を利用した安全停止をサポート。
  - run_monitoring（SystemMonitor ポーリングループ起動スクリプト）を追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - 監視は常に production 相当の sqlite_path を使用する仕様を明記。
    - 停止フラグの検知でループを終了、例外時はログ出力して次ポーリングへ継続。
- 監視 DB 初期化 / DuckDB
  - init_monitoring_db を利用して監視用テーブルの冪等な初期化を行う呼び出しを run 系スクリプトに追加。
  - DuckDB 接続を標準で受け渡す設計（分析用データストア連携を想定）。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: stdout ストリームハンドラと日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーへ統一的に設定。LOG_DIR 作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity 設定ユーティリティも提供。アクセス権限不足等の失敗は警告でフォールバック。
- ポートフォリオ構成ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中上限を適用する apply_sector_cap、および市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装。未知レジームは警告の上でフォールバック値を採用。
  - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。lot_size（単元株）丸め、per-position 上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer による保守的コスト見積り、残差分のロット単位での追加配分ロジックを含む。
- 解析 / 検証ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs を元に稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計し、閾値に基づく PASS/FAIL 判定を実施。コマンドライン引数で期間指定や DB パス指定をサポート。
- research
  - research.factor_research モジュールの骨子を追加（モメンタム系ファクター計算の設計と定数定義）。DuckDB 上の prices_daily / raw_financials を前提とした実装方針を明記（関数 calc_momentum の導入、詳細実装は継続）。

Changed
- 実行スクリプトの挙動を明確化
  - run_execution は停止フラグ検知時に engine.stop() を呼び出してグレースフルに終了するように設計。
  - run_monitoring は monitoring がどの環境でも本番 sqlite_path を参照するという設計判断を明記（監視データの一元化）。
- .env 読み込み順序の明文化
  - OS 環境 > .env.local（上書き）> .env（未設定時にのみ設定）の優先順位を採用。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。

Fixed
- 不正な MONITOR_POLL_INTERVAL の扱いを堅牢化（非整数や <=0 の値は警告ログを出しデフォルトにフォールバック）。
- ログ設定でログディレクトリ作成失敗時にクラッシュしないようフォールバック処理を追加（stderr へ警告出力し、コンソール出力のみで継続）。

Security
- .env の生成テンプレートに「絶対に Git にコミットしないこと」を強調する注記を追加（config_setup の書き込みヘッダ）。

Notes / Operational details
- Paper Trading 環境では paper_trading 用 DB (data/paper_trading.db) を使用し、本番の monitoring DB と完全分離する設計。
- run_execution/run_monitoring はそれぞれ data ディレクトリ内の stop_requested.flag を用いた外部停止命令に対応。
- Settings クラスは KABUSYS_ENV と LOG_LEVEL の値を検証し、不正な値の場合は ValueError を投げるため、起動前に validate_config でチェックすることを推奨。
- 一部モジュール（例: research.factor_research の calc_momentum）は実装継続が示唆されており、今後のリリースで詳細な実装・テストが追加される予定。

Unreleased
- （現時点で未リリースの追加実装や改善はここに記載します。次回リリース時に移動してください。）
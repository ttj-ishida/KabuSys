CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠します。

フォーマットのルール:
- 変更は分類（Added, Changed, Fixed, …）ごとに記載しています。
- バージョンはパッケージの __version__ に合わせています。

[Unreleased]
------------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-21
-----------------

Added
- プロジェクト初回リリース。
- 基本 CLI / デーモン起動スクリプトを追加:
  - run_monitoring.py
    - SystemMonitor をポーリングで実行する監視ループ。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 停止は data/stop_requested.flag により検出。
    - KABUSYS_ENV にかかわらず監視は本番用 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine を起動するエンジン。スレッドで実行し、停止フラグで安全に終了可能。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント注入、OrderManager、RiskManager、Reconciler 等の組み立て。
- 環境設定 / 検証関連:
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - ボタン入力でシークレットのマスク表示、選択肢・デフォルトの提示、保存前の確認を行う。
  - validate_config.py
    - .env と config/*.yaml の設定不備を起動前に検出する CLI を追加。
    - --strict オプションで警告を失敗扱い（exit 1）にできる。
    - 必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、YAML パース確認（PyYAML が無ければスキップ）などを行う。
- 設定管理:
  - config.py
    - Settings クラスで環境変数をラップして一元管理。
    - プロジェクトルート自動検出による .env / .env.local の自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, SQLITE_PATH 等のプロパティ化と妥当性チェック。
    - is_live / is_paper / is_dev 等のユーティリティプロパティを追加。
- ログ / プロセス制御ユーティリティ:
  - utils/logging_setup.py
    - コンソール出力（stdout）と日次ローテートファイル出力（logs/<app>.log）をルートロガーへ設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の環境変数、引数での上書きをサポート。既存ハンドラの二重登録を防止。
  - utils/process_priority.py
    - cross-platform なプロセス優先度設定 set_process_priority(level) を追加（Windows / POSIX 切替対応、例外時は警告でスキップ）。
    - set_cpu_affinity(cpu_count) でプロセスの CPU affinity 固定機能を追加。
    - 起動スクリプトは開始直後に優先度を "high" に設定するようになっている。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選抜。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供（スコア全 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中チェックによる候補の除外ロジックを実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を提供。未知レジームはフォールバック 1.0。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数算出ロジックを実装。
    - 単元株（lot_size）丸め、単銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りをサポート。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite の集計からレポートを出力する CLI を追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出。
    - PASS/FAIL 基準値（稼働率 99%、Filled 90% など）に基づく判定を出力。
- Research（骨格実装）:
  - research/factor_research.py
    - DuckDB 接続を受け取り、モメンタム・ボラティリティ等のファクターを計算する設計（関数群の骨格と定数群を追加）。※実装の一部は継続開発対象。

Changed
- 初期リリースにつき変更履歴はありません。

Fixed
- 初期リリースにつき修正履歴はありません。

Notes / Implementation details
- run_monitoring / run_execution はそれぞれ独立した起動ポイントとして設計され、ログ設定・プロセス優先度設定を統一的に行うことで運用時の挙動を安定化しています。
- 環境変数の自動読み込みはプロジェクトルート検出に基づくため、パッケージ配布後の動作でもカレントワーキングディレクトリに依存しない設計です。
- Paper Trading は本番 DB と完全分離されるよう配慮されています（設定により上書き可能）。
- 一部モジュール（factor_research など）は設計方針と定数を含む初期実装で、今後ファクター計算ロジックの追加・テストが予定されています。

開発者注記
- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダにも警告記載）。
- 本番運用時は KABUSYS_ENV=live の設定や KILL_FLAG_CLEAR_ON_START の値に注意してください。validate_config による事前チェックを推奨します。

----- End of changelog -----
CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" と Semantic Versioning.

0.1.0 - 2026-04-19
------------------

Added
- 基本機能の初期実装を追加（初回リリース）。
- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（既定: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート（実運用／モックの切替）。
    - エンジンはデーモンスレッドで実行、停止フラグ（data/stop_requested.flag）で安全に停止可能。実行 PID ファイルを data/execution.pid に保存。
    - RiskManager / OrderManager / Reconciler 等のコンポーネント組み立てを行い、RiskConfig / EngineConfig によるパラメタ指定をサポート。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒、無効値はフォールバック）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。例外時はログ出力して次ポーリングへ継続。
    - 監視は環境にかかわらず本番 sqlite_path を使用して永続化。
- 設定管理
  - config.py: 環境変数および .env の自動読み込み機能を実装。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD に依存しない自動ロード。
    - .env のパース処理は引用符・エスケープ・インラインコメントに対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - Settings クラスで各種設定値（DB パス、API トークン、Paper モード設定、しきい値、環境種別等）をプロパティとして提供。値検証（有効な列挙値チェックなど）を実装。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 主要な環境項目を対話で入力・既存値の再利用・シークレットマスク表示・保存をサポート。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML があれば検証）。
    - --strict オプションで警告をエラー扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティを追加。
    - ログレベル解決順（引数 > LOG_LEVEL 環境変数 > デフォルト）とログディレクトリの作成失敗時のフォールバック動作を実装。
  - utils/process_priority.py:
    - set_process_priority により Windows/Linux の違いを吸収して優先度設定（high/normal/low）を提供。
    - set_cpu_affinity によりプロセスの CPU affinity を最初の N コアに固定する機能を追加（権限不足や未サポート環境では警告を出してスキップ）。
    - Windows / POSIX の差異や例外時のフォールバックを考慮した実装。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - calc_score_weights は全スコアが 0 の場合に等重配分へフォールバックして警告出力。
  - portfolio/risk_adjustment.py:
    - セクター集中上限を適用する apply_sector_cap を追加（"unknown" セクターは適用除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（未知のレジームは 1.0 にフォールバックし警告）。
  - portfolio/position_sizing.py:
    - 複数の配分方式（risk_based / equal / score）に対応した calc_position_sizes を追加。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer を用いた保守見積り、残余配分の再割当ロジック等を実装。
- 解析／検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、レイテンシ（平均・最大・P95）を算出し、閾値比較による PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 >= 99%、Fill >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を採用。
- データベース / 分析エンジン
  - DuckDB を分析用に利用（設定でパス指定可）。複数コンポーネントから duckdb 接続を受け渡す構成を採用。
  - 監視データ等は SQLite に格納。監視用テーブルの初期化ユーティリティ init_monitoring_db を使用して冪等にテーブルを確保。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Notes / Implementation details
- 環境変数の自動ロードはプロジェクトルートの検出に成功した場合のみ行われ、OS 環境変数は保護（.env の上書きから除外）される。
- ログは標準で logs/ ディレクトリに出力され、ディレクトリ作成に失敗した場合はファイル出力を行わず標準出力のみで継続する。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようと試みる（設定に失敗した場合は警告を出すだけで継続）。
- ペーパートレード向けの挙動（PAPER_FILL_MODE 等）は Settings を通じて厳密に検証し、不正値は ValueError を送出する。
- 一部モジュール（research/factor_research.py 等）はファクター計算の骨組みを実装しており、DuckDB の prices_daily / raw_financials テーブルを前提に計算を行う設計。

Acknowledgements
- 本 CHANGELOG は現行コードベースから推測して作成しています。実際のユーザー向けリリースノートとして公開する場合は、変更点・既知の制限・互換性に関する最終確認をお勧めします。
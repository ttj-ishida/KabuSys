CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に一致します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 初回公開。日本株自動売買システム「KabuSys」の基本コンポーネントを追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動フロー（ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、別スレッドで engine.run_session 実行、停止フラグ監視）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL 環境変数で間隔上書き、停止フラグ検知で終了）。
- 環境・設定関連
  - config.py: Settings クラスによる環境変数ラップ（自動 .env ロード、各種既定値と検証、paper_trading 用 DB パスなど）。
  - config_setup.py: 対話式 .env 作成ウィザード（.env の読み書き、マスク表示、保存確認）。
  - validate_config.py: 起動前検証 CLI（必須環境変数、KABUSYS_ENV 値、DB パス、config/*.yaml の存在とパース、--strict オプション）。
- ロギングと運用ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定（stdout ストリーム + 日次ローテートファイルハンドラ、LOG_DIR/LOG_LEVEL を尊重）。
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ（Windows / POSIX の差分吸収、psutil ベースで安全にフォールバック）。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等重み・スコア重み計算（calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 発注株数算出ロジック（risk_based / equal / score の配分方式、単元株丸め、aggregate cap のスケーリング、cost_buffer の考慮）。
- 監視・検証ツール
  - monitoring.monitoring_db: 監視用 DB 初期化ユーティリティ（init_monitoring_db を呼んで監視テーブルの存在を保証）。
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成（稼働率・注文成功率・送信率・レイテンシ指標、P95 計算、閾値による PASS/FAIL 判定）。PAPER_TRADING_SQLITE_PATH と --db オプションで DB 指定可。
- 研究モジュール（factor 計算）
  - research/factor_research.py: ファクター計算の骨格（モメンタム／ボラティリティ等の計算設計、DuckDB 経由で prices_daily/raw_financials を参照する方針）。（モジュール実装開始）

Changed
- 環境変数ロードの挙動を明確化
  - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD に依存しない自動 .env ロード）。
  - .env の読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env 読み込みは既存 OS 環境変数を保護するため protected set を使用し上書きを制御。
- .env パーサを強化
  - export プレフィックス対応（export KEY=val）。
  - シングル / ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理の改善。
  - クォートなし値のインラインコメント扱いをスペース直前のみとして誤解を減らす実装。
- run_monitoring の設計
  - Monitoring は KABUSYS_ENV にかかわらず（運用上の意図として）本番 sqlite_path を使用する仕様を明記。
  - MONITOR_POLL_INTERVAL のパースを厳格化（1 未満の値はデフォルトへフォールバック、ログで警告）。
- run_execution の設計
  - KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を用い paper_trading DB と本番 DB を完全分離。
  - ExecutionEngine の起動前に停止フラグをチェックし、既に停止フラグがある場合は起動せず終了する安全措置。
- ロギング設定の振る舞い
  - 既存ハンドラの二重登録を防ぐため、ルートロガーの既存ハンドラを flush/close してから再設定。
  - stdout を StreamHandler の出力先に採用（cron / Task Scheduler の運用を想定）。
- process_priority のフォールバック
  - Windows 固有定数の取得は getattr を使い安全に処理。対応外 OS の場合は警告ログを出して処理をスキップ。

Fixed
- 環境ファイル読み込みでの I/O エラーを警告として扱うようにし、処理を継続できるように改善。
- logging_setup がログディレクトリ作成に失敗した場合に stderr へ警告を出してファイルハンドラの作成をスキップするように変更（起動失敗の回避）。
- process_priority / set_cpu_affinity で権限エラー等発生時に警告ログで通知し処理を継続するよう修正。

Notes / Internal details
- データベース
  - DuckDB は分析用（duckdb_path、data/kabusys.duckdb をデフォルト）として接続。
  - SQLite は監視 / 発注履歴用（SQLITE_PATH、data/monitoring.db）、ペーパートレード時は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）を使用。
- 停止制御
  - すべての常駐プロセスはプロジェクトルート/data/stop_requested.flag（または設定によるパス）を参照して停止を検知する設計。
  - ExecutionEngine は data/execution.pid を PID 書き込み先に利用（pid_file の扱いを設定から取得）。
- Risk / Execution デフォルト値
  - RiskManager のデフォルト設定例をコード内で明示（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20, initial_portfolio_value を broker.get_available_cash() で初期化）。
- Portfolio/Position sizing の挙動
  - 単元株（lot_size）単位で切り捨て、aggregate cap 超過時はスケーリングと端数再配分を行う実装。
  - cost_buffer により手数料・スリッページ分を保守的に見積もる。
- tools/paper_verification_report の判定基準（デフォルト閾値）
  - 稼働率 (uptime) >= 99.0%
  - 注文成功率 (fill_rate) >= 90.0%
  - 送信率 (send_rate) >= 95.0%
  - P95 レイテンシ <= 200 ms
- research/factor_research.py はファクター計算の骨格（モメンタム、MA200、ATR、流動性など）を実装中。現時点では一部関数の実装が途中（ファイル末尾が途切れている断片あり）。

Deprecated
- なし

Removed
- なし

Security
- なし

Contributing
- バグ報告・プルリクエストはリポジトリの issue/PR を利用してください。環境変数や .env の取り扱いには秘密情報（API トークン等）が含まれます。.env を絶対にリポジトリにコミットしないでください（config_setup の冒頭にも同旨の注記あり）。

---- 

注: この CHANGELOG は提供されたソースコードからの推測に基づいて生成しています。実際の変更履歴（コミット履歴）に基づく正式な履歴は git のログ等を元に作成してください。
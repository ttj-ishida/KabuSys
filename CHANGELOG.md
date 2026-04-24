CHANGELOG
=========
All notable changes to this project will be documented in this file.
フォーマットは "Keep a Changelog" に準拠します。

形式:
- 変更はセクションごとに整理（Added / Changed / Fixed / Deprecated / Removed / Security）
- 各リリースはバージョンと日付を記載

Unreleased
----------
このセクションは将来の変更のために予約しています。現在認識している改善点・未実装箇所を記載します。

Added
- 複数の運用用 CLI / スクリプトを追加予定:
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL の検証・使用）。
  - run_execution: ExecutionEngine 起動スクリプト（ペーパートレード時は専用 DB を使用し MockBrokerClient を利用）。
  - tools/paper_verification_report: ペーパートレードの検証レポート生成ツール（稼働率・注文成功率・レイテンシ等を算出）。
  - validate_config: .env と config/*.yaml を起動前に検証する CLI。
  - config_setup: 対話式 .env 初期作成・更新ウィザード。
- ポートフォリオ構築モジュール群を追加:
  - portfolio_builder: シグナルの選定 (select_candidates)、等配分 / スコア加重の重み計算 (calc_equal_weights / calc_score_weights)。
  - risk_adjustment: セクター集中制限 (apply_sector_cap)、マーケットレジームに基づく乗数 (calc_regime_multiplier)。
  - position_sizing: 株数計算ロジック (calc_position_sizes) — risk_based / equal / score の配分方式、lot_size 単位への丸め、aggregate cap によるスケールダウン、cost_buffer を考慮。
- 環境設定・読み込みの改善:
  - config.py: .env 自動ロード機能（.env/.env.local の読み込み順序、OS 環境変数の保護）。
  - .env パーサを強化：export プレフィックス対応、クォート文字列内のバックスラッシュエスケープ、インラインコメント処理。
  - Settings クラス追加：環境変数をプロパティとして型付きで取得（DB パス、paper_trading 用パス、閾値、LOG_LEVEL 等）。
- ロギングとプロセス制御ユーティリティ:
  - utils/logging_setup.py: コンソール (stdout) と TimedRotatingFileHandler（日次・30日保持）を統一的に設定。LOG_DIR/LOG_LEVEL の解決順を実装し、ディレクトリ作成失敗時はファイル出力を自動でスキップするフェイルセーフあり。
  - utils/process_priority.py: プラットフォーム依存差分を吸収したプロセス優先度設定（Windows/Linux/macOS 対応）と CPU affinity 設定ユーティリティ。
- データベース関連:
  - duckdb を分析用に導入（Settings.duckdb_path を利用）。
  - monitoring 用 SQLite の初期化を行う init_monitoring_db（冪等処理を保証）。
- 監視・実行プロセスの運用向け機能:
  - stop/kill フラグ（data/stop_requested.flag, data/kill.flag）を用いた安全停止。
  - PID ファイル管理（ExecutionEngine の pid_file 指定）。
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用 DB を使用して本番 DB と分離。
- tools/paper_verification_report:
  - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出し PASS/FAIL 判定を出力。閾値を定数で定義（例: 稼働率 >= 99% など）。
- パッケージメタ:
  - __version__ = "0.1.0"

Changed
- run_monitoring / run_execution の起動フロー:
  - 両スクリプトとも起動直後に set_process_priority("high") を呼び出すようにして、実行時の優先度を高く設定する運用方針を採用。
  - run_monitoring は KABUSYS_ENV に関わらず監視用に production 相当の sqlite_path を使う旨を明示。
  - run_execution は paper_trading モードなら専用の paper_sqlite_path を選択するように変更。
- ロギング:
  - StreamHandler は stdout を使用（stderr ではない） — cron/Task Scheduler などで stdout/stderr を一括リダイレクトする運用に配慮。

Fixed
- 環境変数からポーリング間隔を取得する際の堅牢性向上:
  - MONITOR_POLL_INTERVAL の値が不正（非整数や 0 以下）だった場合に警告を出し、デフォルト（60 秒）にフォールバックするように改善。
- .env 読み込み時の例外ハンドリングを追加:
  - ファイルオープン失敗時に warnings.warn を出すようにして自動ロードの失敗を無視可能にした。
- ログディレクトリ作成失敗時のフォールバック:
  - ディレクトリ作成に失敗してもコンソール出力のみで継続するように変更（ファイルハンドラ生成時に例外処理を追加）。
- psutil を用いた優先度設定での例外を捕捉して警告ログを出力するようにした（権限不足や未対応 OS でも起動継続可能）。

Deprecated
- なし

Removed
- なし

Security
- なし

[0.1.0] - 2026-04-24
---------------------
初回リリース (ベースライン機能群)

Added
- プロジェクト初期実装をリリース:
  - 実行・監視の起動スクリプト: run_execution.py, run_monitoring.py
  - 環境設定ユーティリティ: config_setup.py（対話式ウィザード）
  - 設定検証ツール: validate_config.py
  - ペーパートレード検証レポート: tools/paper_verification_report.py
  - ポートフォリオ構築ライブラリ: kabusys.portfolio (portfolio_builder, risk_adjustment, position_sizing)
  - 解析向け研究モジュール（骨格）: research/factor_research.py（モメンタム等の計算ユーティリティを実装中）
  - 共通ユーティリティ: utils/logging_setup.py, utils/process_priority.py
  - 設定読み込み: config.py (.env 自動ロード、Settings クラス)
  - モニタリング DB 初期化ユーティリティを利用する init_monitoring_db を各スクリプトで呼び出す
- 多くの CLI とユーティリティで堅牢なエラーハンドリングを追加（例: DB 接続時の finally でのクローズ処理、スレッド停止の整合性確保など）。

Changed
- なし（初回公開）

Fixed
- なし（初回公開）

Notes / Known issues
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少に見積もられる可能性があり、将来的に前日終値などのフォールバックを追加することを検討（TODO コメントあり）。
- research/factor_research.py:
  - ファイル末尾が切れている / 実装途中の関数あり（calc_momentum の実装が途中で終端）。今後のプルリクエストで完成予定。
- コンフィグ検証:
  - PyYAML 未インストール時は YAML 検証をスキップし、警告を出す仕様（validate_config）。プロジェクトの CI では PyYAML を依存に含めることを推奨。

参考: 運用上の挙動
- run_execution はデフォルトで thread を用いて ExecutionEngine をデーモンとして起動し、data/stop_requested.flag を検知したら engine.stop() を呼び出して安全停止を試みる。
- run_monitoring は継続的に monitor.check_once() を呼び、例外はキャッチして次ポーリングに備える（ロバストな長期監視を想定）。
- PAPER_TRADING_SQLITE_PATH を利用することで paper_trading 環境が本番データベースと完全に分離される設計。

今後の改善予定 (短期)
- research/factor_research の完成（ファクター計算の SQL 最適化とテスト追加）
- セクター露出計算における価格フォールバックの実装
- ロギング設定のユニットテスト整備および CI でのローテーション動作確認
- モジュール間の型ヒント整備と mypy 等の静的解析ルール導入

----------------------------------------
この CHANGELOG はコードベースの内容から推測して作成されています。実際のコミット履歴に基づく正確な変更履歴は各コミットメッセージをご確認ください。
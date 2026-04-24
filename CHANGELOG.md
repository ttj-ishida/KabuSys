CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（重要な変更のみを記載）

Unreleased
----------

- （なし）

0.1.0 - 2026-04-24
-----------------

Added
- 基本機能の初期実装を追加。
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。
- 実行用エントリスクリプトを追加。
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV=paper_trading 時にはペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。起動時にプロセス優先度を設定し、停止フラグ（data/stop_requested.flag）検知で安全停止する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用し、停止フラグでループを終了する。
- 設定管理と補助 CLI を追加。
  - config.py: .env 自動読込、各種環境変数プロパティ（DB パス、API トークン、Paper Trading の挙動等）とバリデーションを実装。PAPER_FILL_MODE 等の厳密な値チェックを導入。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を実装（シークレットのマスク表示、デフォルト・選択肢サポート、保存前確認など）。
  - validate_config.py: 起動前の設定検証 CLI を実装。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML が無ければ警告）や本番環境固有のガードをチェック。--strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセスユーティリティを追加。
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを実装。コンソール(stdout)出力と日次ローテートファイル出力を設定。LOG_DIR/LOG_LEVEL の解決順や、ログディレクトリ作成失敗時のフォールバックをサポート。
  - utils/process_priority.py: Windows/Linux/macOS を吸収するプロセス優先度設定および CPU affinity 設定ユーティリティを実装。アクセス権限関連の例外は警告にフォールバック。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし）。
  - portfolio/portfolio_builder.py: シグナルの候補選定と等金額・スコア重み付け関数を実装。
  - portfolio/position_sizing.py: position sizing（risk_based / equal / score）ロジックを実装。単元株丸め、max_position_pct、aggregate cap（available_cash によるスケーリング）、手数料・スリッページ想定の cost_buffer を考慮。
  - portfolio/risk_adjustment.py: セクター集中上限適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/__init__.py: 上記 API を公開。
- 解析/検証ツールを追加。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを実装。稼働率、注文成功率／送信率、リスク却下数、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで DB 指定が可能。P95 計算ユーティリティや閾値（デフォルト）を定義。
- リサーチ用の骨組みを追加。
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの設計とモメンタム系の計算用定数群を実装（calc_momentum の骨組み含む、以降の実装が続く想定）。
- DB 初期化ユーティリティ（監視用）を導入。
  - monitoring/monitoring_db.py（参照され使用）を通じて起動時に監視用テーブルの存在を保証する init_monitoring_db 呼び出しを追加（冪等）。

Changed
- （初期リリースのため履歴無し）

Fixed
- 環境変数パースの改善。
  - config._parse_env_line: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、クォート無しのコメント取り扱いをサポートし、より柔軟に .env 行を解釈するように改善。
- MONITOR_POLL_INTERVAL の異常値ハンドリング。
  - run_monitoring._get_poll_interval: 0 以下や非整数が設定された場合にデフォルト（60 秒）へフォールバックし、警告ログを出力するように改良（time.sleep に渡す不正値による例外回避）。
- ログ出力の扱いを安定化。
  - utils/logging_setup.setup_logging: 既存ハンドラを安全に flush/close してから再設定するようにし、二重登録を防止。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続する。

Security
- .env 取り扱いに関する注意喚起を CLI に追加。
  - config_setup._write_env のヘッダに ".env は絶対に Git にコミットしないこと" を明記。
- validate_config: 本番環境（KABUSYS_ENV=live）で LINE 通知周りや KILL_FLAG_CLEAR_ON_START の設定に注意を促す警告を追加。

Notes / Migration
- .env の自動ロードはデフォルトで有効。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env の読み込み順は OS 環境 > .env.local > .env（.env.local は既存値を上書き）。既存の OS 環境変数は保護されます。
- Paper Trading モードではデータ永続化先が paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に分離されているため、本番監視 DB（SQLITE_PATH）とは独立して運用できます。
- run_execution/run_monitoring はプロセス優先度を起動時に "high" に設定しようと試みます（権限不足時は警告でフォールバック）。
- logging 設定は stdout を主要なストリームに使用します（Task Scheduler/cron 等でのリダイレクトを想定）。

Deprecated
- （なし）

Removed
- （なし）

For more details
- 各機能の実装は src/kabusys 以下の該当ファイルを参照してください。
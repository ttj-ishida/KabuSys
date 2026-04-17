CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース: KabuSys Python パッケージを追加。
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
- 起動スクリプト:
  - run_execution.py: 実行エンジン（ExecutionEngine）起動スクリプトを追加。プロセス優先度を上げ、SQLite/DuckDB に接続して Engine をスレッドで実行。停止フラグ(stop_requested.flag)と PID ファイル(data/execution.pid)を扱う。paper_trading 環境用に専用 SQLite (data/paper_trading.db) を使用し、本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境変数に関わらず本番 sqlite_path を使用して監視テーブルを初期化。
- 設定管理:
  - config.py: 環境変数/.env 読み込みロジックを実装。プロジェクトルート自動検出(.git または pyproject.toml)、.env/.env.local の読み込み順序と上書きポリシー（OS 環境変数保護）をサポート。多くの設定プロパティを提供（DB パス、API トークン、監視閾値など）。
  - config_setup.py: 対話式 .env ウィザードを実装。デフォルト値・選択肢・シークレット入力に対応し、.env テンプレートの書き出しを行う。
  - validate_config.py: 起動前設定検証 CLI を実装。必須環境変数や config/*.yaml の存在・パースチェックを行い、--strict モードで警告を FAIL 扱いにできる。
- ユーティリティ:
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを実装。Windows / POSIX(nice) に対応。CPU アフィニティ設定関数も提供。失敗時は警告を出して安全にスキップ。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: 候補選定（スコア順）、等重配分、スコア加重配分を実装。スコアが全て 0 の場合に等重へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限ロジック（apply_sector_cap）と市場レジームに依る乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: position-sizing ロジックを実装（risk_based / equal / score）。単元株(lot_size)丸め、1銘柄上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer を考慮したスケーリングと端数扱いの再配分を実装。
- リサーチ:
  - research/factor_research.py: DuckDB を用いるファクター計算モジュール（モメンタム、ボラティリティ等）を実装。prices_daily / raw_financials テーブル参照で各種指標を算出。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ(P95) 等を SQLite から集計して PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数／--db オプション対応。
- DB 初期化:
  - monitoring_db.init_monitoring_db を利用して監視テーブルの存在を保証する仕組みを起動時に追加（冪等）。

Changed
- ログ・メッセージの追加/改善:
  - 起動時に KABUSYS_ENV をログ出力。ポーリング間隔や停止フラグ検出時のログを追加。
  - 設定検証ツールで INFO/WARNING/ERROR を整備し、PyYAML 未導入時の挙動を警告。
- 環境読み込み挙動:
  - .env 読み込みは OS 環境変数を保護（protected set）しつつ .env → .env.local の順で適切に適用。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。

Fixed
- 堅牢性改善:
  - .env パース処理(_parse_env_line)でクォート／エスケープシーケンスやインラインコメントの扱いを適切に処理するように実装。不正な行を無視して安全に読み込む。
  - run_monitoring のポーリング間隔取得で不正な値を検出した場合にデフォルトへフォールバックし警告を出力（time.sleep に渡す不正値対策）。
  - process_priority 設定時にアクセス拒否や未実装の API をキャッチして警告し、安全に続行するよう修正。

Documentation / CLI
- validate_config と config_setup にコマンドラインインターフェースを追加。使い方はそれぞれ python -m kabusys.validate_config / python -m kabusys.config_setup。
- tools/paper_verification_report はコマンドライン引数 (--from/--to/--db) をサポートし、レポート期間フィルタが可能。

Configuration / Environment
- 新たに利用される主な環境変数を明示:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, KILL_FLAG_CLEAR_ON_START, KILL_FLAG_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_DISABLE_AUTO_ENV_LOAD
- PAPER_FILL_MODE に対する妥当性チェックを追加（instant/partial/never/reject のみ有効）。

Notes / Behavioural highlights
- 監視プロセスは環境に関係なく本番の sqlite_path を用いて監視テーブルを操作する設計（監視データの混在防止）。
- 実行エンジンは paper_trading 環境で MockBrokerClient（BrokerClientFactory にて生成）を利用し、paper_trading 用 DB に記録して本番 DB と分離。
- Execution 側の RiskManager 初期設定値をコード内で与え、初期ポートフォリオ値はブローカーから取得して設定する（broker.get_available_cash() を利用）。

Security
- .env は生成メッセージで Git にコミットしないよう明示（config_setup の出力メッセージ）。

Acknowledgements / Misc
- 内部関数は可能な限り例外をキャッチしてログ出力しつつプロセスを継続する方針を採用。各モジュールはデータ欠損時に None や N/A を返すなどフォールバックを備える。

今後の予定（未実装・改善候補）
- position_sizing: 銘柄別の lot_size をマスターから取得できるよう拡張（TODO コメントあり）。
- apply_sector_cap: 価格欠損時のフォールバック値（前日終値など）による改善。
- research/factor_research: 追加ファクターや高速化、DuckDB クエリ最適化。
- より詳細なドキュメント・サンプル .env ファイルの整備。

以上。
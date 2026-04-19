Keep a Changelog 準拠 — 重要な変更のみ記載します。  
この CHANGELOG はコードベース（初期リリース相当）から推測して作成しています。

Unreleased
----------

- （現在なし）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本アプリケーション初期実装を追加。
  - パッケージ情報: kabusys/__init__.py にバージョン 0.1.0 を追加。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく production の sqlite_path を使用。停止フラグ（data/stop_requested.flag）検知で安全にループ終了。
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、MockBroker を利用して本番 DB と完全に分離。停止フラグと PID ファイル管理をサポート。
- 設定管理 / ユーティリティ
  - config.py: 環境変数（.env / .env.local / OS 環境）を自動読み込みする仕組みを実装。プロジェクトルートの検出ロジック（.git / pyproject.toml）を導入。複雑な .env のパース（export プレフィックス、クォート処理、インラインコメント扱い）をサポート。Settings クラスで各種設定値・検証（env, log level, DB パス, paper 設定 等）を提供。
  - config_setup.py: 対話式 .env 作成ウィザードを実装。テンプレート項目（J-Quants / kabu API / DB パス / LINE / log level / Kill Switch 等）を対話で設定し .env を書き込む。
  - validate_config.py: 起動前検証 CLI を実装。.env の必須キー未設定検出、KABUSYS_ENV チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML 未インストール時は警告）などを行う。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全て 0 の場合は等分配へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック（1.0）して警告を出す。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装（allocation_method: "risk_based", "equal", "score" をサポート）。単元株（lot_size）で丸め、per-stock 上限・aggregate 上限（available_cash）を適用、コストバッファを考慮したスケーリングと端数配分ロジックを実装。
  - portfolio/__init__.py で上記関数を公開。
- 実行系ユーティリティ
  - utils/logging_setup.py: 共通ロギングセットアップを実装。stdout 出力の StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows/Linux（POSIX）差分を吸収したプロセス優先度設定と CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポートを実装。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出し、閾値に基づく PASS/FAIL 判定を出力。コマンドライン引数で期間（--from / --to）や DB パス（--db）を指定可能。閾値定義と P95 計算ユーティリティを含む。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_* から呼び出して監視用テーブルの存在を保証（冪等）。
- データ分析（研究用）
  - research/factor_research.py: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）のスケルトンを追加。DuckDB を利用して prices_daily / raw_financials に基づくファクター計算を想定。設計方針や定数が定義されている（ただし一部実装は未完：calc_momentum の途中でファイルが切れている）。

Changed
- 監視・実行起動時のプロセス優先度を最初に high に設定するように変更（set_process_priority("high") を各 main で呼び出す）。
- run_monitoring と run_execution で DuckDB と SQLite 両方を使う設計を導入（分析用に DuckDB、運用ログに SQLite）。
- .env 自動読み込みの挙動: デフォルトで有効。テストや特殊用途向けに KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Fixed / Robustness
- .env パーサーの強化: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
- ロギングセットアップでログディレクトリ作成に失敗しても起動継続するようにフォールバック処理を追加。
- process_priority, set_cpu_affinity: 権限不足や未対応環境での例外をキャッチして警告ログを出すことで起動失敗を防止。
- run_monitoring のポーリング間隔取得で不正値（0 以下や非数）を検出するとデフォルトにフォールバックして警告を出す。

Notes / Known issues
- research/factor_research.py の calc_momentum など、一部ファクション実装が途中（ファイル切断）になっているため、研究用ファクター計算はまだ未完成。実用前に実装の完成と追加テストが必要。
- position_sizing と apply_sector_cap の一部に TODO コメントあり（価格欠損時のフォールバック、銘柄別単元対応等）。将来的な拡張点として注記。
- monitoring は「環境にかかわらず」production の sqlite_path を使用する設計になっているため、paper_trading 環境で監視ログを分離したい場合は運用上の注意が必要。
- set_process_priority / set_cpu_affinity は権限（root / 管理者）が必要な操作になることがあり、実行環境に応じて動作しない場合がある（ログに詳細を出力してスキップ）。

Security
- センシティブな値（API トークン等）は .env にプレーンテキストで保存される設計。 .env は絶対に Git にコミットしない旨をドキュメントに明記（config_setup のヘッダに記載）。

CLI / エントリポイント
- validate_config: python -m kabusys.validate_config
- config_setup: python -m kabusys.config_setup
- paper_verification_report: python -m kabusys.tools.paper_verification_report
- run scripts: python -m kabusys.run_monitoring / python -m kabusys.run_execution

その他
- 環境変数 / 設定項目（主なもの）
  - KABUSYS_ENV (development | paper_trading | live)
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - PAPER_FILL_MODE (instant | partial | never | reject)
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔, 秒)
  - LOG_LEVEL, LOG_DIR
  - KILL_FLAG_CLEAR_ON_START, KILL_FLAG_PATH, PID_FILE_PATH

References
- この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴や意図と差異がある場合があります。
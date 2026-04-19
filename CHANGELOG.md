# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- プロジェクト初期リリース相当の主要コンポーネントを追加しました。
  - 実行・監視用エントリポイントスクリプト
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し、paper_trading 用 DB（data/paper_trading.db など）と本番 DB を分離して動作します。起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）に対応します。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用します。
  - 設定・検証関連 CLI
    - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（python -m kabusys.config_setup）。複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL など）をサポートします。
    - validate_config.py: .env と config/*.yaml を事前検証する CLI を追加（python -m kabusys.validate_config）。`--strict` モードで警告も失敗扱いにできます。
  - 環境/設定管理
    - config.py: Settings クラスを追加。.env 自動読み込み（.env → .env.local、OS 環境変数保護ルールあり）や各種環境変数の取得・検証ロジック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。複雑な .env の行解析（export 形式、クォート内のエスケープ、インラインコメント等）に対応しています。
  - ログ・プロセスユーティリティ
    - utils/logging_setup.py: ルートロガーの統一設定ユーティリティを追加。コンソール（stdout）と日次ローテートファイル（TimedRotatingFileHandler）を設定。ログディレクトリは引数 / 環境変数 LOG_DIR / デフォルト `logs/` の順で解決。
    - utils/process_priority.py: psutil ベースで Windows/Linux（および一部 POSIX）に対応するプロセス優先度設定と CPU affinity 設定ユーティリティを追加。set_process_priority("high"|"normal"|"low"), set_cpu_affinity を提供。
  - ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
    - portfolio/portfolio_builder.py: select_candidates, calc_equal_weights, calc_score_weights を実装。スコア降順ソートやスコアが全て 0 の場合のフォールバック対応を含む。
    - portfolio/risk_adjustment.py: apply_sector_cap（セクター集中の除外ロジック）、calc_regime_multiplier（市場レジームに応じた乗数）を実装。
    - portfolio/position_sizing.py: calc_position_sizes（risk_based / equal / score の割当方法、lot_size 単位丸め、aggregate cap のスケーリング、cost_buffer を使った保守的見積り）を実装。
    - portfolio/__init__.py から上記関数をエクスポート。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py: ペーパートレード用 SQLite を集計して検証レポートを生成する CLI を追加（python -m kabusys.tools.paper_verification_report）。稼働率、注文成功率、送信率、P95 レイテンシなどの指標を計算し、閾値に基づいて PASS/FAIL を出力します。P95 計算、日付フィルタ、N/A 表示などに対応。
  - 研究用モジュール（スキャフォールド）
    - research/factor_research.py: モメンタム等のファクター計算ロジック（calc_momentum 等の実装開始）および計算に関する定数を追加（DuckDB 接続を用いる設計）。（ファイルは一部実装まで）
  - パッケージメタ
    - kabusys.__version__ = "0.1.0" を追加。

### 変更 (Changed)
- DB の取り扱い方針を明示
  - 監視系（run_monitoring）は常に Settings.sqlite_path（本番監視 DB）を使用するように明確化。
  - 実行系（run_execution）は KABUSYS_ENV に応じて paper_trading 用 DB（settings.paper_sqlite_path）を使用することで paper_trading と本番を明確に分離。
- ロギング設定の挙動
  - setup_logging は既存ハンドラをクリアしてから再設定するように変更（重複ハンドラ防止）。
  - コンソール出力は stdout を使用する方針を採用（cron や Task Scheduler でのログ管理を考慮）。
- .env 自動ロードの仕様
  - 自動ロードの順序: OS 環境変数（保護） > .env（未設定のみセット） > .env.local（上書き）となるロジックが導入され、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- 環境変数の検証強化
  - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject" のみ許容）。
  - KABUSYS_ENV や LOG_LEVEL の値検査を追加（無効値は ValueError）。
- 実行開始時のプロセス優先度設定
  - run_execution と run_monitoring の起動直後に set_process_priority("high") を呼び出すようになりました。

### 修正 (Fixed)
- .env ファイル読み込みの堅牢化
  - ファイル読み込み失敗時に警告を出して続行するようにし、export 形式・クォート・エスケープやインラインコメントを正しく解析するよう改善。
- logging_setup のディレクトリ作成失敗時のフォールバック
  - ログディレクトリ作成に失敗してもコンソール出力は継続するようにし、失敗理由を stderr に出力する対応を追加。

### 注意事項 (Notes)
- 必須環境変数
  - 本リリースでは JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD が必須です。validate_config により起動前のチェックが可能です。
- Kill / Stop フラグ
  - 停止制御はプロジェクトルート下の data/stop_requested.flag（run_monitoring/run_execution）や data/kill.flag（Settings.kill_flag_path がデフォルト）で行います。KILL_FLAG_CLEAR_ON_START 環境変数に注意してください（本番では 0 推奨）。
- DuckDB / SQLite
  - 一部モジュールは DuckDB 接続（分析用）と SQLite（監視・履歴用）双方を利用します。デフォルトパスは DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db、PAPER_TRADING_SQLITE_PATH= data/paper_trading.db です。必要に応じて環境変数で上書きしてください。
- 研究モジュールは未完成の箇所があります（factor_research.py は実装途中）。実運用前に追加実装・レビューを推奨します。

### 既知の制限 (Known limitations)
- position_sizing の lot_size は全銘柄共通で固定（将来的に銘柄別拡張を検討）。
- apply_sector_cap は price_map に価格欠損（0.0）があるとエクスポージャーが過小評価される可能性があり、将来的に価格フォールバックの導入を想定。
- process_priority / cpu_affinity の設定は権限不足やプラットフォームによって無効化される場合がありますが、その場合は警告を出して安全にスキップします。

---

（必要であればリリース以降のバージョンや細かなコミットごとの差分を追記できます。ご希望があれば、各ファイルごとの変更点の詳細や開発者向けのマイグレーション手順を追加で生成します。）
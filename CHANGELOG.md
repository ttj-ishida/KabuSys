CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。重要な仕様変更・新機能・挙動に関する注意点を日本語でまとめています。

0.1.0 - 2026-04-11
-----------------

Added
- 実行用エントリポイントを追加
  - run_execution: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用データベース（デフォルト: data/paper_trading.db）を使用して本番 DB と分離して実行する。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60秒）。監視は環境に関わらず本番 sqlite_path を使用する点に注意。
- 環境設定関連の CLI を追加
  - config_setup: 対話式ウィザードで .env を作成 / 更新するユーティリティを追加。各設定項目の説明・デフォルトを提示し、保存機能を提供。
  - validate_config: .env と config/*.yaml の起動前検証ツールを追加。--strict オプションで警告も失敗扱いにできる。PyYAML 未インストール時は YAML 検証をスキップして警告を出す。
- Paper Trading 検証ツールを追加
  - tools.paper_verification_report: ペーパートレード用 SQLite を参照してシステム稼働率、注文成功率、送信率、API レイテンシ（P95 等）を集計・レポートする CLI を追加。閾値 (稼働率、成功率、P95 等) を定義して PASS/FAIL 判定を出力する。
- 設定管理・ユーティリティを充実
  - config.Settings クラスを追加/拡張: 各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等）をプロパティとして提供。KABUSYS_ENV の妥当性チェック、LOG_LEVEL 検証などを実装。
  - .env 自動読み込みを追加 (.env, .env.local)。優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサの堅牢化: export KEY=val 形式、クォート／エスケープ、行内コメント処理をサポートするパーサを実装。
- ポートフォリオ構築モジュールを追加
  - portfolio.portfolio_builder: BUY シグナルの候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights を実装。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を実装（未定義レジームは警告の上で 1.0 にフォールバック）。
  - portfolio.position_sizing: allocation_method（"risk_based" / "equal" / "score"）に基づいた株数計算を実装。lot_size 単位で丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap のスケーリングロジックを含む。
- ログ・プロセス制御ユーティリティを追加
  - utils.logging_setup.setup_logging: stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログを logs/<app_name>.log に出力する共通設定を提供。LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority: Windows/Linux/macOS を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。psutil の権限不足等は警告でスキップする。

Changed
- run_execution / run_monitoring の初期動作
  - 起動時にプロセス優先度を "high" に設定する処理を追加（プラットフォーム依存権限で失敗する場合は警告）。
  - 実行と監視で DuckDB 接続を作成するよう変更（duckdb_path を使用）。
- DB 接続ポリシー
  - run_monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（本番監視 DB）を使用する設計とした（監視データは一元管理）。
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（分離された Paper Trading DB）を使用することで本番 DB と完全分離する挙動に変更。
- .env の読み込みルール
  - .env.local の優先度を .env より高くし、protected（OS 環境変数）を上書きしない仕組みを導入。
  - _find_project_root により __file__ を基準にプロジェクトルートを探索するため、CWD に依存しない自動ロードを実現。
- ログ出力の標準化
  - ルートロガーの既存ハンドラをクリアしてから再設定するように変更し、二重出力を防止。

Fixed
- 環境変数パースの不備を修正
  - クォート内のバックスラッシュエスケープや行内コメントの判定を正しく処理するように改善。
- Paper 検証レポートの統計計算
  - P95 計算を追加し、latency_ms が NULL の場合の扱いを明確化。各クエリでテーブルが存在しない場合に sqlite3.OperationalError を捕捉してフォールバックするように修正。

Security
- .env の取り扱いについて注意喚起を追加
  - config_setup が生成する .env ヘッダに「.env は絶対に Git にコミットしないこと」を明示。

Deprecated
- なし

Removed
- なし

Notes / Breaking changes / Migration
- 監視 DB の使用ポリシー
  - run_monitoring は意図的に settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。開発環境で監視を分離したい場合は sqlite_path を別ファイルに設定してください。
- Paper Trading 分離
  - run_execution は paper_trading モード時に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用するため、従来の本番監視 DB を上書きすることはありません。Paper モードの DB は本番データと完全に分離されます。
- 環境自動読み込みの動作
  - OS 環境変数が優先され、.env.local が .env より優先されます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログディレクトリ作成失敗時のフォールバック
  - 権限や環境によって logs ディレクトリが作成できない場合、ファイルハンドラは使用されず stdout のみでログが出力されます。

開発者向けメモ
- package version は __init__.py にて __version__ = "0.1.0" に設定されています。
- 新しい CLI はそれぞれモジュール実行可能:
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report

今後の改善候補
- price の欠損時（0.0）のフォールバック戦略（前日終値や取得原価の利用）を検討中（apply_sector_cap に TODO コメントあり）。
- 銘柄ごとの lot_size をサポートするため、将来的に stocks マスタを導入して position_sizing を拡張する予定。
- factor_research モジュール（ファクター計算）は設計方針を記載済みだが、実装の続き（コード断片の途中で切れている箇所）があるため完了させる必要あり。

--- 

注: 上記はソースコードから推察した変更点・設計方針のまとめです。実行時の具体的な挙動は環境変数や外部ライブラリ（psutil, duckdb, PyYAML 等）の有無・バージョンに依存します。
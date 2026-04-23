CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）

0.1.0 - 2026-04-23
------------------

Added
- 基本リリースとしてコア機能を実装。
- 起動スクリプトを追加:
  - run_monitoring.py — SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag による。
  - run_execution.py — ExecutionEngine 起動。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db をデフォルト）を使用し MockBroker を利用して本番 DB と分離。
- 設定管理:
  - config.py: Settings クラスを導入し、環境変数 / .env / .env.local から設定を取得。プロジェクトルート検出ロジック（.git または pyproject.toml 基準）を実装して自動 .env ロードを行う（無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意）。
  - .env パースロジックは export プレフィックス、クォート、インラインコメント、エスケープを考慮。
  - 各種設定プロパティ（DB パス、paper_trading 用パス、監視しきい値、KABUSYS_ENV 判定ロジック等）を提供。
- 設定ユーティリティ / CLI:
  - config_setup.py — 対話式ウィザードで .env を初期作成・更新。秘密情報はマスク表示、デフォルト値・選択肢をサポート。
  - validate_config.py — 起動前に環境変数・config/*.yaml・DB パス・本番向けのガード条件を検証する CLI。--strict オプションで警告を FAIL 扱いにできる。PyYAML がない場合は YAML 検証をスキップして警告を出す。
- ロギング / 実行環境ユーティリティ:
  - utils/logging_setup.py — setup_logging(): stdout へ StreamHandler（stdout 使用）とログファイルへ TimedRotatingFileHandler（日次ローテート、30日保持）をルートロガーに設定。既存ハンドラをクリアして二重設定を防止。LOG_DIR/LOG_LEVEL の解決順を実装。
  - utils/process_priority.py — set_process_priority, set_cpu_affinity を実装。Windows / POSIX の違いを吸収し、アクセス権限や未対応 OS 時は警告でスキップ。
- ポートフォリオ構築関連（純粋関数群）:
  - portfolio/portfolio_builder.py — 銘柄選定（スコア降順、同点は signal_rank でタイブレーク）、等金額配分、スコア加重配分（全スコアが 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py — セクター集中制限の適用（既存ポジションを基にセクターごとのエクスポージャーを計算して新規候補を除外）、市場レジームに応じた投下資金乗数計算（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py — allocation_method（risk_based / equal / score）に応じた株数算出、単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的コスト見積り、残余の再配分ロジックを実装。
- 解析ツール:
  - tools/paper_verification_report.py — ペーパートレード DB から稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）等を集計して判定（PASS/FAIL）を出力するレポートツール。日付フィルタ、--db 指定、環境変数 PAPER_TRADING_SQLITE_PATH に対応。
- 研究用モジュール（骨子実装）:
  - research/factor_research.py — モメンタム等のファクター計算を行うための定数・calc_momentum の骨子を実装（DuckDB 接続を受ける設計）。

Changed
- ログ出力方法:
  - StreamHandler は stderr ではなく stdout を利用（cron 等からのリダイレクトを想定）。
- 環境変数読み込み順:
  - OS 環境 > .env.local > .env の順で解決。OS 環境を保護するため、.env(.local) 上書き時に OS 環境変数のキーは保護される。
- モニタリングの DB 接続:
  - run_monitoring は KABUSYS_ENV に関係なく sqlite_path（本番用設定）を使用する設計になっている旨を注記（意図的な動作）。

Fixed
- 環境変数の不正値時のフォールバックと警告:
  - MONITOR_POLL_INTERVAL の不正値を検出してデフォルト（60 秒）を使用する処理を実装。
  - Settings.paper_fill_mode など、許容値外の設定に対して明示的な例外/警告を出すように改善。
- ロギングディレクトリ作成失敗時はファイルハンドラをスキップし、コンソールログのみで継続する安全な挙動に統一。

Security
- 秘密情報取り扱い:
  - config_setup の対話ではシークレット項目をマスクして表示。README/ドキュメントで .env を Git にコミットしないことを強調（ヘッダコメント）。

Notes / Known behaviors
- run_monitoring が常に production 用 sqlite_path を使う点は意図的だが、環境に応じた別 DB を想定する場合は挙動に注意してください。
- set_process_priority / set_cpu_affinity は実行 OS・権限によって失敗する可能性があり、その場合は警告ログを出してスキップします（例: 権限不足）。
- tools/paper_verification_report は SQLite テーブルの存在・カラムに依存します。テーブルがない場合は該当指標を N/A や 0 で処理する耐性を持ちます。
- PyYAML はオプション（validate_config の YAML 検証に使用）。インストールされていない場合は YAML のパース検証をスキップして警告を出します。
- パッケージのバージョンは kabusys.__version__ = "0.1.0"。

Examples / CLI
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ペーパートレードレポート:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite
- 実行スクリプト（例）:
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution

Unreleased
- 今後のリリースでは factor_research の各ファクター計算実装完了、より詳細なテスト、各モジュールの型注釈・ドキュメントの拡充を予定。
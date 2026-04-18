# Changelog

すべての注記は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
このファイルはコードベースから推測して生成した変更履歴です。

## [0.1.0] - 2026-04-18

### Added
- 初期リリース。本パッケージの主要機能を追加。
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV による paper_trading の分離（MockBrokerClient を利用）と専用 SQLite（data/paper_trading.db）への記録をサポート。エンジンは別スレッドで実行され、stop フラグ検知で安全に停止可能。起動時に PID ファイルを書き込む仕組みを提供。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は実行環境にかかわらず本番の sqlite_path を使用し、stop フラグ検知で終了。
- 設定管理と支援ツール
  - config.py: .env の自動読み込み機能（プロジェクトルート探索）、.env ファイル行の柔軟なパース（export 形式、クォート／エスケープ、インラインコメント処理）、Settings クラスによる環境変数の型チェックと既定値を実装。PAPER_FILL_MODE のバリデーションや env 判定（development/paper_trading/live）など多数のプロパティを提供。
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。シークレット値のマスク表示や既存 .env の取り込み、保存処理を提供。
  - validate_config.py: 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ確認、YAML パースチェック（PyYAML が未インストールの場合は警告）、本番環境向けのガードチェックを実施。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルの候補選定（スコア順、タイブレーク）、等金額・スコア加重の重み計算を追加。スコア全0時のフォールバックに警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限の適用ロジック（既存保有のエクスポージャ計算と新規候補フィルタ）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を追加。未知レジーム時はフォールバックして警告を出す。
  - portfolio/position_sizing.py: 各種配分方式（risk_based, equal, score）に基づく株数算出ロジックを追加。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer（手数料・スリッページ見積）を考慮した配分・スケーリング処理を実装。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティを追加。StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）を設定。LOG_LEVEL / LOG_DIR の解決順を実装し、ディレクトリ作成失敗時にファイル出力をスキップしてコンソールのみで継続する。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定を追加。Windows / POSIX（Linux, Darwin, FreeBSD）を考慮し、権限不足や未対応プラットフォームでは安全にスキップして警告を出す。
- ペーパートレーディング検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite のログから稼働率、注文成功率、送信率、レイテンシ等を集計し、PASS/FAIL 判定を出力するレポート生成 CLI を追加。P95 計算、期間フィルタ（--from / --to）、閾値定義を実装。DB が存在しない場合のユーザ向けメッセージも含む。
- research/factor_research.py（初期実装の一部）
  - DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム / MA200 / ATR / ボラティリティ等を想定）。関数設計方針と定数が定義されており、prices_daily/raw_financials テーブルを参照する設計。

### Changed
- パッケージメタ情報
  - __init__.py にて初期バージョンを 0.1.0 に設定。

### Notes / Implementation details
- run_monitoring と run_execution はどちらも起動時に set_process_priority("high") を呼ぶことで、優先度を高めに設定しようとする（設定失敗時は警告を出して継続）。
- run_execution は paper_trading モード時に paper_sqlite_path を使用して本番 DB と明確に分離する設計。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行い、OS 環境変数は保護して上書きを制御する仕組みを採用。
- validate_config は PyYAML の未インストールを許容して YAML 検証をスキップ（警告）することで依存を緩めている。
- logging_setup は stdout に出力することで、cron や Task Scheduler などで stdout/stderr を一元的に扱いやすくしている。

### Removed
- なし（初回リリース）

### Deprecated
- なし（初回リリース）

### Security
- なし（初回リリース）
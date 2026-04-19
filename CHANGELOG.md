Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に準拠します。
安定版リリースはセマンティックバージョニングに従います。

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 2026-04-19
-----------------

Added
- 初回公開リリース。
- アプリケーション全体のエントリポイント / 起動スクリプトを追加:
  - run_execution.py — ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時に専用の paper DB を使用して本番 DB と分離する仕組みを実装。エンジンは別スレッドで起動し、data/stop_requested.flag による停止監視、実行 PID の書き出しをサポート。
  - run_monitoring.py — システム監視（SystemMonitor）用ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト: 60秒）。監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
- 環境設定・検証関連の CLI を追加:
  - config_setup.py — 対話式ウィザードで .env ファイルを作成・更新するツール。各種設定項目（API トークン、DB パス、LOG_LEVEL、KABUSYS_ENV 等）を対話的に入力可能。
  - validate_config.py — .env および config/*.yaml の事前チェックツール。必須環境変数やパス、YAML のパース確認、KABUSYS_ENV=live に対する追加ガードを実装。--strict オプションで警告をエラー扱いにする。
- 設定管理機能を追加:
  - config.py — .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）と環境変数取得用 Settings クラスを実装。各種既定値、バリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を提供。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- ポートフォリオ構築関連モジュールを追加（純粋関数群、DB 参照なし）:
  - portfolio/portfolio_builder.py — 候補選定（スコア降順）・等金額配分・スコア加重配分。
  - portfolio/risk_adjustment.py — セクター集中制限（apply_sector_cap）、市況レジームに基づく乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py — 各銘柄の株数計算（risk_based / equal / score）、単元丸め、aggregate cap によるスケーリング、手数料・スリッページを考慮する cost_buffer。
  - portfolio/__init__.py で主要関数をエクスポート。
- 分析・研究用モジュールを追加（DuckDB ベース）:
  - research/factor_research.py — モメンタム、ボラティリティ、バリュー等のファクター計算の骨組み（DuckDB 接続を受け取る設計）。（注: モジュールは設計途中の関数を含む。）
- 運用ツールを追加:
  - tools/paper_verification_report.py — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・レイテンシ（P95 など）を計算して PASS/FAIL 判定するレポート生成スクリプト。期間フィルタ（--from / --to）対応。デフォルトの基準値を設定（例: 稼働率 >= 99% 等）。
- 汎用ユーティリティを追加:
  - utils/logging_setup.py — StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保管）をルートロガーに設定するユーティリティ。ログディレクトリの自動作成と、失敗時はファイル出力を自動でスキップする安全策を実装。ログレベル/ログディレクトリは引数・環境変数から解決。
  - utils/process_priority.py — Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）と CPU affinity 設定を行うユーティリティ。権限不足・未対応環境では警告を出してスキップする。
- 監視用 DB 初期化ヘルパー（monitoring_db 参照）と SystemMonitor 組み込み（起動スクリプトから利用）を統合（init_monitoring_db を呼び出して監視テーブルを冪等に作成）。

Changed
- プロジェクトパッケージ宣言を追加:
  - kabusys/__init__.py に __version__ = "0.1.0" と主要サブパッケージを列挙。

Fixed
- 起動時のプロセス優先度設定を各起動スクリプトの最初に実行するようにし、運用時の優先度指定を明示化（set_process_priority("high") を使用）。

Security
- .env ファイルは生成時に Git コミットしないよう明示（config_setup.py の出力ヘッダに警告）。

Notes / Known issues / TODO
- research/factor_research.py の一部関数（例: calc_momentum）は実装が途中でファイルの末尾が切れている箇所が見られます。完全実装が必要です。
- apply_sector_cap の価格取得で price が欠損（0.0）の場合、エクスポージャーが過小に見積もられる旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する必要があります。
- position_sizing.py では将来的に銘柄別の単元（lot_size）をサポートする TODO が残っています。
- run_monitoring.py は説明コメントにある通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」します。運用前に意図的な設定かを確認してください。
- config.py の .env 自動ロードはプロジェクトルート検出に依存するため、配布後やインストール環境によっては自動ロードがスキップされる場合があります（その場合は環境変数で明示的に設定してください）。
- set_process_priority / set_cpu_affinity はプラットフォームや権限によって失敗する可能性があり、その場合は警告ログに留めて処理を継続します。
- ログディレクトリの作成やファイルハンドラの作成に失敗した場合、ログはコンソール（stdout）出力のみで継続します。

Upgrade notes
- 初回リリースのためアップグレードに伴う破壊的変更はありません。

Contributing
- バグ報告、機能追加の提案、プルリクエストは歓迎します。開発中のモジュール（特に research/*）はインタフェース変更が発生する可能性があります。

License
- （リポジトリに含まれるライセンス文書に従ってください）
# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に従って記載しています。

現在のバージョン: 0.1.0 — 2026-04-18

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

追加 (Added)
- 初回リリース: KabuSys 日本株自動売買システムの基礎機能を実装。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレーディング用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。起動時にプロセス優先度を設定し、停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を扱う。
  - run_monitoring.py: SystemMonitor のポーリングループを行うエントリポイントを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を参照する設計。
- 設定管理
  - config.py: 環境変数取得用 Settings クラスを実装。自動 .env 読み込み（プロジェクトルートの .env / .env.local、OS 環境変数優先）と堅牢な .env パーサを提供。各種設定プロパティ（DB パス、KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を定義し、値検証を行う。
  - config_setup.py: 対話式の .env 作成/更新ウィザードを実装。シークレット入力のマスク化、選択肢・デフォルトの扱い、保存前の確認を含む。
  - validate_config.py: 起動前設定検証 CLI を実装。必須環境変数や KABUSYS_ENV、DB パス、config/*.yaml の存在・パース検証（PyYAML があればパースまで）、`--strict` モードで警告をエラー扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーに対して StreamHandler（stdout）および TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。ログディレクトリ自動作成、既存ハンドラのクリア、ログレベル解決（引数 > LOG_LEVEL 環境変数 > デフォルト）をサポート。ログ出力に失敗した場合は console のみで継続。
  - utils/process_priority.py: クロスプラットフォーム向けプロセス優先度設定と CPU affinity 設定を追加。Windows/Linux/macOS を考慮し、権限不足などで失敗した場合は警告を出してスキップする。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順で上位 N 件選択）、等分配・スコア加重配分（スコア全てが 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知のレジームは 1.0 でフォールバックし警告を出す。
  - portfolio/position_sizing.py: 発注株数算出を実装（allocation_method: "risk_based", "equal", "score" をサポート）。損切り・リスク率に基づく算出、上限（単銘柄比率 / aggregate 利用可能現金）適用、単元株（lot_size）丸め、コストバッファを考慮したスケーリングと端数配分ロジックを実装。
- データ解析 / リサーチ
  - research/factor_research.py（骨格実装）: DuckDB 接続を受け取り、prices_daily / raw_financials を用いたモメンタム・バリュー・ボラティリティ・流動性ファクター計算のための関数群設計を追加（calc_momentum 等の実装方針と定数定義を含む）。
- ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。システム安定性（稼働率）、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を計算し、閾値に基づく PASS/FAIL 判定を行う。閾値はソース内定数で定義（稼働率 99% など）。コマンドライン引数で期間指定と DB パス上書きが可能。
- パッケージ情報
  - src/kabusys/__init__.py にバージョン文字列 __version__ = "0.1.0" を追加。

変更 (Changed)
- 初回リリースのため該当なし。

修正 (Fixed)
- 初回リリースのため該当なし。

非推奨 (Deprecated)
- 初回リリースのため該当なし。

削除 (Removed)
- 初回リリースのため該当なし。

セキュリティ (Security)
- 初回リリースのため該当なし。

注記 / 動作上の重要ポイント
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を発見した場合のみ行います。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。無効な値は起動時に ValueError を発生させます。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を変更できます。不正な値（0 以下や非整数）はデフォルト 60 秒にフォールバックします。
- run_execution はペーパートレード時に本番データベースと完全分離する設計（paper_sqlite_path を使用）で、RiskManager の初期化時に broker.get_available_cash() を用いて initial_portfolio_value を設定します。
- logging_setup は標準出力にログを出力するように設計されており、cron 等で stdout/stderr を一本化している環境を考慮しています。
- process_priority の設定は権限や OS の違いで必ずしも成功しないため、失敗時は警告ログを出して処理を継続します。
- portfolio モジュールの関数群は副作用を持たない純粋関数として実装され、単体テストしやすい設計になっています。

参照
- CLI:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証:   python -m kabusys.validate_config [--strict]
  - ペーパーレポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

今後の予定（非包括的）
- research/factor_research のファクター計算の完全実装（calc_momentum の続き等）。
- ExecutionEngine / ブローカラッパの詳細実装およびテスト強化。
- モニタリング周り（SystemMonitor や monitoring_db）の拡充とアラート連携（LINE 通知等）。
- 単体テスト・統合テストの整備とドキュメント追加。

------------------------------------------------------------
（この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴とは一部差異がある可能性があります。）
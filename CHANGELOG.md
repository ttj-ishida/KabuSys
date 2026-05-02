CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
書式は "Keep a Changelog" に準拠し、Semantic Versioning を想定します。

[Unreleased]
------------

（現時点では未リリースの差分はありません。下記はコードベースから推測した初期リリースの機能一覧です。）

[0.1.0] - 2026-05-02
--------------------

Added
- 基本アプリケーション初期リリース。
- 実行/運用用の複数 CLI エントリポイントを追加:
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使用し MockBroker を利用（本番 DB と完全分離）。起動時に総資産を計算し、Reconciler による起動時リコンシリエーションと Startup Summary を生成する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - run_intraday_monitor.py: ザラ場中監視向け CLI（単発出力 / watch モード）。プロセス状態、ドローダウン、注文エラー／滞留注文、システム指標などを表示。
  - run_signal_queue_report.py: Signal Queue 確認ビュー生成 CLI（--date / --save / --json 対応）。
  - run_position_reconciliation_report.py: ポジション突合レポート CLI（--date / --save / --json / --watch / --interval 対応）。Broker からポジションを取得し突合レポートを生成。
  - run_pre_market_report.py: Pre-Market Report 生成 CLI（--save / --json 対応）。stop_flag のチェックやタスクスケジューラ準備状態も確認。
  - run_market_close_report.py: Market Close Summary 生成 CLI（--date / --save / --json 対応）。
  - run_performance_report.py: 運用成績サマリーレポート生成 CLI（daily/weekly/monthly、--env、期間指定、--save 対応）。
  - validate_config.py: .env と config/*.yaml の事前検証ツール（--strict オプションで警告を FAIL 扱いにできる）。
  - config_setup.py: 対話式 .env 作成/更新ウィザード。シークレットマスク、選択肢提示、デフォルト値のサポート。
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプト（稼働率、注文成功率、送信率、レイテンシ P95 等の算出と閾値判定）。

- 環境設定 / 設定読み込み:
  - config.py: Settings クラスを実装。環境変数の自動読み込み（.env, .env.local）機能を提供。プロジェクトルート検出は .git または pyproject.toml を基準とするため CWD 非依存で動作。
  - .env パーサーの強化: export KEY=val 形式、クォートされた値（バックスラッシュエスケープ対応）、インラインコメントの扱いをサポート。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings による各種設定プロパティを提供（J-Quants / kabu API / LINE / DuckDB / SQLite / Paper trading 用設定 / モニタリング閾値 / ログレベル 等）。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject のみ許容）。
  - paper_sqlite_path：ペーパートレード専用 DB パスのサポート。

- DB / 分析連携:
  - DuckDB を分析用 DB として採用し、各種レポート／収集処理で利用。
  - SQLite を監視・トレードログ用に利用。paper_trading 環境向けに別 SQLite（data/paper_trading.db）を用意して分離。

- 監視 / プロセス管理:
  - PID ファイルと停止フラグ（data/*.pid, stop_requested.flag）によるプロセス起動・停止制御。
  - run_monitoring/run_execution でプロセス優先度を "high" に設定するユーティリティ呼び出しを実行。
  - モニタリング初期化（monitoring_db 初期化）を冪等に保証。

- リスク管理:
  - risk_config.yaml のロードと厳密なバリデーションを実装。パラメータの型チェック、範囲チェック（0 < 値 <= 1 など）、相関チェック（max_position_pct <= max_utilization）を行う。
  - RiskConfig オブジェクトを RiskManager に渡す設計。

- レポート機能:
  - CLI からの --json 出力、ローカル保存 (--save) を多くのレポートでサポート。JSON 出力時に保存先メッセージは stderr に出す等の配慮を実装。
  - パフォーマンス / ポジション / シグナルキュー / プレマーケット / マーケットクローズ等のレポートビルダーとフォーマッタを用意。

- その他ユーティリティ:
  - validate_config により環境変数未設定、プレースホルダ検出、ファイル存在／YAML パースチェック、live 環境向けガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の警告）などを提供。
  - config_setup による .env の生成／上書き（既存値の再利用・マスク表示・キャンセル対応）。

Changed
- なし（初回リリース想定のため）。

Fixed
- なし（初回リリース想定のため）。

Notes / 実装上の挙動（重要事項）
- run_monitoring は KABUSYS_ENV の値に関わらず常に本番 sqlite_path を参照する設計になっているため、ペーパートレード時は注意が必要（実運用では監視 DB の分離方針を確認してください）。
- ペーパートレード環境では run_execution が settings.paper_sqlite_path を使うことで実 DB と分離される。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる。テストなどで自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- validate_config の --strict を利用すると警告も失敗（exit 1）と扱うため、デプロイ前のチェックに便利。
- paper_verification_report では P95 計算を独自に実装しており、データがない場合は N/A を返す仕様。

開発者向けメモ
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として管理。
- 多数の CLI モジュールが duckdb / sqlite / BrokerClientFactory / ExecutionEngine 等の外部コンポーネントに依存するため、実行環境では必要な DB ファイル、API キー、kabuステーションの設定が正しく配置されていることを確認してください。

----


（本 CHANGELOG は提供されたソースコードから推測して作成しています。実際の変更履歴やリリース日、マイナー／パッチ扱いはプロジェクトのリリースポリシーに合わせて調整してください。）
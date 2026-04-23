# Changelog

すべての注目すべき変更はここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新リリース
------------

### [0.1.0] - 2026-04-23

Added
- 初期リリース。以下の主要コンポーネントを導入しました。
  - 起動スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。
      - 停止はプロジェクト直下 data/stop_requested.flag により検出。監視は常に本番の sqlite_path を参照。
      - SQLite / DuckDB 接続確立と初期化を行い、例外発生時もループを継続するガードを実装。
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db がデフォルト）を使用し、本番 DB と分離。
      - BrokerClientFactory を通じてブローカークライアントを生成。Engine は別スレッドで実行され、停止フラグで安全停止。
      - PID ファイル管理（data/execution.pid）と停止フラグ検出を実装。
  - 設定管理 / CLI
    - src/kabusys/config.py
      - 環境変数読み込みユーティリティ。プロジェクトルートを .git または pyproject.toml から自動検出。
      - .env / .env.local を自動ロード（OS 環境変数は保護）。値のパースはクォート、export プレフィックス、インラインコメント等に対応。
      - 各種設定プロパティ（DB パス、API トークン、監視閾値、環境判定等）を提供。
    - src/kabusys/config_setup.py
      - .env 初期作成・更新の対話式ウィザード。既存 .env の読み込み・マスク表示、保存機能を提供。
    - src/kabusys/validate_config.py
      - 起動前の設定検証 CLI。必須環境変数の存在、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検査、live 環境向けガードを提供。
      - --strict モードで警告も失敗扱いにできる。
  - ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定するユーティリティ。
      - LOG_DIR / LOG_LEVEL からの解決、既存ハンドラのクリア、ファイルハンドラ作成失敗時のフォールバックを考慮。
    - src/kabusys/utils/process_priority.py
      - Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（high/normal/low）。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。失敗時は警告を出してスキップ。
  - ポートフォリオ構築ロジック（pure functions）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定（スコア降順・タイブレーク）と等配分 / スコア加重配分の実装。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - src/kabusys/portfolio/position_sizing.py
      - 単元株丸め、risk_based / equal / score の割当方式、max_position や aggregate cap、cost_buffer を考慮したスケーリングなどを実装。
    - src/kabusys/portfolio/__init__.py によるエクスポート。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレード DB を解析して検証レポートを出力するスクリプト。
      - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
      - デフォルト閾値: 稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms。DB パスは引数または PAPER_TRADING_SQLITE_PATH で指定可能。
  - リサーチ
    - src/kabusys/research/factor_research.py
      - DuckDB を用いたファクター計算モジュール（モメンタム、MA200乖離、ATR、流動性など）の骨組みを追加。prices_daily / raw_financials を参照する設計。
  - パッケージメタ
    - src/kabusys/__init__.py
      - パッケージバージョン __version__ = "0.1.0" を設定。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

Notes / 注意点
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。プロジェクトルートが特定できない場合は自動ロードをスキップする。
- run_monitoring は監視用に常に settings.sqlite_path（本番パス）を使用する設計です。ペーパートレードでは run_execution が settings.paper_sqlite_path を使用して DB 分離します。
- process_priority / set_cpu_affinity は権限やプラットフォームにより機能しない場合があります。その場合は警告を出して処理を継続します。
- tools/paper_verification_report の閾値は現状ハードコードされています。運用に合わせて調整してください。
- src/kabusys/research/factor_research.py はファイル末尾で未完了（ソースが途中で切れている可能性）が見られます。ファクター計算ロジックの完全実装は今後のタスクです。

今後の予定（提案）
- factor_research の続き実装（calc_momentum 等の完成・テスト）。
- strategy / execution のユニットテスト追加、および BrokerClient のモック整備。
- logging のメトリクス出力や Prometheus Exporter 等の統合検討。
- paper_verification_report の自動化（CI / 定期ジョブでのレポーティング）と閾値の設定ファイル化。

--------------------------------
この CHANGELOG はコードの現状から推測して作成しています。実際の開発履歴や意図と差異がある場合がありますので、必要に応じて追記・修正してください。
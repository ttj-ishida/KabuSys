CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-04-23
------------------

Added
- 初回公開: KabuSys v0.1.0 をリリース。
- 実行用エントリポイント:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、ブローカークライアント生成、OrderManager / RiskManager / Reconciler 組み立て、別スレッドでのセッション実行、停止フラグ検知による安全停止等を実装。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を分離して使用する設計。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番向け sqlite_path を参照する（環境に依存しない）。
- 設定関連 CLI/ユーティリティ:
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加（選択肢表示、シークレットマスク、保存確認）。
  - validate_config.py: .env と config/*.yaml の整合性チェック CLI を追加。必須環境変数チェック、パスや YAML パース確認、KABUSYS_ENV による追加ガード等を実装。--strict オプションで警告を FAIL 扱いにできる。
  - config.py: 環境変数/ .env 自動読み込み機能を実装（プロジェクトルート自動検出。.env/.env.local を上書き処理付きで読込）。値パース、必須取得ヘルパー、各種設定プロパティ（DB パス、ログレベル、Paper Trading の挙動など）を提供。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を追加。スコア全ゼロ時のフォールバックを含む。
  - portfolio/risk_adjustment.py: セクター集中（apply_sector_cap）と市場レジームによる投下資金乗数（calc_regime_multiplier）を追加。未知レジームのフォールバックやログ出力を含む。
  - portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score）を追加。単元丸め、per-position / aggregate cap、スケールダウンロジック、コストバッファ考慮を実装。
  - portfolio/__init__.py: 上記関数群をパッケージとしてエクスポート。
- ユーティリティ:
  - utils/logging_setup.py: 統一的ロギング設定を追加。stdout ストリームハンドラと日次ローテーションのファイルハンドラを設定（デフォルト logs/<app>.log、30日分保持）。LOG_LEVEL / LOG_DIR の解決順、失敗時のフォールバックを実装。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度（Windows の優先度 / POSIX の nice）および CPU affinity 設定ユーティリティを追加。アクセス権限や未対応 OS に対するフォールバック処理を実装。
- ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を算出し PASS/FAIL を判定。日付フィルタ、DB パス引数/環境変数対応を実装。
- 研究用モジュール（基盤実装）:
  - research/factor_research.py: ファクター計算モジュール（モメンタム／MA200乖離／ATR／流動性等の設計方針と一部定数）を追加。DuckDB を用いた prices_daily / raw_financials ベースの計算を想定（関数実装は継続中）。
- パッケージメタ:
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- 初期リリースのため変更履歴は特になし（新規導入）。

Fixed
- 初期リリースのため修正履歴は特になし。

Security
- 環境変数ファイル (.env) 生成時に注意書きを追加（.env を絶対に Git にコミットしない旨を記載）。

Notes / 実装上の重要ポイント
- run_execution/run_monitoring は stop flag と pid file を用いる設計（data/stop_requested.flag, data/execution.pid など）。運用時にこれらファイルでプロセス制御を行う想定。
- Paper Trading は本番 DB と物理的に分離（PAPER_TRADING_SQLITE_PATH、data/paper_trading.db がデフォルト）。
- config の自動読み込みはプロジェクトルート検出（.git または pyproject.toml）に基づくため、配布後やインストール環境でも CWD に依存せず動作するよう配慮。
- ログ設定は stdout を標準出力に設定（cron 等で stdout/stderr を統一してリダイレクトする用途を想定）。
- process_priority や CPU affinity の変更は権限不足や未対応 OS の場合に警告ログを出して安全にフォールバックする。

Acknowledgements
- 本リリースは初期実装フェーズであり、ドキュメント・テスト・一部機能（例: research/factor_research の完全実装や外部 API 連携の詳細）は今後の改善対象です。
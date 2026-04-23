# CHANGELOG

すべての変更は Keep a Changelog の規約に準拠して記載しています。  
代表的なコマンド・エントリポイント:
- 監視プロセス: python -m kabusys.run_monitoring
- 実行エンジン: python -m kabusys.run_execution
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report

注: 日付はこのリリース作成日です。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-23
初回リリース。自動売買システム「KabuSys」の基本機能を公開。

### Added
- パッケージ基礎
  - 初期バージョン番号を追加 (src/kabusys/__init__.py: __version__ = "0.1.0")。
  - パッケージ公開用エクスポート定義を追加（data, strategy, execution, monitoring）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db を既定）を使用し、本番データベースと分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動ロジックを実装。
    - 停止フラグ (data/stop_requested.flag) の検出と PID ファイル管理 (_EXECUTION_PID) をサポート。
  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor を使ったポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。

- 設定管理
  - 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - _find_project_root による安全なルート検出。
    - .env のパースはクォート / エスケープ / コメントに対応。
    - Settings クラスでアプリ設定をプロパティとして提供（DB パス、環境、ログレベル、Paper トレード設定等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化機能。

- 設定ツール・検証
  - 対話式設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を支援。既存値の再利用、シークレット項目のマスク表示、保存前の確認をサポート。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML 有りの場合）パース検証、live 環境向けの追加ガードを実施。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と、日次ローテート（30日保持）の TimedRotatingFileHandler をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の優先解決、ディレクトリ作成失敗時のフォールバックをサポート。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/Mac/FreeBSD）での差分を吸収して優先度設定、CPU affinity 設定を提供。権限不足や未対応環境では安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレーク処理）
    - calc_equal_weights（等額配分）
    - calc_score_weights（スコア正規化、全スコア 0 の場合は等配分にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存ポジションを考慮したセクター上限チェック。unknown セクターは除外しない）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく乗数。未知レジームは警告して 1.0 にフォールバック）
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes（risk_based / equal / score の割当方式、lot_size による丸め、aggregate cap のスケールダウン、cost_buffer の考慮、各種パラメータ）

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）を出力。
    - 合否判定の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200ms）を定義。
    - --from / --to / --db オプションをサポート。

- リサーチ（開始実装）
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum / MA200 / ATR / Volume 指標計算の定義・定数を追加。DuckDB を利用する設計。
    - （一部実装途中の関数あり）

### Changed
- 監視・実行の設計意図を明確化
  - run_monitoring は監視専用 DB（monitoring テーブル）を確実に初期化するため、init_monitoring_db を起動時に呼び出すよう実装。
  - run_execution は paper_trading 環境で DB を分離することで本番データと完全に区別する設計を採用。

- ログ出力
  - StreamHandler を stdout に向ける設計により、cron などからの stdout/stderr のリダイレクト運用に適応。

### Fixed
- .env パースの堅牢化（src/kabusys/config.py）
  - export プレフィックス、クォートされた値内のバックスラッシュエスケープ、インラインコメント判定などに対応し、より実運用に耐えるパーサに改善。

- Process priority の安全性強化（src/kabusys/utils/process_priority.py）
  - 未対応 OS や権限不足時に例外を投げず警告でスキップするように修正。

### Deprecated
- なし

### Removed
- なし

### Security
- なし（機密情報は .env に保存する運用を想定。 .env のコミット禁止をドキュメント内で明記）

---

補足（運用上の注意）
- デフォルトの DB / ログ / PID / フラグパスは data/ および logs/ 以下に設定されています。初回起動時に親ディレクトリが無ければ警告が出ますが、多くのケースで起動時に自動作成されます。
- 自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます。1 秒未満や非整数は無視されデフォルト 60 秒にフォールバックします。
- Paper Trading モードを使用する場合は PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE（instant/partial/never/reject）などの設定を確認してください。

既知の TODO / 制約
- position_sizing の価格フォールバック（price_map の欠損時に前日終値等を使う）は未実装（TODO コメントあり）。
- research モジュールは一部未完（ファクター計算の続きが必要）。必要に応じて追加実装が必要です。
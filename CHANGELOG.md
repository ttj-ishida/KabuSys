CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- (なし)

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基礎機能を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBroker を用い、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離します。起動時にプロセス優先度を "high" に設定し、停止フラグ(data/stop_requested.flag)・PID 管理(data/execution.pid)に対応します。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計になっています。停止フラグ検知で安全に終了します。
- 設定管理
  - config.py: 環境変数読み込み・ラッパー Settings クラスを追加。.env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）と、必要変数取得ヘルパーを提供。PAPER_FILL_MODE のバリデーションや各種パス・閾値プロパティを実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。既存 .env 読み取り、シークレットマスク表示、保存時のテンプレート生成を行います。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パスや config/*.yaml の存在・パース（PyYAML 利用時）などを検証。--strict モードで警告も失敗扱いにできます。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを追加。LOG_DIR/LOG_LEVEL の解決ロジックとファイルハンドラ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: Windows/Linux/macOS の差分を吸収するプロセス優先度設定ユーティリティを追加。set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。アクセス権限等で失敗した場合は警告ログでスキップします。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を追加。スコアが全てゼロの場合のフォールバック挙動を含む。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。unknown セクターの扱い、レジームのデフォルトフォールバックを定義。
  - portfolio/position_sizing.py: position sizing ロジックを追加。allocation_method = "risk_based" / "equal" / "score" に対応し、lot_size（単元株）、cost_buffer、aggregate cap によるスケールダウンロジック、端数処理（lot 単位の再配分）を実装。
  - portfolio/__init__.py: 主要関数をエクスポート。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。期間フィルタ指定 (--from / --to)、DB 指定 (--db / 環境変数 PAPER_TRADING_SQLITE_PATH) に対応。以下の判定閾値を定義:
    - 稼働率 (uptime) >= 99.0%
    - 注文成功率 (fill rate) >= 90.0%
    - 送信率 (send rate) >= 95.0%
    - P95 レイテンシ <= 200 ms
  - tools/__init__.py: パッケージ化のための空ファイルを追加。
- データベース / 分析統合
  - DuckDB 統合: duckdb 接続を受け取る設計（Execution/Monitoring/Research で利用）。
  - 監視 DB 初期化: init_monitoring_db 呼び出しを通じて監視用テーブルの存在を保証（冪等）。
- パッケージ情報
  - __init__.py: パッケージバージョン __version__ = "0.1.0" をセット。

Notes / 使用上の注意
- .env 自動読み込みはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config._parse_env_line はシングル/ダブルクォート対応、export KEY=val 形式、インラインコメントの考慮など実用的な .env パース機能を提供します。
- run_monitoring は Monitoring の性質上、KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用する設計です。run_execution は is_paper に応じて paper_sqlite_path を切り替えます。
- MONITOR_POLL_INTERVAL の値が不正 (整数でない、0 以下など) な場合はデフォルト 60 秒にフォールバックして警告を出力します。
- Logging 設定は既存ハンドラを一旦クリアしてから再設定するため、複数回 setup_logging を呼ぶ場合でも二重出力になりません。
- process_priority / cpu_affinity の設定は権限や OS により失敗することがあり、その場合は警告を出して処理を続行します。

Fixed
- (初回リリースのため該当なし)

Changed
- (初回リリースのため該当なし)

Deprecated
- (初回リリースのため該当なし)

Security
- (初回リリースのため該当なし)

参考: 主要 CLI
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---
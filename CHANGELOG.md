CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」を基本にしています。

0.1.0 - 2026-04-20
-----------------

Added
- 基本アプリケーションバージョンを追加（__version__ = 0.1.0）。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にループ終了。
    - Monitoring は実行環境にかかわらず本番用 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は Paper Trading 用の専用 SQLite（data/paper_trading.db を想定）を使用して本番 DB と分離。
    - 停止フラグ検知でエンジン停止、実行 PID ファイル管理。
    - BrokerClientFactory 経由のブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと実行スレッド管理。
- 設定関連 CLI
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
    - 秘匿項目はマスク表示、選択肢やデフォルトのサポート、保存確認。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック、KABUSYS_ENV=live 向けの追加ガード、--strict フラグ（警告を FAIL 扱い）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）などを算出してコンソールに出力。
    - 日付フィルタ (--from/--to) と DB パス指定 (--db) に対応。
    - 合格閾値（稼働率 99% 等）を実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定と重み計算（スコア順ソート、等金額配分、スコア加重配分）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: ポジションサイズ計算（risk_based / equal / score の各方式）、単元株（lot_size）丸め、aggregate cap によるスケールダウンロジック（残差調整で lot 単位の再配分）。
  - portfolio/__init__.py で上記関数をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux, macOS, FreeBSD) に対応。権限不足等は警告で無視。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。
- 設定読み込み
  - config.py:
    - .env 自動読み込み機構を追加（OS 環境変数 > .env.local > .env の優先順位）。
    - .env パースロジックを強化（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理など）。
    - Settings クラスに多数のプロパティを追加（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE の検証、paper_sqlite_path、pid/kill flag パス、閾値設定、env/log_level 判定便利プロパティなど）。
- データリサーチ
  - research/factor_research.py（ファクター計算モジュール）を追加（Momentum、Value、Volatility、Liquidity を想定）。DuckDB を用いる設計。注: ファイル末尾で実装途中の記述あり（本リリースでは一部未完）。

Changed
- ロギングの標準化:
  - すべての起動スクリプトで setup_logging を呼ぶ設計に統一。アプリケーション名を指定することで個別ログファイル（logs/<app_name>.log）を出力。
  - StreamHandler は stdout を使用（stderr ではない）。これにより Task Scheduler/cron 等でのリダイレクトが容易。
- プロセス起動時の優先度:
  - run_monitoring / run_execution で起動直後に set_process_priority("high") を呼ぶようにして、重要プロセスの優先度を上げる運用想定。
- DB ハンドリング:
  - Monitoring 初期化系は init_monitoring_db を通じて監視テーブル存在を保証（冪等）。Paper Trading 環境では paper_sqlite_path を使って本番 DB と完全分離。
- 設定検証の振る舞い:
  - validate_config により設定ファイル（config/*.yaml）の存在と YAML パースをチェック（PyYAML 未インストール時は警告を出してスキップ）。
  - KABUSYS_ENV=live の場合の注意喚起（LINE 設定、KILL_FLAG_CLEAR_ON_START の安全性）を追加。

Fixed
- 環境変数の数値パースの堅牢化:
  - MONITOR_POLL_INTERVAL の不正値を警告してデフォルトにフォールバックするように実装（run_monitoring._get_poll_interval）。
- ログディレクトリ作成失敗時のフォールバック:
  - ログディレクトリ作成に失敗した場合でも StreamHandler のみでログ出力を継続し、致命的エラーを回避するように変更。
- process_priority, set_cpu_affinity のエラー処理強化:
  - 権限不足や未対応 OS の場合は警告でスキップするようにして起動失敗を防止。

Known issues / TODO（コード内コメントに基づく）
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題あり。将来的に前日終値や取得原価などをフォールバック価格として使用する予定。
- portfolio/position_sizing:
  - 将来的には銘柄ごとの単元株（lot_size）をマスターに保持し、銘柄別 lot_map を受け取るように拡張する想定（現状は全銘柄共通の lot_size）。
- research/factor_research.py:
  - ファイル末尾が途中で切れており、一部関数実装が未完（本リリースでは設計と初期実装に留まる）。今後完成予定。
- 警告の扱い:
  - validate_config の --strict を使用しない場合、警告は EXIT 0 扱いとなるため注意（本番導入時は --strict での検証を推奨）。

Security
- シークレット値（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に記載し、.env を絶対にリポジトリにコミットしない旨を config_setup の生成コメントで明示。

その他
- ドキュメント / README の更新は本リリースに含まれていません。設定手順（.env 作成 → validate_config による検証 → 実行）は config_setup と validate_config の案内メッセージに従ってください。
- 本 CHANGELOG はコードの内容から推測して作成しています。実運用向けの詳細な変更履歴や責任者、テスト・マイグレーション手順等は別途ドキュメントで補完してください。
# Changelog

すべての notable な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。  
リリース履歴はセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-24

### Added
- 起動スクリプトを追加
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ開始スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止制御はプロジェクト直下の data/stop_requested.flag を監視して行う。
    - 監視処理は常に本番用 sqlite_path を使用する（KABUSYS_ENV に依存しない）。
    - プロセス起動時にプロセス優先度を "high" に設定。
    - sqlite3 / duckdb 接続の初期化とクリーンなクローズ処理を実装。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine のスレッド起動制御を実装。
    - 起動前/実行中に data/stop_requested.flag を監視し、安全に停止する機構を実装。
    - 実行用 PID ファイル管理（data/execution.pid）に対応。
- 設定管理・自動読み込み機能を追加
  - src/kabusys/config.py
    - .env ファイル（.env、.env.local）の自動読み込み機構を実装（OS 環境変数が優先）。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しない読み込み。
    - .env の行パーサー強化（export プレフィックス、クォート内エスケープ、インラインコメント等を考慮）。
    - 各種設定プロパティを提供（DB パス、PID パス、しきい値等）と検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
    - settings = Settings() の単一インスタンスをエクスポート。
- 設定検証 CLI を追加
  - src/kabusys/validate_config.py
    - .env と config/*.yaml の存在・妥当性チェック用 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルの検証、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば実行）などを実施。
    - --strict オプションで警告も失敗扱いにできる。
    - KABUSYS_ENV=live 時の本番向け警告（LINE 通知設定や Kill Switch の設定など）を実装。
- .env 作成ウィザードを追加
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成/更新できる CLI を提供。
    - 複数の設定項目定義（シークレット項目、選択肢、デフォルト、説明）を用意。
    - 既存 .env 読み込み、シークレットのマスク表示、書き込み前の確認を実装。
- Paper Trading 検証レポートツールを追加
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH 指定可）から集計して検証レポートを生成する CLI を実装。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。
    - P95 計算、期間フィルタリング、欠損テーブルに対するフォールバックに対応。
- ポートフォリオ構築関連の純粋関数群を追加
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限の適用(apply_sector_cap)、市場レジームに応じた投下資金乗数(calc_regime_multiplier) を実装。
  - src/kabusys/portfolio/position_sizing.py
    - 株数決定ロジック(calc_position_sizes) を実装（risk_based / equal / score に対応、単元株丸め、aggregate cap によるスケールダウン等）。
  - src/kabusys/portfolio/__init__.py で上記 API を公開。
- ロギングとプロセス制御ユーティリティを追加
  - src/kabusys/utils/logging_setup.py
    - ルートロガーの統一設定関数 setup_logging を実装。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。
    - LOG_DIR / LOG_LEVEL の解決順、ログディレクトリ作成失敗時のフォールバックを実装。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定(set_process_priority) と CPU affinity 設定(set_cpu_affinity) を実装（psutil を使用）。
    - Windows / POSIX(nice) を吸収し、権限不足や未対応 OS を安全にハンドリング。
- research/factor_research ベースを追加
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールの骨格（モメンタム / ボラティリティ / などを計算する方針と定数）を追加。DuckDB 参照方式を想定。

### Changed
- 初期アーキテクチャ設計を反映
  - 監視・実行・構成管理・検証・ツール・ポートフォリオ・ユーティリティ群を分割し、明確な責務でモジュール化。
  - run_monitoring と run_execution は起動時にプロセス優先度を高に設定するよう変更（重要処理の安定化を目的）。
  - ログ出力は stdout を使用するよう統一（cron/task scheduler での扱いを考慮）。

### Fixed
- .env パーサーの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理などのケースに対応。
- MONITOR_POLL_INTERVAL の不正値処理
  - 0 以下や非整数が設定された場合はデフォルト（60 秒）にフォールバックし、警告ログを出力するよう改善。

### Security
- .env ファイル作成時にシークレット項目をマスク表示（config_setup の対話 UI）し、.env を絶対に Git にコミットしない旨の注意書きを追加。

### Internal
- パッケージメタ情報を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

---

注記:
- 各 CLI スクリプト・ユーティリティは外部依存（psutil, duckdb, PyYAML 等）が必要な機能があるため、実行環境に応じて依存パッケージをインストールしてください。
- 本リリースは基盤機能（起動スクリプト、設定管理、検証ツール、ポートフォリオロジック、ユーティリティ）を揃えた初期版です。今後のリリースでファクター計算の詳細実装や ExecutionEngine の具体的な挙動、監視メトリクス拡充などを追加予定です。
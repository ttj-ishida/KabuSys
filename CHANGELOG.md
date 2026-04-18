# CHANGELOG

すべての注目すべき変更点を時系列で記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお本リリースではバージョン番号はパッケージメタデータ（src/kabusys/__init__.py）上で 0.1.0 に設定されています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18

Added
- 起動用スクリプトと運用ユーティリティ
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag の存在を検知して安全に停止。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用する設計。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - 起動前に停止フラグをチェックし、起動後はフラグ検知でエンジンを停止。
    - 実行中の PID を data/execution.pid に保存する仕組みを想定（Engine 側で pid_file を使用）。
- 設定管理
  - config: 環境変数・設定読み込みモジュールを追加。
    - プロジェクトルート（.git / pyproject.toml）を基準に自動で .env/.env.local を読み込む（OS 環境変数を保護して上書き制御）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースはシングル/ダブルクォートや export 形式、インラインコメントなどに対応。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、閾値、環境種別など）をプロパティ経由で取得できるようにした。値検証（有効な列挙値や数値変換）を含む。
- 設定支援 & 検証 CLI
  - config_setup: 対話式の .env 作成・更新ウィザードを実装。デフォルト・既存値の再利用、シークレットのマスク表示、最終確認と保存までカバー。
  - validate_config: 起動前検証ツールを実装。必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と PyYAML を用いた簡易パース検証、本番環境向けの追加ガードを行う。--strict フラグで警告をエラー扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。LOG_DIR/LOG_LEVEL の優先順解決、ファイル出力失敗時のフォールバック処理を実装。
  - utils/process_priority: プラットフォーム差分を吸収するプロセス優先度設定と CPU affinity 設定を提供。Windows / POSIX（Linux, Darwin, FreeBSD）をサポートし、権限不足などのケースでは警告を出してスキップする。
- ポートフォリオ構築ロジック（純関数群）
  - portfolio/portfolio_builder: BUY シグナルの候補選定（スコア降順・タイブレーク）、等金額配分、スコア重み配分（全スコア 0.0 の場合は等金額にフォールバック）を実装。
  - portfolio/risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームや "unknown" セクターに対するフォールバック挙動を定義。
  - portfolio/position_sizing: 株数決定ロジックを実装（allocation_method: "risk_based", "equal", "score" をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer の考慮、スケーリング後の端数処理（残差の大きい順に単元で再配分）を実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report: Paper Trading 用 SQLite から稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）等を集計してレポート出力するスクリプトを追加。閾値（稼働率 99%、成功率 90% 等）に基づく PASS/FAIL 判定機能を提供する。--from/--to/--db オプションをサポート。
- リサーチ（断片的）
  - research/factor_research: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity などのファクター計算を行うための基盤を追加（モジュールは部分実装、calc_momentum などの関数シグネチャと設計方針を含む）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- なし

Removed
- なし

Security
- 機密情報（API トークン・パスワード）は .env に保存する想定だが、config_setup のヘッダーに「.env は絶対に Git にコミットしないこと」と明記。自動ロード時に OS 環境変数を保護する仕組みを導入。

Notes / 実装上の注意点
- run_monitoring は Monitoring 用テーブル作成を保証する init_monitoring_db を呼び出すが、Monitoring は環境にかかわらず Settings.sqlite_path（本番 DB）を使うため、テストやローカル実行時は注意が必要。
- run_execution は paper_trading 環境で paper_sqlite_path を使用し DB を分離するが、設定ミスにより本番 DB を参照すると危険なので validate_config と config_setup での確認を推奨。
- process_priority / set_cpu_affinity はプラットフォーム権限に依存するため、アクセス権限不足時は無害にスキップして警告を出す設計。
- portfolio の位置付け・算出ロジックには TODO コメントや将来の拡張（銘柄別 lot_size、価格フォールバック等）が残されている。運用前にパラメータ（risk_pct, stop_loss_pct, max_position_pct, lot_size, cost_buffer 等）のチューニングを推奨。
- research/factor_research は設計方針と定数を含むが、関数実装の一部が未完（calc_momentum の途中）であるため、使用前に完成させる必要がある。

--- 

開発者向けヒント
- ローカルでのテスト実行時は KABUSYS_ENV を "development" に設定し、Paper Trading の挙動を試す際は "paper_trading" を使用してください。  
- .env/.env.local の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。  
- ログはデフォルトで stdout に出力され、logs/<app_name>.log に日次ローテートで保存されます（logs ディレクトリの作成に失敗した場合はコンソールのみで継続します）。

（初版: 0.1.0）
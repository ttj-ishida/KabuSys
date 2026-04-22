CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
リリース日はソースコードから推測した日付です。

[0.1.0] - 2026-04-22
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のデーモンスレッド起動。  
    - 停止フラグ（data/stop_requested.flag）検出によるグレースフルシャットダウン、PID ファイル管理、プロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。  
    - 監視は本番用 sqlite_path を常に使用する挙動（環境に依存しない）。  
    - 停止フラグ検知、check_once() の例外ハンドリング、DuckDB 接続、プロセス優先度向上。
- 設定関連
  - config.py: 環境変数/設定管理モジュールを追加。  
    - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）に基づく .env 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。  
    - .env のパースは export 形式やクォート・エスケープ・コメントを考慮した堅牢な実装。  
    - Settings クラスにプロパティ化された設定群（J-Quants / kabu API / DB パス / ログ等）と入力検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。  
  - config_setup.py: 対話式 .env 作成ウィザードを追加（既存 .env 読み込み、シークレットマスク、確認後保存）。  
  - validate_config.py: 起動前に .env および config/*.yaml の設定不備を検出する CLI を追加（--strict オプションにより警告を失敗扱いにできる）。  
    - 必須環境変数チェック、KABUSYS_ENV の整合性チェック、DB パスや YAML ファイルの存在・パース検証、live 環境時の追加注意喚起。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。  
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）を併用、既存ハンドラのクリア、ログディレクトリ自動作成と失敗時のフォールバックを実装。  
    - ログレベル/ログディレクトリの解決優先順を実装。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定関数を追加（psutil ベース、権限不足や未対応 OS では警告を出してスキップ）。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。  
    - スコアが全て 0 の場合は等金額配分にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）。  
    - 未知セクターや未知レジームのフォールバック挙動を明記。
  - portfolio/position_sizing.py: 株数決定ロジック（calc_position_sizes）。  
    - risk_based / equal / score の割当方式に対応。  
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（利用可能現金）でのスケールダウン、コストバッファ考慮、残差処理による追加配分ロジックを実装。
  - portfolio/__init__.py: 上記 API をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（P95 等）を集計し PASS/FAIL を判定（閾値はソース内定義）。  
    - --from / --to / --db オプションで期間・DB パス指定可。PAPER_TRADING_SQLITE_PATH 環境変数を利用可能。
- 研究モジュール（ファクター計算）
  - research/factor_research.py: DuckDB を用いたモメンタム等のファクター計算モジュールのスケルトンを追加（momentum 等の定数・設計方針を含む）。  
    - prices_daily / raw_financials を参照する設計。Zスコア正規化等を想定。
- パッケージメタ情報
  - __init__.py: パッケージバージョンを 0.1.0 に設定。

Changed
- （該当なし）初期リリースのため変更履歴は追加項目のみ。

Fixed
- （該当なし）初期リリースのため修正項目はなし。

Notes / 実装上の注意
- .env 自動読み込みはプロジェクトルートを .git または pyproject.toml から検出するため、配布後（パッケージ化後）も CWD に依存せず動作する設計。ただし検出できない場合は自動ロードをスキップします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- run_monitoring は監視用 DB として Settings.sqlite_path（本番想定）を使用します。paper_trading の場合でも監視テーブルは本番 DB を用いる点に注意してください。一方 run_execution は paper_trading 環境では専用の paper_sqlite_path を使用して本番 DB と完全分離します。
- process_priority / cpu_affinity は psutil と OS 権限に依存します。権限不足や未対応プラットフォームでは警告を出して安全にスキップします。
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合はコンソール出力のみで継続するフォールバック実装があります。

Acknowledgements
- 本 CHANGELOG は提供されたソースコードからの推測に基づき作成しています。実際のリリースノート作成時には README やリリース差分（コミット履歴）を参照して補完してください。
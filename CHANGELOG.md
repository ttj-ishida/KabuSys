# Changelog

すべての注記は Keep a Changelog の形式に従い、セマンティックバージョニングを想定しています。  
本ファイルはコードベースの内容から推測して作成した初期リリースの変更履歴です。

なお、バージョン番号はパッケージ定義 (src/kabusys/__init__.py の __version__) に合わせています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-19
初回公開リリース。自動売買システム「KabuSys」の基盤機能を実装。

### Added
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db を想定）を使用し MockBroker を利用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にエンジンを停止する仕組みを実装。
    - 実行用 PID ファイル (data/execution.pid) をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用して監視データを記録（環境に依存しない動作）。
    - 停止フラグ（data/stop_requested.flag）によるループ終了対応と KeyboardInterrupt 対応。

- 設定・環境管理
  - config.py: 環境変数・設定読み込みモジュールを追加。  
    - プロジェクトルート自動検出（.git または pyproject.toml 基準）に基づいて .env 自動読み込みを行う（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
    - .env パース機能（export プレフィックス、クォート対応、インラインコメント処理）を実装。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / paper trading 関連 / 監視閾値 / ログレベル等）。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）や KABUSYS_ENV の検証（development/paper_trading/live）を実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 各種設定項目（実行環境、API トークン、DB パス、LOG_LEVEL、Kill Flag 設定など）を対話的に設定・保存。
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と PyYAML を用いたパース検証、KABUSYS_ENV=live 時の追加警告などを行う。
    - --strict モードで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定・重み計算（score / equal）を実装。
  - portfolio/position_sizing.py: 発注株数計算（allocation_method: risk_based / equal / score）を実装。  
    - lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリング、残差配分ロジックを実装。
  - portfolio/risk_adjustment.py: セクター集中上限（apply_sector_cap）と市場レジームによる乗数（calc_regime_multiplier）を実装。  
    - Unknown セクターの扱い、レジームに対するデフォルトフォールバックを含む。

- 監視・記録基盤
  - monitoring モジュールと monitoring_db 初期化フック（実行スクリプトから呼ばれる想定）を追加（run_monitoring / run_execution から初期化呼び出しあり）。
  - DuckDB を分析用に使用するための接続サポート（duckdb パッケージを利用）。

- ユーティリティ
  - utils/logging_setup.py: ロギング初期化ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。既存ハンドラのクリアを行い二重設定を防止。
    - LOG_DIR / LOG_LEVEL / 引数による上書き対応、ログディレクトリ作成失敗時のフォールバック。
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティを追加。  
    - Windows と POSIX(Linux/Mac/FreeBSD) を吸収、psutil を使って nice/priority を設定。失敗時は警告ログでフォールバック。
    - set_cpu_affinity によるコア固定機能を提供。

- ツール
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ指標（平均・最大・P95）を算出し PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - --from / --to / --db CLI オプション対応。

- リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（DuckDB を用いた Momentum/Value/Volatility/Liquidity の計算を想定）。  
    - モメンタム計算関数（calc_momentum）の導入（prices_daily テーブルを参照）および計算パラメータ定義を含む。実装はプロジェクト設計に沿った形で開始済み。

### Changed
- 既存設計（コードベース初期導入のための振る舞いを明文化）
  - run_* スクリプトの起動時に最初に set_process_priority("high") を呼び出し、プロセス優先度を高めに設定するように統一。
  - run_execution.py 内で paper_trading と production DB を明確に分離。paper_trading 時は paper_sqlite_path を使用。

### Fixed
- .env パーサーの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント（クォートなしの場合の扱い）を考慮して .env を正確に読み込むように修正。
  - _load_env_file の protected 引数により OS 環境変数の上書きを防止する仕組みを導入。

- ロギングの堅牢化
  - ログディレクトリ作成失敗時にファイルハンドラをスキップしコンソール出力のみで継続するように変更。

- process_priority のフォールバック
  - 未対応 OS や権限不足時に例外で落ちないように警告ログでスキップするように修正。

### Documentation / Misc
- パッケージ __init__.py に __version__ = "0.1.0" を設定。
- 各モジュールに docstring と使用例 / 設計ノートを充実させ、リポジトリ内ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）との参照を示すコメントを追加。

---

Semantic Versioning に基づき、後続のリリースでは「Added / Changed / Fixed / Deprecated / Removed / Security」カテゴリで差分を追記してください。
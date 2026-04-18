# Changelog

すべての重要な変更は Keep a Changelog の規約に従って記載しています。  
このファイルはコードベースから推測した変更点・導入機能を基に作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回リリース。本リリースでは自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築ロジック、検証ツール類をまとめて導入しています。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。プロセス優先度の設定、SQLite / DuckDB 接続、Broker クライアント生成、ExecutionEngine のスレッド実行／停止監視を行う（ファイル: src/kabusys/run_execution.py）。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番用 sqlite_path を使用（ファイル: src/kabusys/run_monitoring.py）。

- 設定管理・初期化
  - Settings クラス: 環境変数から各種設定を取得する集中管理（src/kabusys/config.py）。以下を含む:
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - 環境モード判定（development / paper_trading / live）および is_dev/is_paper/is_live のユーティリティ
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）
    - 監視閾値や PID / kill flag パスなど
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

- 設定支援 / 検証 CLI
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI（src/kabusys/config_setup.py）。
  - validate_config.py: .env と config/*.yaml を起動前に検証する CLI。必須環境変数チェック、パスの存在確認、YAML パースチェック、`KABUSYS_ENV=live` 向けのガードチェックを実施（src/kabusys/validate_config.py）。

- ロギング / プロセス管理ユーティリティ
  - setup_logging: ルートロガーの統一設定。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を自動設定。LOG_DIR / LOG_LEVEL の解決、既存ハンドラのクリアに対応（src/kabusys/utils/logging_setup.py）。
  - process_priority: Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティ。権限や未対応 OS の場合は警告を出してスキップ（src/kabusys/utils/process_priority.py）。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: シグナルの選別（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）（src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター集中上限適用（apply_sector_cap）および市場レジームに応じた投下資金乗数計算（calc_regime_multiplier）（src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: 各銘柄の発注株数算出（risk_based / equal / score の配分方式、単元丸め、aggregate cap のスケーリング、手数料・スリッページバッファ考慮）（src/kabusys/portfolio/position_sizing.py）。
  - ポートフォリオモジュールのトップレベルエクスポート（src/kabusys/portfolio/__init__.py）。

- Paper Trading 検証ツール
  - paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から集計して検証レポートを生成する CLI。稼働率、注文成功率、送信率、レイテンシ（P95）などを計算し PASS/FAIL 判定を行う。しきい値はソース内定数として定義（src/kabusys/tools/paper_verification_report.py）。

- リサーチ（計算基盤の投入）
  - factor_research.py（実装途中）: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを計算するモジュールの導入（src/kabusys/research/factor_research.py）。（注: ファイルは途中で切れているため本リリース時点で未完成の関数あり）

- パッケージメタデータ
  - バージョン設定（src/kabusys/__init__.py: __version__ = "0.1.0"）

### Changed
- データベース運用方針の明確化
  - 監視（run_monitoring）は KABUSYS_ENV に関わらず本番用 sqlite_path（Settings.sqlite_path）を使用する仕様に明記。
  - 実行エンジン（run_execution）は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH（Settings.paper_sqlite_path）を使用して本番 DB と分離する設計を採用。

### Fixed
- .env パースの堅牢化（src/kabusys/config.py）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、コメント扱いの判定を改善して .env の多様な記法に対応。

### Documentation / UX
- config_setup の対話ウィザードはシークレット入力をマスク表示し、既存値の再利用・デフォルト提示をサポート。
- validate_config は --strict モードを提供（警告も FAIL 扱い）し、出力で INFO/WARNING/ERROR を整理して表示。
- run_monitoring と run_execution はプロセス優先度を起動時に high に設定するようになっており、起動ログに環境情報を出力。

### Notes / Known limitations
- factor_research.py は一部実装が未完（ファイルの末尾が途中で切れています）。ファクター計算機能は今後のリリースで完成予定。
- process_priority の適用は権限が必要な場合や未対応 OS ではスキップされ、警告が出力されます。
- position_sizing の単元（lot_size）は現状全銘柄共通（デフォルト 100）であり、将来は銘柄ごとの単元対応を想定している旨の TODO コメントあり。
- run_monitoring と run_execution は stop/kill フラグ（data/stop_requested.flag, data/kill.flag）や PID ファイルを使った起動/停止制御を行う設計。運用時はプロジェクトディレクトリ下の data ディレクトリ構成と権限に注意してください。

---

完全な変更履歴や差分はソース管理履歴（例: Git のコミットログ）を参照してください。上記は現行ソースコードから推測してまとめた CHANGELOG です。必要であれば各項目をさらに分割して詳細（影響ファイル、使用例、移行手順）を追加できます。
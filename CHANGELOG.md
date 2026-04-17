CHANGELOG
=========

All notable changes to this project will be documented in this file.
フォーマットは "Keep a Changelog" に準拠します。

v0.1.0 — 2026-04-17
-------------------

初回リリース。KabuSys の基礎機能（設定管理、起動スクリプト、監視、実行エンジン周辺、ポートフォリオ構築・ポジションサイジング、研究用ファクター計算、ユーティリティ、各種 CLI ツール）を含みます。

Added
- 基本情報
  - パッケージバージョンを __version__ = "0.1.0" として追加（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数/ .env 読み込みの自動化を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み。
    - .env パーサは export KEY=val 形式、シングル／ダブルクォート、インラインコメント、バックスラッシュエスケープをサポート。
    - OS 環境変数を保護するための上書き制御（override / protected）を実装。
  - Settings クラスを追加し、主要な設定値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）をプロパティ経由で安全に取得する仕組みを提供。
    - PAPER_FILL_MODE のバリデーション（instant / partial / never / reject）。
    - KABUSYS_ENV の許容値検証（development / paper_trading / live）。
    - 監視・kill フラグ等のパス設定、しきい値（CPU/MEM/ディスク）の設定を提供。

- 設定ウィザード & 検証ツール（CLI）
  - .env の対話式作成・更新ウィザードを追加（src/kabusys/config_setup.py）。
    - 各項目の説明、デフォルト、シークレット入力扱い、保存の確認機能を提供。
  - 起動前設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV の警告/エラー、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML がある場合）、
      本番向けガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の確認）を実装。
    - --strict オプションで警告も FAIL 扱いにできる。

- 実行・監視用スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - 起動時にプロセス優先度を "high" に設定する呼び出し。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db）を使用し、本番 DB と完全分離する動作。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止制御（stop flag / PID 管理）を行う。
    - RiskManager デフォルト設定を明示（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する仕様（監視 DB は本番の稼働状況を参照するため）。
    - stop_requested.flag による外部停止検出、監視 DB 初期化（init_monitoring_db）を行う。

- 監視 DB 初期化（モジュール参照）
  - monitoring_db 初期化呼び出しが run_monitoring/run_execution から行われる（冪等に監視テーブルを保証）。

- Paper Trading 関連ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し PASS/FAIL を判定。
    - P95 計算、日付フィルタ（--from / --to）、DB パスの cli/環境変数指定をサポート。
    - デフォルト基準値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - 候補選定 select_candidates（score 降順、同点は signal_rank の小さい方を優先）。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等金額にフォールバックして WARNING ログ）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクターごとの既存エクスポージャーが上限を超える場合、新規候補の除外処理。
    - calc_regime_multiplier: market regime に応じた投入資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 にフォールバック）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - allocation_method ("risk_based" デフォルト) による株数算出（lot_size に丸め、max_position_pct や max_utilization、cost_buffer を考慮した aggregate cap のスケーリング実装）。
    - aggregate cap 再配分ロジック（残差に基づき lot 単位で追加配分するアルゴリズム）を実装。

- 研究用ファクター計算
  - factor_research（src/kabusys/research/factor_research.py）
    - DuckDB を使って momentum / volatility / liquidity 等のファクターを計算する関数群を実装（prices_daily, raw_financials テーブル参照）。
    - モメンタム: 1M/3M/6M リターン、200日移動平均乖離率の計算（ウィンドウチェック）。
    - ボラティリティ: ATR、相対 ATR、20日平均売買代金、出来高比等（NULL 伝播の扱いに注意）。

- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX 系を吸収する set_process_priority(level)（"high"/"normal"/"low"）を提供。アクセス権限不足や未対応 OS では警告を出して安全にフォールバック。
    - set_cpu_affinity(cpu_count) による CPU コア固定を実装（PermissionError 等は警告でスキップ）。

Changed
- なし（初回リリースのため変更履歴はありません）。

Fixed
- MONITOR_POLL_INTERVAL の取り扱い強化（src/kabusys/run_monitoring.py）
  - 環境変数の値が整数でない、あるいは 0 以下のときは警告を出してデフォルト（60 秒）にフォールバックする安全処理を追加。
- .env パーサの堅牢化（src/kabusys/config.py）
  - 引用符付き文字列のバックスラッシュエスケープ処理、インラインコメント解析、export プレフィックス対応により .env の誤解析を減らす。

Deprecated
- なし。

Removed
- なし。

Security
- 環境変数ファイル (.env) の扱いに関する注意を CLI ヘルプ・ウィザード内で明示（.env を絶対に Git にコミットしないよう警告）。

Breaking Changes / Important Notes
- 監視（run_monitoring）は「環境にかかわらず本番 sqlite_path を使用する」設計です。期待する動作と異なる場合は設定（SQLITE_PATH）を確認してください。
- KABUSYS_ENV=paper_trading の際は実行エンジンが paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。Paper Trading 用 DB を明示していないとデフォルトパスが使われます。
- process_priority / cpu_affinity の設定は OS 権限に依存します。権限不足では警告が出て設定はスキップされます。

Usage examples (抜粋)
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH=path/to/db.sqlite を指定可能

Authors
- KabuSys 開発チーム

Acknowledgments
- この CHANGELOG はソースコードの内容から推測して作成されています。実際のリリースノート作成時は差分やコミットログを参照して調整してください。
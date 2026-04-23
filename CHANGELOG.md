# Changelog

すべての注目すべき変更はここに記録します。  
このファイルは "Keep a Changelog" の構成に従います。  

## [Unreleased]

## [0.1.0] - 2026-04-23

### Added
- 全体
  - 初期リリースを追加。ライブラリのバージョンは `kabusys.__version__ = "0.1.0"`。
  - プロジェクト構成に合わせた自動 .env 読み込み機能（プロジェクトルート検出）を実装（src/kabusys/config.py）。
  - .env ファイルの対話式作成・更新ウィザードを追加（src/kabusys/config_setup.py）。
  - 起動前に環境設定を検証する CLI を追加（src/kabusys/validate_config.py）。
  - ログ共通セットアップユーティリティを追加（src/kabusys/utils/logging_setup.py）。
  - プロセス優先度と CPU affinity のユーティリティを追加（src/kabusys/utils/process_priority.py）。
- 実行 / 監視
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は MockBroker を利用し、paper_trading 用 DB にデータを分離して記録する仕組みをサポート。
    - PID ファイル管理および data/stop_requested.flag による外部停止制御を実装。
    - ExecutionEngine の起動時に依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てる処理を追加。
  - SystemMonitor 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番の sqlite_path を使用して監視データを記録する設計（monitoring 用 DB 初期化処理を呼び出す）。
    - stop フラグ検出で安全にループを終了。
- データベース / 分析
  - DuckDB / SQLite 接続を前提とするユーティリティと初期化処理を導入（Monitoring DB 初期化呼び出しを各スクリプトで実行）。
- ポートフォリオ構築
  - 銘柄選定・重み算出ロジックを提供（src/kabusys/portfolio/portfolio_builder.py）。
    - 候補選定（スコア降順 + タイブレーク）、等金額配分、スコア加重配分を実装。
  - セクター集中制限とレジーム乗数を提供（src/kabusys/portfolio/risk_adjustment.py）。
    - 既存ポジションのセクター別エクスポージャに基づく新規候補除外（unknown セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
  - 株数決定・リスク制限・単元株丸めロジックを提供（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の割当方式をサポート。
    - per-stock 上限、aggregate cap、lot_size 単位での切り捨て・残余配分ロジック、cost_buffer による保守的見積りを実装。
- 研究・指標
  - ファクター計算モジュール（Momentum 等）の土台を追加（src/kabusys/research/factor_research.py）。DuckDB を用いた時系列計算を想定。
- ツール
  - Paper Trading 用検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を算出し PASS/FAIL 判定を行う。
    - デフォルト DB パスは `data/paper_trading.db`、環境変数 `PAPER_TRADING_SQLITE_PATH` またはコマンドライン `--db` で上書き可能。
- パッケージ公開関連
  - パッケージの public API を定義（src/kabusys/portfolio/__init__.py, src/kabusys/__init__.py）。

### Changed
- .env 自動読み込みの挙動を明確化（src/kabusys/config.py）
  - プロジェクトルートは .git または pyproject.toml を基準に探索するため CWD に依存しない。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - OS 環境変数は protected として上書き不可にする保護機構を導入。
- ロギング
  - 共通の logging 設定で StreamHandler を stdout に送り、ファイルは TimedRotatingFileHandler（日次、30 日保持）で出力（src/kabusys/utils/logging_setup.py）。
  - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続するフォールバックを実装。
- プロセス優先度 / CPU affinity
  - Windows / POSIX (Linux, macOS, FreeBSD) を吸収するクロスプラットフォーム実装（src/kabusys/utils/process_priority.py）。
  - 権限不足や未対応プラットフォーム時は警告出力して安全にスキップする挙動とした。
- 実行フロー
  - run_execution/run_monitoring が起動時にプロセス優先度を先に設定するための手順を統一。

### Fixed
- .env パーサの改善（src/kabusys/config.py）
  - export プレフィックス、クォート文字列内のバックスラッシュエスケープ、インラインコメントルール（クォートあり/なしの違い）に対応してより堅牢にパースするよう修正。
  - 不正な .env 行は無視する安全策を実装。
- MONITOR_POLL_INTERVAL の扱い（src/kabusys/run_monitoring.py）
  - 環境変数の不正値（非整数や 0 以下）が指定された場合、警告を出してデフォルト（60 秒）にフォールバックするよう修正。
- calc_score_weights のフォールバック（src/kabusys/portfolio/portfolio_builder.py）
  - 全銘柄スコアが 0.0 の場合に等金額配分へフォールバックし、警告ログを出力するように改善。
- apply_sector_cap の挙動（src/kabusys/portfolio/risk_adjustment.py）
  - unknown セクターの銘柄はセクター上限判定の対象外とする設計を明文化。
- position sizing の scaling ロジック（src/kabusys/portfolio/position_sizing.py）
  - aggregate cap 超過時のスケーリング後、lot_size 単位で端数処理をし、残余キャッシュで端数配分（fractional remainder）を行うアルゴリズムを導入。
- Paper Trading 分離（src/kabusys/run_execution.py）
  - paper_trading 環境時に専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離するよう実装。

### Security
- .env 作成ウィザードの出力ファイルに関する注意書きを追加（src/kabusys/config_setup.py）
  - .env を絶対に Git にコミットしない旨を明記。
- validate_config に本番環境向けのガード条件を追加（src/kabusys/validate_config.py）
  - KABUSYS_ENV=live の場合、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険な設定を警告するチェックを実装。

### Documentation / UX
- CLI の使い方 / ヘルプを各スクリプトに整備（config_setup、validate_config、paper_verification_report 等）。
- 各モジュールに docstring を整備し設計方針・使用上の注意（例: PortfolioConstruction.md 参照箇所）を明記。

---

今後の改善候補（未実装 / TODO）
- position_sizing: 銘柄別 lot_size を持つ設計への拡張（stocks マスタによる lot_map）。
- risk_adjustment: price 欠損時のフォールバック価格（前日終値や取得原価）を使ったエクスポージャ見積りの改善。
- factor_research: 各ファクターの完全実装・テスト・DuckDB 上での最適化。
- ExecutionEngine / Broker クライアント周りのテスト強化とフェールオーバー戦略の追加。

（以上）
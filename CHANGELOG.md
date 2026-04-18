# Changelog

すべての変更点は「Keep a Changelog」形式に従って記載しています。日付は本リリースの作成日です。

リリースノート要約:
- 初回公開リリース v0.1.0（2026-04-18）
- 自動売買システムのコアユーティリティ、CLI、実行/監視ランナー、ポートフォリオ構築、リスク制御、検証ツールなどを含む初期実装を追加。

## [Unreleased]

（次回以降の変更をここに記載）

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初期パッケージ公開。パッケージバージョンは kubusys.__version__ = "0.1.0" に設定。
  - DuckDB / SQLite を用いたデータ保存・分析基盤の統合（設定経由でパス指定可能）。
  - ログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout 出力用 StreamHandler と日次ローテーション（30日保持）の TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL を環境変数や引数で解決可能。
- 設定管理
  - 環境変数の自動読み込み（.env / .env.local）機能を追加（kabusys.config）。
    - プロジェクトルート検出は .git または pyproject.toml を基準に探索。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env のパースはシングル/ダブルクォート、エスケープ、コメント対応。
  - Settings クラスを導入し、各種設定（J-Quants トークン、kabuAPI、DB パス、Paper Trading 設定、監視閾値など）をプロパティとして取得可能に。
    - PAPER_FILL_MODE（instant/partial/never/reject）検証を実装。
    - PAPER_TRADING_SQLITE_PATH / SQLITE_PATH / DUCKDB_PATH / PID/KILL フラグ等の既定値を提供。
    - env ロジック（development / paper_trading / live）とログレベル検証を実装。
  - 対話式 .env 作成ウィザード CLI を追加（kabusys.config_setup）。
    - .env の読み書き・既存値の利用・シークレットマスク表示・保存確認をサポート。
- 実行・監視ランナー
  - Execution エンジン起動用スクリプトを追加（kabusys.run_execution）。
    - プロセス優先度を "high" に設定する呼び出しを最初に行う。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（分離）を使用する挙動をサポート（settings.is_paper）。
    - BrokerClientFactory によるブローカークライアント生成（Paper 環境では MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をデーモンスレッドで実行。停止フラグ（data/stop_requested.flag）を監視して安全停止。
    - 実行用 PID ファイル管理（data/execution.pid）と停止フラグにより外部からの制御が可能。
  - Monitoring ポーリングループ起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告を出力。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計（監視用 DB は production path）。
    - stop フラグファイル検知による安全なループ停止と例外ハンドリングを実装。
- 監視 DB 初期化
  - init_monitoring_db（kabusys.monitoring.monitoring_db の想定）を呼び出し、監視テーブルの冪等初期化を行うフローを導入（run_execution / run_monitoring で利用）。
- プロセス制御ユーティリティ
  - プロセス優先度設定と CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows と POSIX（Linux / Darwin / FreeBSD）差分を吸収して nice 値／Windows 優先度クラスを設定。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。
    - 権限不足や未対応 OS 時は警告ログでスキップ。
- ポートフォリオ構築（純粋関数群）
  - 候補選定と重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights（全スコア 0 の場合は等金額フォールバック）。
  - セクター集中・レジーム調整（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存ポジションのセクターごとの時価を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム毎の乗数 (bull=1.0, neutral=0.7, bear=0.3)。未知レジームは 1.0 にフォールバック（警告）。
  - ポジションサイズ計算（kabusys.portfolio.position_sizing）
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づき、lot_size（単元）丸め、1銘柄上限、aggregate cap（available_cash） を考慮して発注株数を算出。
    - サンクション：cost_buffer（手数料・スリッページ見積）、scale-down（available_cash を超えた場合のスケーリング）や残差処理を実装。
- 研究モジュール
  - ファクター計算モジュール（kabusys.research.factor_research）の骨格を追加。
    - Momentum（1M/3M/6M、MA200乖離）、ATR 等、一定の定数と関数インターフェースを定義（DuckDB 接続を受け取り SQL/Python で計算する設計）。
- 検証ツール
  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認・パース（PyYAML がない場合は警告）などを実装。
    - --strict フラグで警告を FAIL 扱いにできる。
- Paper Trading 向け検証レポート
  - tools/paper_verification_report.py を追加。
    - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）からデータを読み、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して PASS/FAIL を判定する CLI。
    - デフォルト閾値（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 latency <=200ms）を実装。
    - 日付フィルタ（--from / --to）や --db オプション対応。
- パッケージ構成
  - kabusys.portfolio、kabusys.tools、kabusys.utils、kabusys.research 等のパッケージ構成を整備。__all__ エクスポートを定義。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注記・実装上の重要ポイント（設計上の想定挙動／利用上の注意）
- 自動環境読み込みはプロジェクトルートが見つからない場合はスキップされるため、配布環境では明示的に環境変数を設定すること。
- run_monitoring は「監視用」プロセスとして本番 sqlite_path を常に用いる設計になっているため、テスト時は環境変数 SQLITE_PATH を適切に切り替えること。
- run_execution は paper_trading 環境で paper_sqlite_path を使用することで発注系データを完全に分離する。
- ファイルベースの停止制御（data/stop_requested.flag、data/execution.pid、data/kill.flag 等）により外部プロセス管理・障害時の安全停止を行う設計。
- process_priority や CPU affinity の設定は権限依存のため、権限不足時は警告を出してスキップする。

必要であれば、各モジュールごとの詳細な API リファレンスや使用例、既知の制限点（例えば price が欠損した際のエクスポージャー過小評価問題の TODO）を別途作成します。どのモジュールから詳しくドキュメント化するか指示してください。
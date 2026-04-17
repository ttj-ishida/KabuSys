# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載します。  
本ファイルはリポジトリ内のソースコードから機能・振る舞いを推測して生成した変更履歴です。

## [Unreleased]

- 今後の変更記録用。

## [0.1.0] - 2026-04-17

初回リリース。以下の主要機能・ユーティリティ・CLI を含みます。

### Added
- 全体
  - パッケージ初期バージョンを導入（kabusys v0.1.0）。
  - 基本的なパッケージ構成（execution, monitoring, portfolio, research, tools, utils 等）を実装。

- 設定・環境読み込み
  - Settings クラスによる環境変数ベースの設定取得機能を実装（kabusys.config）。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み機能を追加。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。

- .env パーサー
  - 強化された .env 行パーサーを実装（引用符・エスケープ・export プレフィックス・コメント処理に対応）（kabusys.config._parse_env_line）。
  - .env ファイル読み込み時の保護オプション（既存 OS 環境変数を上書きしない protected set）を追加。

- 環境設定ウィザード CLI
  - 対話式 .env 生成/編集ウィザードを提供（kabusys.config_setup）。
  - J-Quants / kabuAPI / DB パス / LINE / ログレベル / Kill Switch 等の推奨項目をサポート。
  - 既存値の読み込み、シークレットマスク表示、保存前の確認を実装。

- 設定検証 CLI
  - 起動前に環境変数や config/*.yaml の存在/簡易妥当性を検証する CLI を追加（kabusys.validate_config）。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、PyYAML の有無による YAML 検査の有効化・警告出力を実装。
  - --strict オプションで警告も失敗扱いにする機能を追加。

- 実行/監視プロセス起動スクリプト
  - ExecutionEngine 起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading の場合、ペーパートレード用独立 SQLite（data/paper_trading.db）を使用して本番 DB と分離する仕様を導入。
    - BrokerClientFactory を利用してブローカークライアントを生成（設定に応じて MockBrokerClient を用いる想定）。
    - OrderRepository / OrderManager / Reconciler / RiskManager（RiskConfig をデフォルトで設定）を組み立て、ExecutionEngine をスレッドで実行。
    - execution.pid および stop フラグ（data/stop_requested.flag）による起動制御・停止処理を実装。
  - SystemMonitor 起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は常に本番用 sqlite_path を使って監視 DB を初期化・接続する設計（init_monitoring_db を実行）。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しを実行スクリプトに組み込み、監視用テーブルの存在を保証（冪等処理）。

- プロセス優先度 / CPU affinity ユーティリティ
  - set_process_priority(level) を実装し、Windows / POSIX（Linux/Mac/FreeBSD）の差分を吸収して優先度設定を行う（kabusys.utils.process_priority）。
  - set_cpu_affinity(cpu_count) を実装（指定コア数にカレントプロセスを固定する。未対応 OS や権限不足時は警告を出してスキップ）。
  - 実行スクリプトで起動直後にプロセス優先度を "high" に設定する運用を採用。

- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: score 降順＋signal_rank によるタイブレークで候補を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率による重み。全スコアが 0 の場合は等金額にフォールバックして警告。
  - リスク調整（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: セクター集中上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームはログ警告のうえ 1.0 でフォールバック。
  - ポジションサイジング（kabusys.portfolio.position_sizing）
    - calc_position_sizes: risk_based / equal / score の allocation_method に対応。
    - 単元株（lot_size）で丸めるロジック、1 銘柄上限（max_position_pct）、総投下上限（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残差配分アルゴリズムを実装。
    - 価格欠損時のスキップや 0/不正値対策のログ記録。

- 研究用ファクター計算
  - ファクター計算モジュールを実装（kabusys.research.factor_research）。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB の prices_daily を用いて計算（ウィンドウ不足時は None）。
    - calc_volatility: ATR20、相対 ATR、20 日平均売買代金、出来高比率等を計算するクエリを用意。
    - DuckDB 接続を受ける設計で、表（prices_daily, raw_financials）以外には副作用を持たない純粋関数的実装。

- Paper Trading 検証ツール
  - paper_verification_report CLI（kabusys.tools.paper_verification_report）。
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）に対して、稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計してレポート出力。
    - 閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定ロジックを搭載。
    - SQL 実行失敗（テーブル未作成など）に対する安全なハンドリングを実装（OperationalError を捕捉して N/A を出力）。

### Changed / Improved
- .env のパース挙動を強化
  - 引用符付き値内のバックスラッシュエスケープ処理、引用符閉じの検出、インラインコメント処理（非引用値で '# ' の前をコメントとして扱う）を実装。これによりより堅牢な .env パースが可能に。

- 設定検証の利便性向上
  - PyYAML が未インストールの場合は YAML 検証をスキップし警告を出力することで、依存性がない環境でも基本検証が行えるように変更。

- ロバストネス強化
  - 監視ループで monitor.check_once() が例外を投げてもループを継続するように例外捕捉とログ出力を追加（kabusys.run_monitoring）。
  - run_execution / run_monitoring の終了時に DB 接続（sqlite3, duckdb）を確実にクローズするよう finally ブロックを追加。
  - 設定ウィザードでの中断（EOF/KeyboardInterrupt）時に適切にメッセージを出す等の UX 改善。

### Fixed
- 環境変数読み込みの上書き制御のバグ回避
  - .env 読み込み時に OS 環境変数を誤って上書きしないための protected キーセットを導入し、安全に override の挙動を制御。

### Notes / Implementation details
- run_execution は RiskConfig のデフォルト値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を用いて RiskManager を初期化し、broker.get_available_cash() を initial_portfolio_value に設定することで初期リスクパラメータを決定します。
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数から取得し、1 未満や非整数等の不正値はデフォルト（60 秒）にフォールバックして警告ログを出力します。
- portofolio/risk_adjustment の apply_sector_cap は price_map に価格が欠損（0.0）するとエクスポージャーが過小見積りされる旨の TODO コメントを残しています（将来的なフォールバック価格導入の注記）。

---

既知の制約や拡張余地についてはソース内ドキュメント（docstrings / TODO コメント）に注記しています。必要であれば、CHANGELOG の記載をさらに細分化（ファイル単位の変更履歴追加、バグ修正の詳細化など）して更新できます。
CHANGELOG
=========

すべての変更は「Keep a Changelog」準拠で記載しています。  
主な項目: Added / Changed / Fixed / Removed / Deprecated / Security

Unreleased
----------

- （現時点のコードベースに対する未リリースの変更はありません）

0.1.0 - 2026-04-18
------------------

Added
- プロジェクト初期版を追加（バージョン: 0.1.0）。
- 全体
  - パッケージ初期構成を追加。主要モジュール群（config, utils, portfolio, execution, monitoring, research, tools）を実装。
  - バージョン情報を kabusys.__init__ にて定義（__version__ = "0.1.0"）。

- 環境・設定
  - Settings クラス（kabusys.config）を実装し、環境変数から設定値を取得する仕組みを提供。
    - 自動 .env ロード機能: プロジェクトルート (.git または pyproject.toml を起点) が見つかれば .env と .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パースの強化: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱いルールを導入。
    - 多数の設定プロパティを提供（DB パス、API トークン、監視閾値、ログレベル、環境種別判定など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - 対話式環境設定ウィザード（kabusys.config_setup）
    - .env の初期生成・更新を支援する CLI を実装。シークレットのマスク表示、選択肢・デフォルト提示、保存確認機能を備える。
  - 設定検証ツール（kabusys.validate_config）
    - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML がある場合は）パース検証を実行。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定警告）。
    - --strict モードで警告を失敗扱いにできる。

- ロギング・プロセス管理
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）を設定。
    - LOG_LEVEL / LOG_DIR の優先解決を実装し、ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU アフィニティユーティリティ（kabusys.utils.process_priority）
    - Windows と POSIX（Linux/macOS/FreeBSD）を吸収する抽象的な set_process_priority 実装（high/normal/low）。
    - CPU コア数固定用 set_cpu_affinity。権限不足や未サポート環境は警告を出して安全にスキップ。

- 実行・監視起動スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - プロセス優先度を最初に high に設定。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH による上書き可能）。
    - BrokerClientFactory によるブローカークライアント作成を想定。OrderRepository / OrderManager / RiskManager / Reconciler を組み上げ、ExecutionEngine を別スレッドで起動。
    - 停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）に対応。停止検知時にエンジン停止処理を実行。
    - RiskManager のデフォルト構成例を含む（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。initial_portfolio_value は broker.get_available_cash() を使用。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - 同様にプロセス優先度を high に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告。
    - 監視は環境にかかわらず production の sqlite_path を使用する設計（監視データは本番 DB に一元）。
    - 停止フラグ（data/stop_requested.flag）の検知でループを終了。check_once() の例外は捕捉してログ出力し継続。

- データベース・分析基盤
  - DuckDB を分析用 DB として利用（Settings.duckdb_path）。
  - 監視テーブルの初期化ユーティリティ（init_monitoring_db を呼び出す場所を run_* で確保）。

- ポートフォリオ構築
  - portfolio.portfolio_builder
    - select_candidates: スコア降順、同点は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額にフォールバックして警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有セクター比率が max_sector_pct を超える場合、同セクターの新規候補を除外（"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応。
    - 単元株（lot_size）丸め、per-position と aggregate の上限（max_position_pct / max_utilization）を考慮。
    - cost_buffer を使った保守的なコスト見積り、投下合計が available_cash を超える場合はスケールダウンし、残余キャッシュで lot 単位の再配分を行う（端数処理で再現性を確保）。

- Paper Trading 検証ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH デフォルト: data/paper_trading.db）から各種指標を集計してレポート出力。
    - 取得指標: システム稼働率（system_status）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（平均/最大/P95）。
    - P95 計算、閾値比較による PASS/FAIL 判定、日付フィルタ (--from/--to) をサポート。

- 研究用モジュール（部分実装）
  - research.factor_research
    - ファクター計算の設計方針を導入（DuckDB 接続を受け SQL/Python で計算、momentum/value/volatility/liquidity 等）。
    - モーメンタム系 (calc_momentum) の雛形を追加（実装は継続／拡張を想定）。関数設計はターゲット日を基準に過去リターンや MA200 乖離率を計算する仕様。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- 外部に漏洩してはならない値（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に保存する設計。config_setup にて .env を生成する際に「.env は絶対に Git にコミットしないこと」と注記。

Notes / 既知の制約
- run_monitoring は監視データの格納先として常に Settings.sqlite_path（デフォルト: data/monitoring.db）を使用する設計。テスト用途に分離したい場合は別途設定が必要。
- position_sizing 内の price が欠損（0.0）の場合はエクスポージャーが過少見積もられる可能性があり、将来的に前日終値や取得原価のフォールバックを検討する旨の TODO を含む。
- research.factor_research は設計方針と一部の実装を含むが、完全実装は継続作業が必要。

今後の予定（例）
- research.factor_research の完全実装（Value / Volatility / Liquidity ファクター）。
- テストカバレッジ強化、各モジュールのユニットテスト追加。
- 実稼働時の運用ガイド（デプロイ手順・監視アラート設定）の整備。
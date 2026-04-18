# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお本CHANGELOGは与えられたコードベースの内容から機能追加・動作仕様・注意点を推測して記載しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下は主要な追加点・仕様です。

### Added
- 基本パッケージとバージョン
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
- 環境設定管理
  - Settings クラスを実装し、環境変数から各種設定（J-Quants / kabu API トークン、DB パス、Paper Trading モード、監視閾値など）を取得するAPIを提供。
  - 自動 .env ロード機能を追加（プロジェクトルートに .env / .env.local があれば読み込む）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース処理を静的に実装（export プレフィックス、シングル/ダブルクォート中のエスケープ、インラインコメント処理などに対応）。
- 設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで .env を作成・更新する CLI を追加。各項目の説明と既存値の再利用、シークレットマスキング表示などをサポート。
- 設定検証 CLI
  - `kabusys.validate_config`：.env と config/*.yaml（存在する場合）の事前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、live 環境用ガード（LINE 通知設定や Kill Switch 設定の注意喚起）を実施。--strict オプションで警告を失敗扱いにできる。
- 実行系起動スクリプト
  - `run_execution.py`：ExecutionEngine の起動スクリプトを追加。起動時にプロセス優先度を High に設定し、SQLite / DuckDB 接続の初期化、Broker クライアントの生成、OrderManager/RiskManager/Reconciler の組立てを行い、別スレッドでエンジンを実行。Paper Trading 時は専用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離する設計。
  - 停止制御としてプロジェクト内の data/stop_requested.flag を監視し、フラグ検知時に安全に停止する仕組みを実装。実行 PID の書き出しに対応（data/execution.pid を使用）。
- 監視系起動スクリプト
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックし警告を出す）。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
  - 監視ループ内で停止フラグ（data/stop_requested.flag）を検知して安全に終了。check_once() の例外はロギングして次ポーリングへ継続。
- DB 初期化ユーティリティ
  - 監視用の SQLite テーブル等を初期化する init_monitoring_db を利用して冪等に監視 DB の準備を行う呼び出しを実装（Execution / Monitoring 起動時）。
- 実行・リスク管理コンポーネント（骨格）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）などの組立てを実装するエントリポイントを追加（詳細な実装は別モジュールに依存）。
  - RiskConfig の初期値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をデフォルトで設定。initial_portfolio_value を broker.get_available_cash() から取得して初期化。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選択し上位 N を返す（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を計算（{code: 1/N}）。
    - calc_score_weights: スコア比率で重みを計算。全スコアが 0.0 の場合は等金額配分にフォールバックして警告をログ出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェックにより過剰セクターの新規候補を除外。unknown セクターは制限を適用しない。売却予定銘柄はエクスポージャー計算から除外。
    - calc_regime_multiplier: 市場レジームに基づく資金乗数（bull=1.0, neutral=0.7, bear=0.3）を提供。未知のレジームは警告とともに 1.0 を返す。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき銘柄ごとの発注株数（lot_size 単位）を計算。ポジション上限、利用可能現金によるスケーリング、aggregate cap によるスケールダウン、端数処理（remainders による追加配分）を実装。price が欠損時はスキップするロジックを備える。
  - portfolio パッケージを公開（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。
- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX に対応したプロセス優先度設定を実装（Windows の HIGH_PRIORITY_CLASS 等は getattr でフォールバック）。権限不足等で失敗した場合は警告ログを出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留めする機能を追加。未対応 OS や権限不足時は警告を出してスキップ。
- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum / calc_volatility（実装途中まで提供）: DuckDB の prices_daily テーブルを参照してモメンタム（1m/3m/6m、MA200乖離）や ATR や流動性指標を計算する関数を追加。欠損データやウィンドウ不足に対する扱いを定義。
    - 設計方針により、DuckDB 経由での SQL + Python のハイブリッド計算を採用し、外部APIへの依存はない。
- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB から system_status、trade_logs、risk_logs を集計し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を計算して PASS/FAIL を判定する。閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ（--from / --to）をサポートし、期間を ISO8601 形式に変換してクエリを行う。DB が存在しない場合はエラーを表示。
- DuckDB / SQLite の採用
  - 分析用に DuckDB を使用し、実行/監視データや研究データをそれぞれの DB ファイルで保持する設計を採用。

### Changed
- 実行と監視の DB 分離設計
  - run_execution: Paper Trading 実行時は paper_sqlite_path（data/paper_trading.db）を使用し、発注ログ等を本番 DB と完全分離するよう変更（設定に基づく）。
  - run_monitoring: 監視は環境に関わらず本番 sqlite_path を使用する旨を明記。
- .env の読み込み順と保護
  - OS 環境変数を保護しつつ .env（.env.local）を読み込む。読み込み順は OS > .env.local > .env。既存 OS 環境変数は上書きされない（明示的に override=True の場合は protected を除いて上書き可能）。

### Fixed
- 環境変数パースの堅牢化
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、コメント判定の細やかな扱いなどを実装し、一般的な .env 形式での誤パースを防止。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - 環境変数 MONITOR_POLL_INTERVAL が整数でない、または 1 未満の値だった場合に警告を出しデフォルト（60 秒）にフォールバックするようにして time.sleep の ValueError を防止。

### Known issues / Notes
- position_sizing 内で price が 0.0（欠損）の場合、エクスポージャーが過小評価されてブロックが外れる可能性がある点を TODO コメントで記載。将来的に前日終値や取得原価などのフォールバック価格導入を検討する必要あり。
- lot_size は現在全銘柄共通（デフォルト 100）で扱われる。将来的には銘柄別 lot_size を持たせる拡張が想定されている（TODO コメントあり）。
- research.factor_research の calc_volatility はファイル末尾で実装途中の可能性（与えられた抜粋では途中まで）。完全な集計ロジックは別途確認が必要。
- 実行エンジン / ブローカー実装の詳細（BrokerClientFactory や ExecutionEngine 本体）は別モジュール依存であり、本CHANGELOGはエントリポイント周りの仕様に基づく。

### Security
- 機密値（トークン / パスワード）は .env に保存する想定。config_setup にて .env ファイルの Git コミット禁止を明記。

---

作成日: 2026-04-18

（注）本CHANGELOGは提供されたソースコードのコメント・実装内容から推測して作成しています。実際の変更履歴やコミットメッセージがある場合は、それらを優先して正確な履歴に更新してください。
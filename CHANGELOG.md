# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はソース内の __version__ を基にしています。

## [Unreleased]

（現時点の差分はありません）

## [0.1.0] - 2026-04-17

初回リリース。本リリースでは、環境設定、実行/監視用の起動スクリプト、ポートフォリオ構築ユーティリティ、研究用ファクター計算、ユーティリティ類、検証・設定支援ツールなど、システム運用に必要な主要機能を提供します。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 環境変数 / 設定管理
  - kabusys.config.Settings クラスを実装。環境変数から各種設定を取得するプロパティ群を提供（J-Quants / kabu API / LINE / DB パス / 監視・しきい値設定 / 実行環境判定 等）。
  - .env 自動読み込み機能を実装。プロジェクトルート（.git または pyproject.toml）を探索し `.env` と `.env.local` を読み込む（OS 環境変数は保護）。
  - `.env` 読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパースは export 形式、クォート（シングル/ダブル）やエスケープ、インラインコメントを考慮した堅牢な実装。

- 設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を初期作成/更新するツールを追加。
  - デフォルト値、選択肢、シークレット入力の扱い、保存時の確認プロンプトを提供。
  - `.env` に書き込む際、重要事項（.env をコミットしない等）をヘッダに出力。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前に環境変数および `config/*.yaml` を検査するツールを追加。
  - 必須環境変数チェック、KABUSYS_ENV 値検証、LOG_LEVEL 検証、DB パスの親ディレクトリチェック、YAML ファイルの存在／パース検証（PyYAML がインストールされている場合）等を実行。
  - `--strict` オプションで警告も失敗（exit 1）として扱う。

- 実行エンジン起動スクリプト
  - `run_execution.py`：ExecutionEngine の起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を用いて paper_trading 専用 SQLite DB（デフォルト `data/paper_trading.db`）を使用し本番 DB と完全分離。
    - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててExecutionEngineを起動。PID ファイル、停止フラグ（data/stop_requested.flag）による制御をサポート。
    - RiskManager のデフォルト設定（max_position_pct 等）を設定し、初期利用可能現金は broker.get_available_cash() から取得。

- 監視（Monitoring）起動スクリプト
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは production DB を想定）。
    - 停止フラグ検知でループを安全に終了。例外発生時はロギングして次ポーリングへ継続。

- モニタリング DB 初期化
  - `monitoring_db.init_monitoring_db` を呼び出して監視テーブルの存在を保証（冪等な初期化）。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio.portfolio_builder`
    - BUY シグナルから候補選定（スコア降順、同点は signal_rank）`select_candidates`。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコア 0 の場合は等分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 `apply_sector_cap`：既存保有比率に基づき同一セクターの新規候補を除外（"unknown" セクターは対象外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" のマッピング、未知レジームはフォールバックで 1.0）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数計算 `calc_position_sizes`：allocation_method に応じて risk_based / equal / score の算出をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）と残差処理（lot 単位で再配分）、cost_buffer（手数料・スリッページ見積）を考慮。
    - 価格欠損時のスキップ、0 価格対策などを実装。

- リサーチ（ファクター計算）
  - `kabusys.research.factor_research`
    - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルを用いてファクターを計算する関数群を提供。
    - モメンタム（1M/3M/6M）、200日移動平均乖離率、ATR（20 日）、20日平均売買代金、出来高比率等を計算。データ不足時の None 扱いなどの堅牢性を考慮。

- ツール：Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）を読み、システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポートを出力。
    - 基準値（稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を行う。
    - 日付フィルタ（--from/--to）や --db オプションをサポート。
    - データ欠損（テーブル不存在等）は例外ハンドリングして N/A を出力。

- ユーティリティ
  - `kabusys.utils.process_priority`
    - プロセス優先度設定ユーティリティを実装。Windows と POSIX（Linux/Mac/FreeBSD）を透過的に扱う。
    - set_process_priority(level: "high"|"normal"|"low")：psutil 経由で優先度を設定。権限不足や未対応 OS では警告ログを出力してスキップ。
    - set_cpu_affinity(cpu_count: Optional[int])：最初の N コアにプロセスをピン留め（不足時の挙動、エラー時の警告を実装）。

### 変更 (Changed)
- 設定ロード順序・保護
  - .env 自動ロード時に OS 環境変数を保護しつつ `.env`（override=False）→ `.env.local`（override=True）の順に読み込む実装により、ローカルオーバーライドを可能に。

### 修正 (Fixed)
- 入力検証とフォールバックの強化
  - MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の環境変数について妥当性チェックを追加。無効値はログで警告しデフォルトにフォールバックまたは例外を投げる（必須値は例外）。
  - ポジションサイズ計算、セクター露出計算などで価格欠損時の安全なスキップやデバッグログを追加。
  - paper_verification_report の P95 計算・NULL 考慮を実装。テーブルが存在しない場合に備えたエラーハンドリングを追加。

### 既知の制限 (Known issues)
- 一部の実装（例: monitoring_db の詳細、SystemMonitor / ExecutionEngine / Broker の内部実装）は本リリースのスコープ外または別ファイルに分離されており、ここでは呼び出し側の起動制御・初期化ロジックのみを提供。
- position_sizing の lot_size は全銘柄共通で固定（将来的に銘柄別単元対応を予定）。
- price が欠損（0.0）の場合、エクスポージャーが過小見積になる可能性がある旨をログコメントで指摘。フォールバック価格ロジックは未実装。

--- 

開発者メモ:
- デフォルト DB 路径や各種閾値は Settings クラスを通じて環境変数で柔軟に変更できます。運用時は validate_config と config_setup を用いて事前検証・セットアップを行ってください。
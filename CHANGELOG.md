# Changelog

すべての変更は Keep a Changelog の形式に従います。  
バージョン 0.1.0 はプロジェクト初期リリースとして、コア機能（設定管理、起動スクリプト、ポートフォリオ構築ロジック、ユーティリティ、検証/ウィザード、Paper Trading 検証ツール等）をまとめて導入しています。

## [0.1.0] - 2026-04-18

### 追加
- 全体
  - 初期リリース。パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用は実行環境（KABUSYS_ENV）にかかわらず本番用の `sqlite_path` を使用して DB に接続する仕様。
    - 停止はプロジェクトディレクトリ下 `data/stop_requested.flag` の存在で検知。
    - duckdb への接続を確立し、監視 DB 初期化を実施。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用の MockBrokerClient を使用し、paper_trading 用 DB (`data/paper_trading.db` など) にデータを分離して記録。
    - 停止フラグ（`data/stop_requested.flag`）および実行 PID ファイル管理を実装。
    - エンジンは別スレッドで実行し、停止フラグ検知で安全に停止する制御を実装。

- 設定管理
  - config.py
    - 環境変数読み込み機能を追加（プロジェクトルートの `.env` / `.env.local` を自動で読み込む。OS 環境変数を優先）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` オプションを追加。
    - `.env` の読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して実行。
    - .env パーサーが `export KEY=val`、クォート値のエスケープ、インラインコメントルール等に対応。
    - Settings クラスを導入し、環境変数の取得をプロパティ経由で行う設計に変更（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path` 等）。
    - `paper_fill_mode` に入力値検証を導入（有効値: "instant", "partial", "never", "reject"）。
    - 監視閾値等（CPU/MEM/DISK）のデフォルト値をプロパティで定義。
    - `env` / `log_level` の妥当性検証を実装（無効値は ValueError）。

  - config_setup.py
    - 対話式ウィザードを追加。`.env` の初期作成・更新を支援。
    - シークレット項目はマスク表示、選択肢・デフォルト値表示、キャンセル時の動作などユーザーフレンドリな対話を実装。
    - `.env` ファイルのテンプレート書き出し機能を含む。

  - validate_config.py
    - 設定検証 CLI を追加。`.env` と `config/*.yaml`（存在する場合）の基本チェックを実行。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在確認等を行う。
    - PyYAML が利用可能な場合は YAML ファイルのパース検証を行う（未インストール時はスキップして警告）。
    - `--strict` オプションを追加（警告も FAIL として扱う）。

- Paper Trading ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB から期間指定でレポートを生成する CLI を追加。
    - システム稼働率（system_status）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、
      API レイテンシ（P95 等）を集計し PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を備える。
    - P95 計算、NULL 値・テーブル未存在時のフォールバック処理を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（score 降順、signal_rank によるタイブレーク）、候補選択関数を実装。
    - 等金額配分（calc_equal_weights）・スコア加重配分（calc_score_weights）を実装。全スコアが 0.0 の場合は等分配にフォールバック。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター比率に基づき新規候補を除外可能。
    - セクターが "unknown" の場合は上限適用対象外とする挙動を明記。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（"bull"/"neutral"/"bear" マッピング、未知レジームはフォールバック）。

  - portfolio/position_sizing.py
    - position sizing ロジックを実装（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer（コスト余裕）の考慮、残余キャッシュを利用した端数配分ロジックを実装。
    - 価格欠損時のスキップやログ出力、各パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size 等）を引数で指定可能。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保管）を設定。
    - ログレベル解決順（引数 > LOG_LEVEL 環境変数 > デフォルト）とログディレクトリ解決順（引数 > LOG_DIR 環境変数 > デフォルト logs/）を明示。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。

  - utils/process_priority.py
    - プロセス優先度（set_process_priority）と CPU affinity（set_cpu_affinity）設定ユーティリティを追加。
    - Windows（psutil の_PRIORITY_CLASS）と POSIX 系（nice 値）を抽象化して扱う。
    - 権限不足や未対応プラットフォームでは警告を出して安全にスキップする実装。

- リサーチ（骨格）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム、移動平均、ATR、流動性等の計算方針と定数を定義）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針を記載（実装途中/継続予定）。

### 変更
- なし（初期リリース）

### 修正
- .env パース
  - export プレフィックス・クォート・エスケープ・コメント解釈など実務的な .env フォーマットの取りこぼしを考慮するパーサー実装により、既存の単純なパースで想定外となるケースを回避。

### 既知の注意点 / マイグレーション
- run_monitoring は常に Settings.sqlite_path（本番用監視 DB）を使用するため、開発環境で監視 DB を分離したい場合は `SQLITE_PATH` を明示的に設定してください。
- Paper Trading 実行時は専用 DB（`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）を使用するため、本番 DB とデータは分離されます。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定すると自動で .env を読み込まないため、テストや特殊な起動時に便利です。
- `PAPER_FILL_MODE` 等、一部環境変数は値検証を行い、不正値は起動時例外になります。`.env.example` を参考に正しい値を設定してください。
- ログディレクトリの作成に失敗した場合はファイルローテーションは利用されずコンソール出力のみになります。その場合の警告は stderr に出力されます。

### セキュリティ
- `.env` は秘匿情報を含むため、書き出し時に README 等で「絶対に Git にコミットしない」旨を注記するテンプレートを生成。

---

今後の予定（例）
- factor_research の完全実装（モメンタム/バリュー/ボラティリティ/流動性の計算と正規化）
- ExecutionEngine / BrokerClient 周りの詳細実装と統合テスト
- 監視・アラート（LINE 通知）などの運用機能の強化
- 単体テスト・CI の整備

--- 

（必要であれば、各ファイルごとの変更差分や関数ごとの詳細目録を追記できます。どの粒度でドキュメント化するか指示してください。）
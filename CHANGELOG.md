# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョンはソース内の __version__ に基づきます。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 全体
  - プロジェクトの初期リリースとして、自動売買システム "KabuSys" のコア機能群を実装。
  - パッケージメタ情報として `__version__ = "0.1.0"` を設定。

- 設定管理
  - 環境変数・.env を読み込む Settings クラスを実装（`kabusys.config.Settings`）。
  - プロジェクトルート自動検出 `_find_project_root()` を実装し、.env/.env.local の自動読み込みを行う（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - .env ファイルのパース機能を強化（`export KEY=val` 形式、クォート文字とバックスラッシュエスケープ、インラインコメントの扱い対応）。
  - 各種設定プロパティを提供（DB パス、KABUSYS_ENV、LOG_LEVEL、各種閾値、paper_trading 用設定等）。
  - `paper_fill_mode` の検証（有効値: "instant" | "partial" | "never" | "reject"）。

- 環境セットアップ CLI
  - `.env` の対話式ウィザード `kabusys.config_setup` を追加。デフォルト / 既存値の再利用、シークレットマスク表示、保存機能を提供。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス（親ディレクトリ存在確認）、config/*.yaml の存在と YAML パース検査（PyYAML が存在しない場合は警告）、本番向けガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を実行。`--strict` オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - 監視用ランナー `kabusys.run_monitoring` を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用。停止フラグファイルを監視して安全に終了。
  - 実行エンジン起動スクリプト `kabusys.run_execution` を追加。KABUSYS_ENV=paper_trading 時は paper 専用 DB（`data/paper_trading.db` または環境変数で指定）と MockBroker を使用し、本番 DB と分離。ExecutionEngine をスレッドで実行し、停止フラグ検知で停止シグナルを送る。

- 実行・リスク管理
  - ブローカーファクトリ、OrderRepository/OrderManager、RiskManager, Reconciler, ExecutionEngine 等の組立てロジック（起動時に required コンポーネントを構築し起動）を実装。RiskManager に初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker など）を提供し、初期ポートフォリオ値は broker.get_available_cash() を利用。

- 監視 DB 初期化
  - `init_monitoring_db` を呼び出して監視テーブルの存在を保証（冪等性を想定）。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ `kabusys.utils.process_priority` を実装。Windows / POSIX の差異を吸収し、許可エラーや未対応 OS の場合は警告を出して安全にスキップ。`set_process_priority` と `set_cpu_affinity` を提供。

- ポートフォリオ構築（純粋関数群）
  - 候補選定と重み計算（`select_candidates`, `calc_equal_weights`, `calc_score_weights`）。
  - セクター集中度制限（`apply_sector_cap`）、レジームに応じた乗数（`calc_regime_multiplier`）。
  - ポジションサイズ計算（`calc_position_sizes`）:
    - リスクベース、等分配、スコア加重の割当方式をサポート。
    - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap とスケーリング処理を実装。
    - price 欠損時のスキップやログ出力等の堅牢性を確保。

- リサーチ（DuckDB ベース）
  - ファクター計算モジュール `kabusys.research.factor_research` を実装。Momentum、Volatility 等の定量ファクターを DuckDB の prices_daily / raw_financials テーブルから計算する機能を提供（MA200、各種リターン、ATR、平均売買代金など）。関数は DuckDB 接続を受け取り SQL で計算。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。paper_trading の SQLite DB を解析して稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値に基づき PASS/FAIL 判定を出力。コマンドラインで期間指定や DB パス指定が可能。

### 変更 (Changed)
- 設定自動読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。既存 OS 環境変数を保護するため protected セットを導入。
- run_monitoring / run_execution 起動時にプロセス優先度を最初に設定することで、起動直後の安定性を向上。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検知してデフォルトにフォールバックし、警告ログを出力するようにした。

### 修正 (Fixed)
- .env パースの挙動を強化し、引用符内のバックスラッシュエスケープを正しく扱えるようにした（これによりパスやトークン中のエスケープ文字が正しく復元される）。
- process_priority で未対応プラットフォームや権限不足による例外をキャッチしてログに警告を出し、起動を中断しないようにした。
- paper_verification_report の P95 計算や集計クエリで、テーブルが存在しない/データ不足の場合に sqlite3.OperationalError を捕捉し、安全に N/A 表示やゼロ扱いにフォールバックするようにした。

### セキュリティ (Security)
- .env の生成スクリプトで「.env は絶対に Git にコミットしないこと」を明示し、シークレット値はウィザード表示でマスクして扱う。

### 既知の制限 / TODO
- position_sizing の lot_size は現状すべての銘柄で共通の固定値（デフォルト 100）を使用。将来的には銘柄別 lot_map を受け取る拡張を予定。
- apply_sector_cap の価格欠損時の扱いに注記あり（price が 0.0 の場合、エクスポージャーが過少評価される可能性があるため将来的にフォールバック価格の導入を検討）。
- research モジュールは DuckDB のテーブル構成（prices_daily / raw_financials）に依存するため、入力データの前処理が必要。

---

（注）本 CHANGELOG は提供されたソースコードから推測して作成しています。リリース管理上の正式な履歴は実際のコミット履歴やリリースノートを優先してください。
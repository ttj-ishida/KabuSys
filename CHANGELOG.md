# CHANGELOG

すべての notable な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-23
初回公開リリース。KabuSys のコア機能と CLI ツール群、ユーティリティ、ポートフォリオ構築ロジック、ペーパートレード検証ツールを実装しました。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを導入（__version__ = "0.1.0"）。
  - DuckDB / SQLite を使ったデータ格納を前提とした各種ユーティリティと CLI を実装。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により実稼働／モックブローカを切り替え可能。
    - 実行中 PID ファイル（data/execution.pid）に対応。外部停止フラグ（data/stop_requested.flag）で安全停止。
    - リスクマネージャ（RiskManager）および Reconciler、OrderManager、OrderRepository の組み立てを行う。
    - duckdb（分析用 DB）接続を注入。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照して監視テーブルを管理。
    - 停止フラグ（data/stop_requested.flag）を検知して安全終了。

- 設定関連
  - config.py: 環境変数 / .env 読み込みと Settings クラスを導入。
    - プロジェクトルート検出（.git または pyproject.toml を起点）により .env 自動読込（.env → .env.local、OS環境変数を保護）。
    - .env のパースは export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメントなど多数のパターンに対応。
    - Settings より各種設定（J-Quants token、kabu API、DB パス、paper_trading 設定、監視閾値、環境種別判定など）をプロパティとして取得可能。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
  - config_setup.py: .env を対話形式で作成／更新するウィザードを追加。
    - 複数の項目定義、既存 .env 読み取り、秘密値マスク表示、保存前確認を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース確認、production 特有のガードチェックなどを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- Portfolio（銘柄選定・配分・サイズ決定）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N 件を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分を実装。スコア全0 の場合は等配分にフォールバックして警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に新規候補を除外するロジックを実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返すユーティリティを実装（未知レジーム時は 1.0 にフォールバックし警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づいた発注株数計算を実装。
      - 単元株ロジック（lot_size）対応、価格欠損時のスキップ、個別上限（max_position_pct、max_utilization）と aggregate cap のスケーリング処理。
      - cost_buffer を使った保守的なコスト見積りと、残余現金を使った端数の再配分ロジックを実装。

- ユーティリティ
  - utils.logging_setup: 共通ログのセットアップを実装。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。
    - ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR の解決ロジック。ファイル出力失敗時はコンソール出力のみで継続。
  - utils.process_priority: プロセス優先度／CPU affinity 設定ユーティリティを実装。
    - Windows と POSIX（Linux/Mac/FreeBSD）での差分を吸収。権限不足や未対応 OS 時は警告を出してスキップ。
    - set_process_priority("high" 等) と set_cpu_affinity(n) を提供。

- モニタリング DB 初期化
  - monitoring.monitoring_db:init_monitoring_db を使用して監視テーブルの存在を保証（冪等に実行）。

- Tools
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、成立率、送信率、リスク却下数、レイテンシ指標（avg/max/P95）を算出。
    - 判定閾値（稼働率99%、成立率90%、送信率95%、P95 <= 200ms）に基づく PASS/FAIL を出力。
    - 日付フィルタ (--from / --to) と DB パス指定 (--db) に対応。

- Research（下地）
  - research.factor_research: ファクター計算モジュールの骨組みを追加（モメンタム・ATR 等を想定）。DuckDB 接続を受け取る設計。実装は一部で継続作業を想定。

### 変更 (Changed)
- なし（初回リリースのため新規追加が主体）。

### 修正 (Fixed)
- なし（初回リリースにおける実装上の安全処理・例外処理を多数実装。例: ログディレクトリ作成失敗時のフォールバック、process priority 設定失敗時の警告、DB テーブルが存在しない場合のレポート生成耐性など）。

### 既知の制限 / 注意点 (Known issues / Notes)
- research.factor_research の実装は骨組みが含まれているが一部未完（calc_momentum 関数が途中で終端）。今後実装継続が必要。
- position_sizing の価格フォールバックは現状未実装（price が欠損した場合はスキップ）。将来的に前日終値や取得原価でのフォールバックを検討。
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされる。テスト環境等で KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能。
- run_monitoring は監視に本番 sqlite_path を利用する設計上、paper_trading 環境であっても監視 DB は分離されないため運用時の取り扱いに注意。

### セキュリティ
- 機密情報（トークンやパスワード）は .env に保存する設計。.env は Git に含めないことを強く推奨。
- config_setup の出力メッセージで .env を絶対にコミットしないことを明記。

---

今後の予定（例）
- factor_research の完全実装（各ファクター算出と正規化）。
- ExecutionEngine 内のセッション管理・注文再送ロジック・より詳細なモニタリング統合。
- 単元サイズや銘柄ごとの lot_size 管理を stocks マスタでサポート。
- テストカバレッジの追加と CI パイプライン整備。
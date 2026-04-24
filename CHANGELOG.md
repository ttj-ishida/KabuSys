# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このプロジェクトの初回リリース履歴を示します。

## [0.1.0] - 2026-04-24

### 追加 (Added)
- 基本アプリケーション構成
  - パッケージのエントリポイントを追加（kabusys.__version__ = "0.1.0"）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート。
    - ExecutionEngine を別スレッドで起動/監視し、data/stop_requested.flag の検知で安全に停止。
    - 実行中 PID を data/execution.pid に記録（設定で指定可能）。
    - デフォルトでプロセス優先度を "high" に設定（utils.process_priority）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）の検知でループを終了。
    - Monitoring は環境に依らず本番 sqlite_path を使用する挙動を採用。
    - SQLite / DuckDB 接続の初期化処理を実装し、例外発生時もポーリングを継続（ログ出力）。
- 設定管理
  - config.py: 環境変数管理クラス Settings を追加。
    - .env 自動ロード機能（プロジェクトルート判定: .git または pyproject.toml）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env/.env.local の読み込みルール（override/保護キー）を実装。
    - 複雑な .env パース（export プレフィックス、シングル/ダブルクォート、エスケープ、コメントルール）に対応。
    - 多数の設定プロパティ（J-Quants、kabu API、LINE、DUCKDB/SQLite パス、Paper Trading 設定、監視閾値、環境判定等）を提供。
    - PAPER_FILL_MODE の入力検証（"instant"|"partial"|"never"|"reject"）。
    - KABUSYS_ENV / LOG_LEVEL の検証と is_live / is_paper / is_dev ヘルパー。
  - settings オブジェクト（Settings のインスタンス）をエクスポート。
- 設定・検証ツール
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 主要な環境変数を対話的に設定して .env を生成。
    - 秘匿値のマスク表示、選択肢チェック、既存 .env の読み込みをサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 設定未設定や Kill Switch 関連の警告）。
    - --strict オプションで警告をエラー扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_DIR/LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみ継続。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応した優先度設定（"high"|"normal"|"low"）。
    - CPU affinity 固定機能 set_cpu_affinity を提供。
    - 権限不足や未サポート環境では警告を出して安全にフォールバック。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等金額・スコア加重）を実装。
    - select_candidates, calc_equal_weights, calc_score_weights（スコア全0 のフォールバックロジック含む）。
  - portfolio/risk_adjustment.py: セクター上限適用とレジーム乗数を実装。
    - apply_sector_cap: 既存保有を考慮したセクター露出計算と候補フィルタ。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に応じた乗数を返す（未知レジームはフォールバック）。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装。
    - allocation_method="risk_based" または "equal"/"score" をサポート。
    - リスクベースの株数計算、単元株（lot_size）丸め、per-position 上限、aggregate cap スケーリング（cost_buffer を考慮）。
    - 可用現金を超える場合のスケールダウンと端数処理アルゴリズムを実装。
  - portfolio/__init__.py で主要関数をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などの SQLite テーブルから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を計算。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。
    - --from/--to/--db オプションで期間・DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を優先して使用。
- 研究用モジュール（骨格）
  - research/factor_research.py: ファクター計算モジュールの骨格と定数を追加（モメンタム等の計算方針、DuckDB を用いた実装方針）。一部実装は継続中（ファイル末尾で切れている箇所あり）。

### 変更 (Changed)
- ログ出力の標準出力先に stdout を明示的に使用（cron / scheduler のリダイレクトを想定）。
- ロギング構成は全起動スクリプトで統一的に setup_logging を呼ぶことで一貫性を保つ設計に変更。
- .env 自動読み込み時の優先順位を明確化（OS 環境変数 > .env.local > .env）。.env.local は既存の OS 環境変数を保護しつつ上書き可能。
- run_monitoring の設計上、監視用 DB の初期化 (init_monitoring_db) を強制して監視テーブルが存在することを保証するようにした。

### 修正 (Fixed)
- N/A（初回リリース）

### 削除 (Removed)
- N/A（初回リリース）

### セキュリティ (Security)
- 秘匿値入力（config_setup）では画面表示でマスクを行うなど、運用上の秘匿性に配慮したUIを提供。

---

備考:
- 本 CHANGELOG はコードベースから推測して作成した初回リリースの要約です。実際のリリースノートにはテスト結果や互換性注意事項、既知の制限事項などを追記することを推奨します。
# Changelog

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

最新バージョン: 0.1.0 — 2026-04-18

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18

### 追加 (Added)
- プロジェクト初回リリース。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV による DB 分離: paper_trading 環境では settings.paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB とデータを分離。
    - BrokerClientFactory からブローカークライアントを生成（paper_trading 時は Mock 実装を利用する想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を起動。デーモンスレッドでセッションを実行し、停止フラグ（data/stop_requested.flag）で安全停止する。
    - 実行中の PID を data/execution.pid に記録する仕組み（設定でパスを上書き可能）。
- 監視用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし、警告ログを出力する。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を探索）。
    - .env/.env.local の読み込み順を実装（OS 環境変数を優先、.env.local は上書き可能）。
    - .env の行パーサを実装（export プレフィックス対応、シングル/ダブルクォート対応、インラインコメントの扱い）。
    - Settings クラスを追加し、主要な環境変数をプロパティ経由で取得できるように（例: duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode, pid_file_path, kill_flag_path, 各種スレッショルド等）。
    - 環境値の検証ロジック（有効な値範囲チェック、未設定時のエラー）を実装。
- 設定ウィザード & 検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成 / 更新を支援する CLI を実装。秘密項目はマスク表示。
    - .env テンプレート生成機能と保存処理（保存時に .env を上書き）。
    - README 的な注意（.env を Git にコミットしないよう明記）。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の不備を検出する検証ツールを実装。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML がない場合はスキップして警告）を実装。
    - --strict オプションで警告も失敗扱いにできる。
    - 本番（KABUSYS_ENV=live）向けの追加ガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の設定等）を実装。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター露出を計算して上限を超えるセクターの新規候補を除外。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear に対応、未知はフォールバックで警告）。
  - portfolio/position_sizing.py
    - 発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に合わせたスケーリング）、cost_buffer を考慮した保守的見積などを実現。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler, 30日保持）のファイルハンドラを設定。
    - ログディレクトリの自動作成と失敗時のフォールバック（コンソールのみ）を実装。
    - ログレベルは引数 > 環境変数 > デフォルト の順で解決。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定を実装（high/normal/low）。Windows/Linux/macOS に対応。psutil を利用し、権限不足などは警告で無視。
    - CPU affinity 設定ヘルパーも実装（set_cpu_affinity）。
- 分析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から各種指標（稼働率、注文成功率・送信率、リスク却下数、API レイテンシ）を集計して検証レポートを生成する CLI を追加。
    - コマンドライン引数で期間指定（--from, --to）と DB パス指定（--db）に対応。環境変数 PAPER_TRADING_SQLITE_PATH をデフォルトとして使用可能。
    - レポートの Pass/Fail 基準を定義（稼働率 >= 99.0%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
- 研究用モジュール（骨組み）
  - research/factor_research.py
    - モメンタム等のファクター計算モジュールの基盤（定数、設計方針）を追加。DuckDB を使った prices_daily / raw_financials 参照前提で calc_momentum 等の関数実装を開始（ファクター計算ロジックの骨格を含む）。
- パッケージメタ
  - __init__.py にてパッケージバージョンを 0.1.0 として設定。

### 変更 (Changed)
- なし（新規リリース）

### 修正 (Fixed)
- なし（新規リリース）

### 注意 / 既知の制約 (Notes / Known limitations)
- .env 自動ロードはプロジェクトルートが検出できない場合スキップされる（CI / 配布環境での挙動に注意）。
- process_priority の変更や CPU affinity の適用は権限やプラットフォームに依存するため、権限不足時は警告に留まり処理はスキップされる。
- portfolio や research の一部機能は外部データ（価格マップ、セクターマップ、DuckDB 内テーブル等）を前提としており、実運用前にデータ整備が必要。
- tools/paper_verification_report は DB スキーマに依存（system_status, trade_logs, risk_logs テーブル）。スキーマ不一致やテーブル未作成時は一部集計をスキップして N/A 表示となる。
- .env は機密情報を含むため、絶対にバージョン管理にコミットしないでください（config_setup でも注意書きを出力）。

### セキュリティ (Security)
- なし

---

この CHANGELOG はソースコードから推測して作成されています。実際のリリースノートとして配布する際は、差分コミットログやリリース管理情報に基づいて必要に応じて修正してください。
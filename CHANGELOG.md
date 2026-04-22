# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-22

初期リリース。KabuSys のコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築ロジック、検証ツール類を実装しました。

### 追加
- 実行 / 監視エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（data/paper_trading.db がデフォルト）を使用して本番 DB と完全分離。BrokerClientFactory により Mock ブローカーが利用可能（説明あり）。
    - エンジンはデーモンスレッドで run_session を実行。停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 実行中 PID の管理（data/execution.pid）をサポート。
    - RiskManager のデフォルト設定を組み込み（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず production 用の sqlite_path を使用する設計（意図的な挙動として明記）。

- 設定・起動補助
  - config.py
    - .env 自動読み込み（プロジェクトルートに .git または pyproject.toml がある場合）。
    - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント取り扱いなどに対応）。
    - Settings クラスを提供し、各種設定値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、閾値類、KABUSYS_ENV/LOG_LEVEL 判定など）をプロパティとして取得可能。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI を追加。シークレット項目はマスク表示、Enter で既存値やデフォルトを採用、保存時にテンプレートヘッダを付与。
  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数やパス、YAML 設定ファイルの存在とパース検証（PyYAML 未インストール時は警告）を行い、--strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、既定 30 日保存）をルートロガーに設定する共通関数を追加。LOG_DIR 環境変数や引数でログ出力先を指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。
  - utils/process_priority.py
    - psutil を利用してプロセス優先度（high/normal/low）を設定するユーティリティを追加。Windows（priority class）と POSIX（nice 値）を吸収する実装。CPU affinity を固定する関数も提供。権限不足や未対応 OS では警告ログを出してスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバックして警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存ポジションのセクター別エクスポージャーを計算し、上限を超えるセクターの新規候補を除外。regime に応じた乗数（calc_regime_multiplier）も実装（bull/neutral/bear→1.0/0.7/0.3、未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - 株数算出ロジック（calc_position_sizes）を実装。allocation_method による分配（risk_based, equal, score）をサポートし、lot_size（単元）で丸め、per-stock と aggregate の上限を考慮。投資総額が利用可能現金を超える場合はスケーリングと端数配分ロジックを実装。

- ツール・レポート
  - tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト data/paper_trading.db）の検証レポート生成スクリプトを追加。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を集計し、しきい値に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB 存在チェック、SQL 実行時の例外ハンドリングを実装。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - Momentum 等のファクター計算モジュールを追加（DuckDB 接続を受け prices_daily / raw_financials テーブルを参照する設計）。（モジュール内に設計方針と定数を明記）

### 変更
- 初期実装として各機能の設計方針やドキュメント文字列をコード内に詳細に追加。将来的な拡張ポイント（例: 銘柄別 lot_size、価格フォールバックなど）を TODO コメントで明記。

### 修正
- .env のパース精度向上
  - export プレフィックス・クォートやバックスラッシュエスケープ、インラインコメントの取り扱い等に対応して不正な読み取りを防止。
- ログ設定
  - ログディレクトリ作成が失敗した場合にファイルハンドラ作成をスキップし、コンソール出力にフォールバックする堅牢化を行った。

### 既知の制限（ドキュメント的注意）
- apply_sector_cap の価格欠損（price が 0 や欠損）の扱いに TODO が残る：現状は 0.0 を使用しており、エクスポージャーが過小見積りされる可能性があるため将来的に前日終値等のフォールバック実装を検討。
- research/factor_research.py の実装は途中で切れている（モジュールの一部関数は未完）。今後実装継続予定。
- run_monitoring は設計上「監視は environment にかかわらず production sqlite_path を使用」する仕様になっているため、開発環境での誤った DB 参照に注意（意図的な動作として明記）。

### セキュリティ
- .env ファイル生成ウィザードはシークレット項目をマスク表示するが、.env ファイルは平文で保存されるため Git 等へのコミットを禁止する注意書きを付記。

---

今後の予定（例）
- research モジュールの完成、ファクター計算パイプラインの追加
- BrokerClientFactory の実装詳細（Mock と 実ブローカーのテストカバレッジ）強化
- 単元サイズを銘柄別に扱うための stocks マスタ導入と position_sizing の拡張

（本 CHANGELOG はソースコードから推測して作成しています。実際のリリース履歴や日付はプロジェクト運用に合わせて調整してください。）
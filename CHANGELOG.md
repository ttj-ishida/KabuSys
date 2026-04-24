# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。重要な変更・追加点を日本語でまとめています。

フォーマット: 加筆・修正があれば上から順に新しいものを追加してください。

## [0.1.0] - 2026-04-24

初回公開リリース。

### 追加 (Added)
- 実行/監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止処理を実装。エンジンは別スレッドで実行され、停止フラグ (data/stop_requested.flag) を監視して安全停止する。
    - 実行時に PID ファイル (data/execution.pid) を管理。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視データを記録。
    - 停止フラグ (data/stop_requested.flag) を検出してループを終了。
    - プロセス開始時にプロセス優先度を "high" に設定。

- 設定管理・支援ツールを追加
  - config.py: Settings クラスを追加。環境変数から各種設定を取得するユーティリティを提供。
    - .env 自動読み込み機能（プロジェクトルートを自動検出して .env → .env.local の順で読み込み、OS 環境変数を上書きしない仕組み）。
    - .env 行パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いに対応。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等のプロパティを提供。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 各設定項目の説明、既存 .env の読み込み、シークレットのマスク表示、保存確認、.env 書き出し機能を提供。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML によるパース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でのファイル出力をルートロガーに設定。ログディレクトリの作成に失敗した場合はコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py: プラットフォームに依存しないプロセス優先度設定と CPU affinity 設定を追加。
    - Windows / POSIX (Linux/Mac/FreeBSD) に対する nice/priority の抽象化、権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリを追加 (kabusys.portfolio)
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 選出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア比率配分。スコアが全て 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの最大比率チェック（既存保有を考慮）、売却予定銘柄を除外するオプション。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数（デフォルトフォールバックあり）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく株数決定。単元株丸め、per-position/aggregate cap、コストバッファ、スケーリングロジックを実装。

- 解析 / レポートツールを追加
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能。
    - システム稼働率（system_status）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（P95 等）を集計し、PASS/FAIL 判定基準（閾値）に基づく判定を出力。
    - P95 計算、日付フィルタ、欠損テーブルへの耐性（OperationalError をキャッチして N/A 扱い）を実装。

- 研究用モジュールの追加（骨格）
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を設計方針として想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針。モメンタム計算関数（calc_momentum）の骨格を追加。

- パッケージ初期化
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。
  - package の __all__ を定義（data, strategy, execution, monitoring）。

### 変更 (Changed)
- 環境変数の自動読み込みの優先度を明確化
  - OS 環境変数 > .env.local > .env の順で解決。既存 OS 環境変数を protected として .env/.env.local の上書きを防止。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストや特殊な環境向け）。

- ログ出力設計
  - StreamHandler は stderr ではなく stdout を使用（外部ジョブスケジューラからのリダイレクト運用を想定）。

### 修正 (Fixed)
- 環境変数パーサーの堅牢化
  - export プレフィックス、クォート文字内のバックスラッシュエスケープ、行内コメントの扱い（クォート有無での差分）に対応することで .env の誤読を低減。

- Execution / Monitoring の DB 初期化
  - 起動時に監視用テーブルを冪等に初期化（init_monitoring_db）して、テーブルが存在しない環境でも安全に起動できるようにした。

### ドキュメント (Documentation)
- 各 CLI スクリプトに使い方コメントを追加（ファイル先頭に簡易の使用方法と環境変数の説明）。

### その他
- 例外処理とフォールバックが多めに実装されており、権限不足・未インストール依存（例: PyYAML）・ファイルシステムの制約などの状況でもできる限り安全に動作するよう設計されています。

---

今後の予定（例）
- research/factor_research の完全実装（Value, Volatility, Liquidity の計算）。
- 単体テスト・CI の整備、ドキュメントの拡充。
- 銘柄毎の lot_size マスタ導入、position_sizing の拡張。
- 監視・実行コンポーネントのさらに詳細なメトリクス収集とアラート連携（LINE 経由など）。

もし CHANGELOG に追加したい差分や、より詳細なリリースノート（ファイル単位の変更一覧、著者情報など）が必要であれば教えてください。
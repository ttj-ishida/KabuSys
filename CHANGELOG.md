# Changelog

すべての変更は Keep a Changelog の形式に従って記載します。  
初期リリース相当の内容をコードベースから推測してまとめています。

## [0.1.0] - 2026-04-23

### Added
- 初版リリース: KabuSys — 日本株自動売買システムの初期実装。
- 実行/監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は専用 MockBroker と paper_trading.db を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を設定し、停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）を扱う。
    - Engine を別スレッドで実行し、停止フラグ検知で安全に停止する仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する挙動を明示。
    - 停止フラグ検知・例外処理・接続クローズ処理を実装。

- 設定管理
  - config.py: 環境変数/ .env 自動読み込みと Settings クラスを実装。  
    - プロジェクトルートを .git / pyproject.toml から探索して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パースは export プレフィックス、クォート、エスケープ、インラインコメントに対応。
    - 各種プロパティ（DUCKDB_PATH / SQLITE_PATH / PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等）にバリデーションとデフォルトを実装。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。  
    - シークレット入力のマスク、既存値再利用、保存前確認をサポート。
    - .env ファイル生成時に注意書き（Git にコミットしない等）を出力。

- 設定検証ツール
  - validate_config.py: 起動前チェック用 CLI を追加。  
    - 必須環境変数、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在、config/*.yaml の存在・パース（PyYAML が利用可能な場合）などの検証。
    - --strict を指定すると警告も失敗扱いで exit(1)。

- ロギング・ユーティリティ
  - utils/logging_setup.py: 全アプリケーションで共通利用するログ設定ユーティリティを追加。  
    - stdout 出力用 StreamHandler と 日次ローテーション (TimedRotatingFileHandler) を root ロガーに設定。
    - ログディレクトリ自動作成、既存ハンドラのクリア、LOG_LEVEL / LOG_DIR の解決順を実装。

- プロセス管理ユーティリティ
  - utils/process_priority.py: Windows / POSIX を吸収したプロセス優先度と CPU affinity 設定ユーティリティを追加。  
    - set_process_priority("high" | "normal" | "low")、set_cpu_affinity(n) を提供。権限不足時は警告してスキップ。

- データベース連携
  - DuckDB / SQLite の接続を想定した初期統合を実装（各スクリプトで接続確立とクローズを実施）。
  - monitoring_db.init_monitoring_db 呼び出しによる監視用テーブルの冪等な初期化をサポート。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定と等重・スコア重み計算を追加（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクターキャップの適用とレジームに応じた乗数計算（apply_sector_cap, calc_regime_multiplier）。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元丸め、aggregate cap によるスケールダウンと再配分アルゴリズムを実装。
  - portfolio パッケージの __all__ を整理して公開 API を定義。

- 実行系コンポーネント（コード参照から推定）
  - execution 側で BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager を組み立てて起動する基本フローを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。  
    - 稼働率、注文成立率、送信率、P95 レイテンシなど指標を集計し PASS/FAIL を判定する閾値を定義。
    - P95 計算、日付フィルタ (--from/--to)、DB パスの解決（コマンド引数 / 環境変数 / デフォルト）をサポート。

- 研究用モジュール（ファクター計算）
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity 等のファクター計算を行うための骨格を追加。DuckDB 経由で prices_daily / raw_financials を参照する設計。

### Changed
- 各起動スクリプトで起動直後にプロセス優先度を "high" に設定するよう標準化。
- logging_setup によりアプリ全体でログ挙動を統一（stdout + 日次ファイルローテーション、既存ハンドラの二重登録防止）。

### Fixed
- .env 読み込みの堅牢化:
  - export プレフィックス対応、クォート付き値のバックスラッシュエスケープ処理、インラインコメントの扱い、未設定時のフォールバックなどに対応。
  - .env.local による上書き（override）と OS 環境変数の保護（protected set）を実装し、予期せぬ上書きを防止。
- run_monitoring/run_execution のリソースクリーンアップを追加（DB 接続の確実な close）。
- position_sizing の aggregate cap 実装で、スケールダウン後に残余キャッシュを使って lot 単位で再配分するロジックを導入（端数処理の再現性確保）。

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- config_setup に .env を絶対に Git にコミットしない旨の注意を明記。
- 必須機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）は Settings で未設定時に明示的にエラーを出す仕様にして、誤った公開リスクを低減。

### Notes / Known limitations
- run_monitoring は「監視用 DB として常に sqlite_path（本番パス）を使用する」設計になっているため、paper_trading 環境で監視 DB を分離したい場合は運用上の注意が必要。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で失敗する場合があり、その場合は警告でスキップする実装です。
- research/factor_research.py はファクター計算ロジックの骨格を含むが、実データ条件下での追加テスト・チューニングが必要。

---

この CHANGELOG はコードベースからの推測に基づいて作成しています。実リリースや運用履歴に合わせて日付・項目の整理を行ってください。
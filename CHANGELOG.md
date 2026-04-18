# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
このプロジェクトでは Semantic Versioning (SemVer) を採用します。

※ 以下はコードベースの内容から推測して作成した初期リリースの変更履歴です。

## [Unreleased]

- （今後の変更をここに記載）

---

## [0.1.0] - 2026-04-18

初期リリース。日本株自動売買システム「KabuSys」のコア機能・CLI・ユーティリティ群を実装。

### Added
- 全体
  - パッケージの初期バージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - DuckDB / SQLite を利用するデータストレージ基盤を導入（duckdb, sqlite3 統合）。
- 起動スクリプト / デーモン
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時は専用の paper trading SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと実行制御（デーモンスレッド起動／停止フラグ検知）。
    - 起動時にプロセス優先度を設定。
    - PID / 停止フラグ管理（data/execution.pid、data/stop_requested.flag）をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグの検知、例外発生時のロギングとリトライ、リソースクリーンアップを実装。
- 設定管理 / CLI
  - config.py: 環境変数・設定管理クラス（Settings）を実装。
    - .env 自動読み込み機能（.env、.env.local）。OS 環境変数は保護され上書きされない。
    - .env のパースはクォートやエスケープ、インラインコメントに対応。
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PID パス、閾値など）と入力値検証を提供。
    - KABUSYS_ENV / LOG_LEVEL 等の検証ロジック。
  - config_setup.py: .env 作成支援の対話式ウィザードを追加。
    - 初期値、選択肢、シークレットマスク表示、保存確認を実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV 値チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証を実行。
    - --strict オプションで警告をエラーとして扱う機能を提供。
- ポートフォリオ構築ロジック（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア順ソート・上位選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全0 の場合は警告して等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を検査し超過するセクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数の算出（未知レジームは警告してフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に基づく株数算出、単元株丸め、max_position_pct・max_utilization といった制約、aggregate cap によるスケールダウンロジックを実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮した安全側見積り。
- 監視・検証ツール
  - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの初期化を保証（冪等に実行）。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを算出して判定（PASS/FAIL）を出力。
    - デフォルト DB パスは data/paper_trading.db。--from / --to / --db オプションをサポート。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを実装。
    - stdout への StreamHandler（stdout を使用）、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日分保持）を設定。
    - ログレベル・ログディレクトリの解決順とエラー耐性を実装（ファイル作成失敗時はコンソールのみで継続）。
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティを実装。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収。優先度("high"/"normal"/"low") の設定。
    - set_cpu_affinity によるコア固定機能（オプション）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- 研究用モジュール（途中実装）
  - research/factor_research.py: DuckDB 上の価格・財務データを用いたモメンタム等ファクター計算モジュールを追加（設計方針・定義、calc_momentum の実装開始）。

### Changed
- （初回リリースのため過去からの変更はなし）

### Fixed
- run_monitoring.py / run_execution.py
  - DB 接続クローズを finally ブロックで確実に行うようにしてリソースリークを防止。
  - monitor のループで例外発生時に次回ポーリングまで待機し続ける堅牢化を実装。

### Security
- .env の自動読み込みで OS の環境変数が上書きされないよう保護（protected set）。
- .env を生成する config_setup.py に Git へのコミット禁止コメントを明示。

### Notes / Design decisions
- run_monitoring では監視が本番 sqlite_path を常に参照する設計（監視データを環境ごとに混在させない意図）。
- Paper Trading は run_execution にて settings.is_paper 判定で専用 SQLite を使用することで本番 DB と完全に分離。
- .env パーサはクォート内のバックスラッシュエスケープ・インラインコメントの扱い等、POSIX シェル風の仕様に近づけている。
- position_sizing の rounding は現状全銘柄共通の lot_size（デフォルト 100）に依存。将来的に銘柄ごとの単元対応を想定（TODO コメントあり）。
- calc_regime_multiplier は未知のレジームに対しては警告出力して 1.0 をフォールバックとする安全設計。

---

過去リリース・将来の変更についてはこの CHANGELOG.md を更新してください。
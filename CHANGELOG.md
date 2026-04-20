# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-20

### Added
- 実行スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。プロセス起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ストップ制御はプロジェクトの data/stop_requested.flag で行い、実行中スレッド監視 -> 停止のフローを実装。
    - PID ファイルの出力を行う（data/execution.pid をデフォルト）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。デフォルトポーリング間隔は 60 秒で、環境変数 `MONITOR_POLL_INTERVAL` により上書き可能（不正値は警告してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - stop flag 検知で優雅にループを終了する。

- 設定管理・ウィザード・検証
  - config.py
    - .env 自動読み込み実装（プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む）。
    - .env の行パーサを実装（`export ` プレフィックス、クォート／エスケープ、インラインコメントの扱いなどに対応）。
    - 環境変数のキーごとにプロパティ化した Settings クラスを実装（J-Quants / kabu API / DB パス / Paper Trading / 監視閾値 等）。値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を行う。
    - settings インスタンスをモジュールレベルでエクスポート。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。既存値の再利用、シークレット入力マスク、説明表示、最終確認後にファイル保存を行う。
  - validate_config.py
    - 起動前チェック用 CLI を実装。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、`live` 環境向けの追加ガード（LINE 設定や Kill Switch の設定）を提供。
    - `--strict` オプションで警告も失敗扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的ログ設定ユーティリティを提供。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベルとログディレクトリは引数または環境変数（LOG_LEVEL, LOG_DIR）で解決可能。
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows と POSIX の差分吸収）。
    - set_process_priority(level) で "high/normal/low" を設定。アクセス権不足等は警告してスキップ。
    - set_cpu_affinity(cpu_count) を追加し、プロセスの CPU affinity を最初の N コアに固定できる（未指定または不正値は無効化）。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - 銘柄候補の選定（select_candidates）および等金額（calc_equal_weights）・スコア加重（calc_score_weights）配分を実装。全スコア 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定の銘柄をエクスポージャー計算から除外可能）。unknown セクターは除外対象にしない設計。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出 calc_position_sizes を実装。allocation_method に応じて "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、全体の aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮した保守的な計算、残差の順序付けによる追加配分ロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite（デフォルト: data/paper_trading.db）からデータを集計して検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）などを算出し、定義された閾値（稼働率 99%、成功率 90% 等）に基づき PASS/FAIL 判定を行う。
    - P95 の計算や期間フィルタ（--from / --to）に対応。

- データ分析（研究）モジュールの開始実装
  - research/factor_research.py
    - Momentum 等のファクター計算を行う設計を追加（DuckDB を受け取り prices_daily 等のテーブルで計算する方針）。モジュールの骨子・定数が実装されている（calc_momentum の実装途中）。

- パッケージ初期化
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- （初回リリースのため無し。設計上の注意点をドキュメント化）
  - .env 自動ロードはデフォルトで有効。テスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで自動ロードを無効化できる。
  - .env の読み込み順は OS 環境変数 > .env.local > .env（.env.local は既存 OS 環境変数を protected として上書きされないよう配慮）。

### Fixed
- （初回リリースのため無し）

### Security
- 環境変数に含まれるシークレット（J-Quants トークンや kabu API パスワード）は対話ウィザードで入力時にマスク表示される。なお .env ファイルは決して Git にコミットしないよう README 等で注意喚起する構成にしている（config_setup.py に警告ヘッダを出力）。

---

備考:
- 実装は運用上の安全性（stop flag、pid ファイル、死活監視テーブル初期化など）や運用性（ログの統一・ローテーション、プロセス優先度設定、Paper Trading の DB 分離）を重視して設計されています。
- 今後の予定:
  - research/factor_research の残り実装（calc_momentum の SQL/集計ロジック完了など）
  - Engine / Execution の各コンポーネント（broker_factory, execution_engine, order_manager 等）の詳細実装とテストカバレッジ強化
  - 単体テスト・統合テストおよびドキュメントの整備

もし特定のファイルや変更点についてより詳細な説明（設計上の意図、利用手順、環境変数一覧など）をご希望であればお知らせください。
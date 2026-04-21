# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 初期リリース: KabuSys のコアユーティリティ・起動スクリプト・ポートフォリオ構築・検証ツール群を追加。
- 起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db, 環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、MockBrokerClient を利用する設計をサポート。
    - エンジンは別スレッドで run_session を実行。data/execution.pid に PID を書き、 data/stop_requested.flag による停止検出を行う。
    - 起動時にプロセス優先度を "high" に設定。
    - RiskManager 用のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を組み込み。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）処理は環境にかかわらず本番用 sqlite_path を使用する実装。
    - 停止フラグ（data/stop_requested.flag）を監視して安全にループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - src/kabusys/config.py
    - Settings クラスを導入し、環境変数経由で各種設定値を取得する API を提供（例: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, 各種閾値, env 判定プロパティなど）。
    - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。読み込み順序は OS 環境 > .env.local > .env。自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
    - PAPER_FILL_MODE の検証を実装（有効値: instant/partial/never/reject）。
    - Settings インスタンスをモジュールレベルで提供（settings）。

- 設定ユーティリティ
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。デフォルト値・選択肢・シークレット扱いをサポート。
    - 生成する .env のテンプレートと注記（絶対に Git にコミットしないこと）を用意。
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の整合性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML が利用可能な場合のみ）などを実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに対して StreamHandler（標準出力）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。
    - ログディレクトリの解決順: 引数 > LOG_DIR 環境変数 > デフォルト logs/。ディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソール出力のみでフォールバック。
    - ログレベルは引数 > LOG_LEVEL 環境変数 > デフォルト INFO で決定。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の priority class、POSIX の nice 値）と CPU affinity 設定関数を追加。
    - 未対応 OS や権限不足時は警告を出してスキップする安全実装。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分を実装（スコア合計が 0 の場合は等分配にフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクターエクスポージャーが上限を超える場合に新規候補を除外するロジック。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームは警告を出してフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じて買付株数を算出（risk_based / equal / score をサポート）。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超える場合のスケーリング）を実装。
    - cost_buffer（スリッページ・手数料の保守的見積）を考慮したスケーリングロジックや残差処理を実装。

- 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。SQLite データベースからシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）などを集計して表示。
    - デフォルト閾値を定義（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200ms）し、Pass/Fail を判定。
    - --from / --to / --db CLI オプションをサポート。

- リサーチ基盤（骨組み）
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールの骨格を追加。DuckDB を使って prices_daily / raw_financials を参照し、Momentum / Value / Volatility / Liquidity 等の計算設計を記載。
    - モメンタム計算関数（calc_momentum）の実装開始（ファイル末端は途中まで実装）。

- パッケージ初期化
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

補足:
- .env の自動読み込みはプロジェクトルート探索（.git / pyproject.toml）に依存するため、パッケージ配布後も CWD に依存せず動作するよう配慮されています。自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD が用意されています。
- .env のパーサはクォート（シングル/ダブル）、export キーワード、インラインコメントの挙動、バックスラッシュエスケープに対応しています。
- ログ・プロセス優先度処理は権限不足や OS 非対応時に安全にフォールバックするよう設計されています。
- Paper Trading と本番 DB を明確に分離しており、paper_trading 時は専用 DB を用いることで本番データと混在しないことを意図しています。

もし項目をより細かく分けたい（ファイル別の変更履歴や将来の Unreleased セクション追加など）、または日付やバージョン表記を変更したい場合はお知らせください。
# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従い、重要なリリースについて日本語で記載しています。

## [0.1.0] - 2026-04-21

初回リリース。KabuSys のコアユーティリティ、実行・監視ランナー、設定管理、ポートフォリオ構築ロジック、検証ツール群を含みます。

### 追加
- 起動スクリプト・デーモン
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient を利用する設定想定）。
    - 実行中の停止は data/stop_requested.flag により制御。PID ファイルを書き込む（data/execution.pid）。
    - 起動時にプロセス優先度を "high" に設定するユーティリティを呼び出す。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値は警告のうえデフォルトを使用。
    - 監視用 DB は環境に依らず本番 sqlite_path を使用する設計。
    - 停止はプロジェクト直下の data/stop_requested.flag によって行う。

- 設定・環境管理
  - config.py
    - Settings クラスによる環境変数ラッパーを追加（J-Quants / kabu API / DB / 監視閾値 等）。
    - .env ファイルの自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml で検出）。
    - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START などの設定を追加。
    - env / log level の検査（有効値チェック）を実装。
  - config_setup.py
    - 対話式の .env 作成ウィザードを追加（J-Quants トークン、kabu パスワード、DB パス、ログレベルなどを対話で設定・保存）。
    - 既存 .env の読み込み・マスク表示、保存前の確認機能を提供。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の妥当性を検証する CLI を追加。
    - --strict オプションで警告も失敗（exit(1)）扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML のパース検証（PyYAML があれば）などを実行。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガー設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と、日次ローテーション (TimedRotatingFileHandler) を組み合わせて設定。ファイル出力はログディレクトリ作成に失敗した場合はスキップしてコンソールのみで継続。
    - LOG_DIR / LOG_LEVEL 環境変数や関数引数で上書き可能。
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定ユーティリティを追加（high/normal/low）。
    - CPU affinity 設定関数 set_cpu_affinity を追加（任意のコア数に固定可能）。失敗時は警告を出してスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights、スコア全て 0 の場合は等配分にフォールバック) を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier: bull/neutral/bear) を実装。
  - portfolio/position_sizing.py
    - 発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）で丸め、1 銘柄上限(max_position_pct)、総投下上限(max_utilization)、コストバッファ (cost_buffer) を考慮した aggregate cap スケーリングと残差分配を実装。

- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計してレポートを生成する CLI を追加。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を用いた PASS/FAIL 判定を実装。
    - 日付フィルタ(--from / --to) と DB パス指定オプション(--db) をサポート。

- リサーチ（未完のファクター計算実装）
  - research/factor_research.py
    - ファクター計算モジュールのスケルトンを追加（モメンタム、MA200乖離、ATR、流動性等を想定）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計。モメンタム計算関数 calc_momentum の導入を開始（実装途中の箇所あり）。

### 変更
- パッケージメタデータ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### 注意・既知の設計意図（ドキュメント）
- 環境変数自動読み込み
  - .env の自動読み込みはプロジェクトルートが検出できた場合にのみ行われ、OS 環境変数は上書きされないよう保護されています。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading の分離
  - paper_trading モード時は paper_trading 専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使い、本番監視 DB(SQLITE_PATH) とは分離します。
- ログ出力
  - 標準出力は stdout を使用（cron 等で stdout/stderr をまとめて扱う環境を想定）。
  - ログディレクトリ作成失敗時はファイルローテーションを無効化してコンソール出力のみ継続します（堅牢性を重視）。
- セーフガード
  - process_priority/set_cpu_affinity や logging のファイルハンドラ生成など、権限不足や未対応環境で例外が発生した場合は警告ログを出して安全にスキップする設計。

### 追加された環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルトを持つ)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の fill モード: instant|partial|never|reject)
- KABUSYS_ENV (development|paper_trading|live)
- LOG_LEVEL (ログレベル)
- LOG_DIR (ログファイル出力先)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔)
- KILL_FLAG_CLEAR_ON_START (本番での Kill Flag 自動クリアフラグ; デフォルト 0)

### 既知の制限・ TODO
- research/factor_research.py の一部関数は実装途中（calc_momentum の続き等）。ファクター計算ロジックの完成が必要。
- position_sizing の price フォールバック（価格欠損時の補完ロジック）は未実装（TODO コメントあり）。
- 単元株サイズを銘柄別に扱う拡張（stocks マスタ参照）は将来的な改善予定。
- Windows/Linux の優先度設定は OS の制約・権限に依存し、失敗する場合がある（警告でスキップ）。

### 互換性
- 初回リリースのため後方互換性の破壊はありません。今後の変更で環境変数名や DB スキーマを変更する場合は注意してください。

---

この CHANGELOG はコードベースの内容から推測して作成しました。必要に応じて日時、著者、より詳細な変更点（コミット一覧や DB スキーマ変更など）を追記してください。
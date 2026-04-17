# Changelog

すべての顕著な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

※ 本ファイルはコードから推測して作成しています。実際のリリースノートは運用状況に合わせて調整してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

Added
- 基本アプリケーション骨格を追加（初期リリース）。
  - パッケージメタ情報: src/kabusys/__init__.py （__version__ = "0.1.0"）。
- 実行系エントリポイントを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` のときは MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）へ記録して本番 DB と分離。
    - 起動時にプロセス優先度を高 ("high") に設定。
    - 停止制御: data/stop_requested.flag を検知して安全に停止。PID ファイル（data/execution.pid）使用。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立てを実装。
    - RiskManager のデフォルト設定値（最大ポジション比率、利用率、レートリミット、サーキットブレーカー等）を定義。
- 監視系エントリポイントを追加。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックしてログ出力。
    - 監視は環境にかかわらず本番の sqlite_path を使用する（監視 DB 初期化処理を呼出し）。
    - DuckDB 連携（duckdb_path）をサポート。
    - 停止フラグ検知・例外ハンドリング・リソースクローズ処理を実装。
- 設定管理とウィザードを追加。
  - src/kabusys/config.py
    - .env の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パースは export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DuckDB / SQLite / Paper Trading / 監視閾値 / システムフラグ等）。
    -.env の必須チェックを行う _require() を提供。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）と入力プロンプト、シークレット表示マスク、保存処理を実装。
    - .env の書き込みテンプレートでは「.env を絶対に Git にコミットしないこと」を明記。
- 設定検証ツールを追加。
  - src/kabusys/validate_config.py
    - .env と config/*.yaml を事前検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証（PyYAML がない場合はスキップ）、本番環境向けガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ロジック（純粋関数群）を追加。
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates：スコア降順、同点は signal_rank）、
    - 等金額配分（calc_equal_weights）、
    - スコア加重配分（calc_score_weights：全てのスコアが 0 の場合は等配分にフォールバックと警告）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap：既存保有セクター比率が上限を超える場合に新規候補を除外、"unknown" セクターは除外対象外）、
    - レジームに応じた乗数計算（calc_regime_multiplier：bull/neutral/bear のマップ。未知レジームは警告して 1.0 にフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - ポジションサイズ計算（risk_based / equal / score の各方式）。
    - 単元（lot_size）丸め、per-stock 上限・aggregate cap のスケーリング、cost_buffer（手数料・スリッページの保守的見積り）を実装。
    - データ欠損（価格なし等）時のスキップとログ出力を考慮。
  - エクスポートモジュール: src/kabusys/portfolio/__init__.py
- 研究・ファクター計算モジュールを追加（DuckDB ベース）。
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M, MA200 乖離）とボラティリティ（ATR、平均売買代金、出来高比率）計算の実装。
    - DuckDB 上で SQL を実行して prices_daily テーブルを参照する設計。データ不足時の None 戻りを取り扱う。
    - 計算窓や日数定数を定義（例: MA200、ATR 20 日等）。
- ユーティリティを追加。
  - src/kabusys/utils/process_priority.py
    - マルチプラットフォームでのプロセス優先度設定ユーティリティ（Windows / POSIX の差分吸収）。
    - CPU affinity を最初 N コアへ固定する set_cpu_affinity を提供（psutil に依存、権限不足や未対応環境では警告してスキップ）。
- Paper Trading 向け検証ツールを追加。
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の SQLite ログから検証レポートを生成する CLI。
    - 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、レイテンシ（avg/max/P95）を算出。
    - パス/フェイル基準値（稼働率 99%、Fill 90%、Send 95%、P95 レイテンシ 200 ms）を設定し、FAIL 理由を出力。
    - 空データやテーブルがない場合のフォールバックを実装。
- パッケージ構造とモジュール初期化を追加。
  - src/kabusys/tools/__init__.py、src/kabusys/utils/__init__.py

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- .env に関する注意喚起: config_setup にて .env を Git にコミットしない旨を明記。
- 環境変数の必須値未設定時に明示的な例外を投げる仕組みを実装（Settings._require）して、秘密情報の見落としを防止。

Notes / Implementation details
- .env 自動ロードはプロジェクトルートを検出して行う（.git または pyproject.toml が基準）。プロジェクトルートが特定できない場合は自動ロードをスキップ。
- .env パーサは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、およびインラインコメント処理に対応する堅牢な実装。
- run_monitoring は監視 DB 初期化（init_monitoring_db）を行い、例外発生時でもループ継続とログ出力で堅牢性を高める設計。
- run_execution は paper_trading の DB を本番 DB と完全分離することで誤操作リスクを低減。
- process priority / cpu affinity の設定は権限不足や未対応 OS でスキップし、警告ログによりユーザーへ通知する設計。
- 多くの関数は副作用を持たない純粋関数として設計されており、ユニットテストが容易な構造になっている（portfolio.*, research.* 等）。

要望や誤りの報告、追加の詳細を反映したい場合はお知らせください。必要に応じて日付・カテゴリの調整や未リリース変更の追加を行います。
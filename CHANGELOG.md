# Changelog

すべての変更は Keep a Changelog の形式に従い、日本語で記載します。

v0.1.0 - 2026-04-18
-------------------

初回リリース — KabuSys の基本機能をまとめて追加しました。

### 追加 (Added)
- 実行エントリ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境変数 KABUSYS_ENV に応じて paper_trading 用の MockBrokerClient / 専用 SQLite DB を使用可能（PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を参照する仕様にしています。
- 設定管理
  - config.py: 環境変数/ .env 自動読み込み・ラッパーを実装。自動ロードはプロジェクトルート（.git または pyproject.toml）を検出して行い、.env と .env.local の読み込み順（.env → .env.local（上書き））を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - Settings クラスを提供し、各種設定（J-Quants トークン、kabu API、DB パス、監視閾値、環境判定メソッド等）をプロパティとして取得可能にしました。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式の .env 作成ウィザードを追加（python -m kabusys.config_setup）。デフォルト値、選択肢、シークレット入力対応。生成時の注意書き（.env をコミットしない等）を出力。
  - validate_config.py: 起動前の設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在/パース確認（PyYAML があれば内容検証）などをチェック。--strict オプションで警告を FAIL 扱いにできます。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等配分・スコア配分 (calc_equal_weights / calc_score_weights) を追加。
  - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジームに基づく投下資金乗数 (calc_regime_multiplier) を追加。
  - portfolio.position_sizing: 発注株数計算ロジック (calc_position_sizes) を追加。risk_based / equal / score の割付方法、単元株（lot_size）丸め、aggregate cap スケーリング、コストバッファ考慮を実装。
  - package export: kabusys.portfolio モジュールとして主要関数を公開。
- 監視 / 実行用ユーティリティ
  - utils/logging_setup.py: 統一的ロギング初期化関数 setup_logging を追加。stdout への StreamHandler（stdout 使用）と日次ローテーションファイルハンドラ（TimedRotatingFileHandler, 30 日保持）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度設定（Windows/Linux/Mac の差分を吸収）と CPU affinity 設定関数を追加。起動スクリプトで高優先度 ("high") に設定する呼び出しを行います。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ等を集計してレポートを出力する CLI を追加。閾値に基づく PASS/FAIL 判定を行います。
- 研究用（リサーチ）モジュール
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（Momentum/Value/Volatility/Liquidity を想定）。DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみ参照して純計算を行う設計。
- モジュール追加・初期化
  - monitoring.monitoring_db の初期化呼び出しを run_* から行うことで監視テーブルの存在を保証（冪等）。
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

### 変更 (Changed)
- .env のパース挙動を強化
  - config._parse_env_line で export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い等を実装。より実務的な .env フォーマットに対応しています。
- ログ出力の統一
  - setup_logging によりアプリケーション全体で同一のログフォーマット／ローテーションポリシーを採用。ストリームは stdout を使用（cron 等でリダイレクトしやすくするため）。
- DB パス取り扱い
  - run_execution は paper_trading 環境時に専用 SQLite（paper_sqlite_path）を使用するように変更し、ペーパートレードと本番 DB を明確に分離。
- 実行時の安全措置
  - run_execution / run_monitoring の両方で data/stop_requested.flag（停止フラグ）をチェックし、安全に停止できる仕組みを導入。実行エンジンは PID ファイルを生成するオプション（pid_file）を受け取ります。
- 監視ループの堅牢化
  - monitor.check_once() 実行時に例外が発生してもログに残して次のポーリングへ継続するように変更（fail-safe なポーリングループ）。

### 修正 (Fixed)
- init_monitoring_db 呼び出しは冪等性を前提に実行し、監視テーブルが存在しない場合に確実に作成されるようにしました。
- logging_setup: ログディレクトリ作成に失敗した際の挙動を改善し、ファイルハンドラ作成に失敗してもコンソール出力は維持されるようにしました。

### 非互換性 / 注意点 (Breaking Changes / Notes)
- 監視(run_monitoring) は KABUSYS_ENV にかかわらず "本番" 用 sqlite_path を使用します（設計上の意図）。ペーパートレードで監視データを分離したい場合は別途設定が必要です。
- .env ファイルは自動読み込みされますが、テスト等で自動ロードを阻止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE に無効な値を設定すると Settings.paper_fill_mode で ValueError が発生します。許容値は "instant" | "partial" | "never" | "reject" です。
- KABUSYS_ENV の許容値は "development" | "paper_trading" | "live" のいずれかです。誤った値は例外を発生させます（起動前に validate_config で検出推奨）。

### 開発・運用向け情報 (Internal / Ops)
- ログ：
  - デフォルトログディレクトリ: logs/
  - ファイル名: <app_name>.log（app_name は setup_logging の引数。例: "execution"）
  - ローテーション: 日次、30 日保持
- プロセス優先度:
  - 起動時に set_process_priority("high") を呼び出します。権限不足等で設定できない場合は警告を出力してスキップします。
- CLI:
  - 環境ウィザード: python -m kabusys.config_setup
  - 設定検証:    python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- DB:
  - DuckDB（分析用）と SQLite（監視 / 履歴用）を使い分ける設計。
  - デフォルト: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- 注意:
  - .env は決して Git にコミットしないこと（config_setup のヘッダにも明記）。

### 今後の予定 (Unreleased / TODO)
- research/factor_research の完全実装（Value, Volatility, Liquidity ファクター等の詳細ロジック）。
- 銘柄別単元情報 (lot_size) の外部マスタ化と position_sizing の拡張対応。
- モニタリング・アラート（LINE 通知等）の実装強化（本番環境向けガードも追加予定）。
- DuckDB を用いたバッチ分析 / バックテスト用ツールの追加。

---
このリリースに関する質問や追加で記載してほしい項目があればお知らせください。
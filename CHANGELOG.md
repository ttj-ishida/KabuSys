# Changelog

すべての重要な変更をここに記録します。  
このファイルは「Keep a Changelog」の形式に準拠します。  

参考:
- https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-23

初回リリース。本リポジトリは日本株自動売買システム「KabuSys」のコアユーティリティ、実行エントリ、設定管理、ポートフォリオ構築ロジック、監視／検証ツール、および補助ユーティリティ群を提供します。主な追加点は以下の通りです。

### Added
- 基本パッケージ初期化
  - パッケージバージョンを設定: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行・監視スクリプト
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - KABUSYS_ENV=paper_trading 時に本番 DB と分離されたペーパートレード用 DB（data/paper_trading.db をデフォルト）および MockBrokerClient を使用する仕組みをサポート。
    - 実行エンジンを別スレッドで起動し stop flag（data/stop_requested.flag）で安全に停止可能。
    - execution.pid の出力先をサポート。
    - RiskManager のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を初期化し、initial_portfolio_value に broker.get_available_cash() を使用。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor インスタンスを生成してポーリングループを実行。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は環境にかかわらず production 用 sqlite_path を使用する（監視データは本番 DB を想定）。
    - stop flag 検知でループを終了。

- 設定管理 / ヘルパー
  - Settings クラス: src/kabusys/config.py
    - 環境変数や .env ファイルから設定を取得するラッパ。
    - .env の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）を実装。OS 環境変数は上書きされないよう保護。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject を受け入れる）。
    - データベース・ファイルパス、PID/kill flag パス、しきい値等の取得プロパティを追加。
    - env/log_level の検証ロジック（許容値チェック）。
  - 環境設定ウィザード CLI: src/kabusys/config_setup.py
    - 対話式で .env を初期作成・更新するウィザードを実装。
    - 秘匿入力、選択肢、デフォルト表示、既存 .env の読み込み・再利用、最終確認と保存機能を提供。
  - 設定検証 CLI: src/kabusys/validate_config.py
    - .env と config/*.yaml の存在・基本整合性チェックを行うツール。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、PyYAML の有無に応じた YAML パースチェック、本番環境用ガード（LINE 通知や Kill Switch の注記）などを実装。
    - --strict フラグで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 銘柄選定 / 重み計算: src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア正規化配分（全スコアが 0 の場合は等金額にフォールバック）。
  - セクター・レジーム調整: src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有に基づくセクター集中上限（max_sector_pct）適用。unknown セクターは除外しない設計。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバック）。
  - 株数決定・発注量算出: src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた株数計算（"risk_based", "equal", "score" をサポート）。
    - risk_based の場合はリスク %、stop_loss_pct などから算出。
    - lot_size（現在デフォルト 100）で丸め、max_position_pct / max_utilization による per/aggregate 上限を尊重。
    - cost_buffer を考慮した保守的見積りと、投資合計が available_cash を超えた場合のスケールダウン（端数の公平配分ロジック）を実装。

- 監視・レポートツール
  - Paper Trading 検証レポート: src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH で指定可）から統計を集計してレポート出力（期間指定 --from / --to, --db オプション対応）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）。
    - PASS/FAIL 基準（デフォルト）を定義: 稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms。
    - SQL の存在/カラム不整合に備えた例外ハンドリング（OperationalError をキャッチして N/A を扱う）。

- ユーティリティ
  - ロギング設定ユーティリティ: src/kabusys/utils/logging_setup.py
    - 全起動スクリプトから統一して呼べる setup_logging を提供。
    - stdout（StreamHandler）を使用し、TimedRotatingFileHandler（日次ローテーション、30 日保持）でファイル出力を行う。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル・ログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
  - プロセス優先度 / CPU affinity ユーティリティ: src/kabusys/utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX を吸収して nice 値や HIGH_PRIORITY_CLASS を設定。アクセス権限等で失敗した場合は警告してスキップ。
    - set_cpu_affinity(cpu_count) により最初の N コアにプロセスを固定（未対応 OS や権限不足は警告してスキップ）。
  - その他ユーティリティ: src/kabusys/utils/__init__.py を整備。

- リサーチ / ファクター計算（着手）
  - src/kabusys/research/factor_research.py を追加。
    - StrategyModel に基づくファクター（Momentum, Value, Volatility, Liquidity）計算の設計を導入。
    - calc_momentum のインターフェイス／定数類を追加（DuckDB 経由で prices_daily を参照）。実装の続きあり（ファイル末尾で途切れが見られるため今後追記予定）。

### Changed
- DB 初期化
  - 監視テーブルの初期化関数 init_monitoring_db を起動時に呼び出し、監視テーブルが存在することを保証（冪等）。呼び出しは paper_trading でも行うが、ペーパー取引は専用 sqlite_path を使用して本番と分離する。

- デフォルトパスや挙動の明文化
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等のデフォルトパスをコード上で定義し、config_setup や validate_config で参照可能にした。

### Fixed
- 環境変数パーサの強化
  - src/kabusys/config.py の .env 読み込みロジックで以下をサポート・修正:
    - コメント行 / export 形式のサポート
    - シングルクォート・ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし値におけるインラインコメントの扱い（直前がスペース/タブの場合にコメントと判定）
    - OS 環境変数の保護（.env の自動ロードで既存 OS 環境を上書きしない）

### Security
- .env 取り扱いに関する注意
  - config_setup に .env を絶対に Git にコミットしない旨のヘッダを出力するテンプレートを追加。

### Documentation / UX
- CLI ヘルプ・メッセージを充実化
  - validate_config と config_setup にわかりやすいヘルプと推奨手順（例: python -m kabusys.validate_config）の案内を追加。
  - paper_verification_report における期間指定と DB パス解決の説明を追加。

### Known issues / Notes
- factor_research.calc_momentum の実装は途中で終端が見られ、まだ完全実装ではありません。今後のリリースで続きを実装予定です。
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML 等）に依存します。環境により import エラーや機能制限（例: YAML バリデーションのスキップ）が発生する点に注意してください。
- process_priority の設定は権限不足やプラットフォーム差異により効果が出ない場合があります（警告ログを出力してスキップします）。

---

今後のリリース案（予定）
- factor_research の完全実装（momentum の続き、value/volatility/liquidity の実装）
- ExecutionEngine / Reconciler 等の詳細なユニットテスト追加
- モニタリング／アラート（LINE 通知）実装の拡充
- ペーパートレード検証レポートの出力フォーマット（CSV/JSON）拡張

（以上）
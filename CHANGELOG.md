# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（現状、リリース済みの最初のバージョンのみを含みます。今後の変更はここに追記してください。）

---

## [0.1.0] - 2026-04-20

初回リリース。本リポジトリは日本株自動売買システム「KabuSys」の基盤機能を提供します。主な追加点は以下の通りです。

### Added
- パッケージ基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 実行スクリプト / デーモン系
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書きが可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知による安全停止。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番の sqlite_path を使用する旨の挙動。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、data/paper_trading.db に記録することで本番 DB と完全分離。
    - 停止フラグ（data/stop_requested.flag）検知による停止、実行用 pid ファイル管理（data/execution.pid）。

- 設定・環境変数管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - `.env` と `.env.local` の読み込み順序制御（OS 環境変数の保護機能あり）。
    - 複数の設定プロパティ実装（DB パス、paper_trading 用パス、監視閾値、LOG_LEVEL、KABUSYS_ENV 検証など）。
    - 環境変数パースの堅牢化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱いのルール等）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化サポート。

  - config_setup.py
    - 対話式ウィザードで `.env` を作成/更新する CLI を追加（secret 値のマスク表示、確認プロンプト、テンプレート生成）。
    - デフォルト値や選択肢を持つ項目定義を実装（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス 等）。

  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在および（PyYAML があれば）パース検証を実施。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共有可能なロギング設定を追加。stdout への StreamHandler と、日次ローテート（30 日保持）の TimedRotatingFileHandler をルートロガーへ設定。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成に失敗した場合は警告を出しファイル出力をスキップするフォールバック。
  - utils/process_priority.py
    - Windows / POSIX の差を吸収するプロセス優先度設定ユーティリティを追加（high/normal/low をサポート）。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）を追加。
    - 権限不足や未サポート環境に対する安全なフォールバックと警告処理。

- Execution 系コンポーネント（参照インターフェース）
  - 実行エンジンまわりの組み立てコード（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager, RiskConfig, EngineConfig）を起動スクリプトに組み込んで使用する構成を実装（実装ファイル自体は本コードスニペット外の想定コンポーネント）。
  - RiskManager のデフォルト設定例（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を採用。初期ポートフォリオ値に broker.get_available_cash() を利用。

- 監視・モニタリング
  - monitoring_db.init_monitoring_db 呼び出しにより監視用テーブルの初期化（冪等）を確保。
  - SystemMonitor の単発チェック check_once() をループで呼び出し、例外はログ出力してループ継続。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコア全てが 0 の場合は等金額にフォールバックし警告ログを出す設計。

  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）を実装。既存保有のセクター別時価を計算し、上限超過セクターの候補を除外。
    - セクター不明（"unknown"）は上限適用外とする扱い。
    - 市場レジームに対する投下資金乗数（calc_regime_multiplier）を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームはフォールバック 1.0 かつ警告ログ）。

  - portfolio/position_sizing.py
    - 発注株数決定ロジック（calc_position_sizes）を実装。allocation_method により "risk_based" / "equal" / "score" をサポート。
    - 単元（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン処理、cost_buffer を考慮した保守的なコスト見積り、そして端数処理（残余キャッシュでの lot 単位追加）を実装。
    - 価格欠損時の安全スキップやデバッグログ出力あり。

- 研究・ファクター計算基盤
  - research/factor_research.py
    - モメンタム等のファクター計算を行うための基礎実装を追加（DuckDB 接続を想定、prices_daily / raw_financials テーブル参照）。（ファイルは計算ロジックの導入を含むが一部スニペットで切れている）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計し PASS/FAIL 判定（閾値はソース内定義）。
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）に対応。
    - P95 計算を含むレポート出力フォーマットを提供。

### Changed
- （初回リリースにつき過去からの変更はなし）

### Fixed
- （初回リリースにつき修正点はなし）

### Security
- シークレット設定（J-Quants トークン、kabu API パスワード等）は .env ファイルに記述する設計。config_setup ではシークレットをマスクして表示。

### Notes / Important behaviors
- 環境分離:
  - run_execution は paper_trading モード時に paper_sqlite_path を使い DB を分離する。一方 monitoring は環境に無関係に sqlite_path（本番監視 DB） を使用する挙動になっているため、環境に応じた運用上の注意が必要（監視データをペーパートレード用に分離したい場合は設定の調整が必要）。
- 自動 .env 読み込みはプロジェクトルートが特定できない場合スキップされる。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- ログディレクトリ作成やプロセス優先度の設定は権限や OS により失敗する可能性があるため、該当失敗時は警告を出して処理を継続する堅牢性設計を採用。

---

将来のリリースでは、細かなバグ修正、より詳細なユニットテスト、Strategy/Execution のコア実装強化、ファクター計算の完成などを予定しています。
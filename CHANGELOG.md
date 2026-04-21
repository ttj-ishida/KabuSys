# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
主要なバージョンは semver に準拠します。

なお、本ドキュメントはソースコードの内容から推測して作成した変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-21

初回公開リリース。

### Added
- 基本アーキテクチャと起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はリポジトリ直下の data/stop_requested.flag ファイル存在で検知。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、Paper トレード専用 DB（data/paper_trading.db）に記録することで本番 DB と完全分離。
    - デーモンスレッドで ExecutionEngine を起動し、stop フラグにより安全に停止可能。
    - 起動時に data/execution.pid ファイルを使用（PID 管理）。

- 設定管理と補助 CLI を追加
  - config.py: 環境変数/.env ロードと Settings クラスを実装。
    - プロジェクトルートを `.git` または `pyproject.toml` から自動検出して .env を読み込む自動ロード機能を実装（無効化可能: `KABUSYS_DISABLE_AUTO_ENV_LOAD`）。
    - `.env` の解析が強化され、`export KEY=val`、クォート文字列、インラインコメントを適切に処理。
    - 各種設定プロパティ（DB パス、PID パス、閾値、環境判定など）を提供。
    - `PAPER_FILL_MODE` の妥当性チェック（`instant/partial/never/reject`）を実装。
  - config_setup.py: 対話式の .env 作成/更新ウィザードを追加。
    - 初期テンプレート、シークレット項目マスク、確認プロンプト付きで .env を生成。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML 未インストール時は警告）等を行う。
    - `--strict` オプションで警告も失敗扱いにできる。

- 監視・実行用 DB 初期化/共通ユーティリティ
  - monitoring_db の初期化処理を呼び出して監視テーブルの存在を保証（冪等）。
  - duckdb, sqlite の両方を利用する設計を採用（分析用 DuckDB + 運用用 SQLite）。

- ロギングとプロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler (日次・30日保持) を設定する共通ユーティリティを追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力で継続。
    - ログレベル / ログディレクトリは引数・環境変数経由で上書き可能。
  - utils/process_priority.py:
    - Windows/Linux/macOS を吸収するプロセス優先度設定機能（"high"/"normal"/"low"）を追加。
    - CPU affinity を最初の N コアに固定する関数を追加。
    - 権限不足や未対応 OS は安全にスキップして警告を出す。

- ポートフォリオ構築関連モジュール（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナル選定（スコア降順、タイブレークは signal_rank）、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別エクスポージャを計算し上限を超えるセクターの候補を除外。`unknown` セクターは制限対象外とする。
    - 市場レジームに基づく資金乗数（calc_regime_multiplier）を実装（"bull"/"neutral"/"bear"）。
  - portfolio/position_sizing.py:
    - 各配分方式（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、アグリゲート上限（available_cash）によるスケーリング、cost_buffer による保守的コスト見積り、残余キャッシュを使った端数配分ロジックを含む。

- 研究用ファクター計算（研究モジュール）
  - research/factor_research.py（モメンタム等の計算ロジックの骨組み）を追加。DuckDB の prices_daily / raw_financials を用いてモメンタム/MA/ATR/出来高等を計算する構成を想定。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を行う。
    - CLI オプションで日付範囲（--from/--to）と DB パス（--db）を指定可能。
    - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。

- パッケージ情報
  - src/kabusys/__init__.py にバージョン `0.1.0` を設定。

### Changed
- （初回リリースのため無し）

### Fixed
- （初回リリースのため無し）

### Security
- （無し）

---

注記（実装上の重要ポイント／挙動）
- run_monitoring は MONITOR_POLL_INTERVAL が不正な値（0 以下や非整数）の場合に警告を出してデフォルトにフォールバックする。
- run_execution は paper_trading 環境時に専用の SQLite を使用するため、本番 DB とデータが混ざらない設計になっている。
- .env 自動ロードはプロジェクトルートが見つからない場合はスキップされるため、配布後の実行環境でも安全に動作する（テスト環境用の無効化オプションあり）。
- logging_setup は stdout を使用する設計（stderr を避ける）により、cron/task scheduler などでのログリダイレクト運用を想定している。
- process_priority や CPU affinity は権限やプラットフォームによって実行できない場合があるため、例外を握りつぶして警告ログで通知する挙動。

もしリリースノートに追記したい詳細（例: 実装上の制限、既知の問題、将来の改善予定など）があれば指示してください。
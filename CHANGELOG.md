# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
要約は日本語で記載しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-20

### Added
- 基本アプリケーションの初期実装を追加しました（初回リリース）。
  - パッケージバージョン: `kabusys` __version__ = `0.1.0`

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御ファイル（data/stop_requested.flag）を監視してループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の `sqlite_path` を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定。
    - sqlite3 / DuckDB 接続を確立し、終了時にクローズ。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` のときは paper-trading 用 DB を使い、MockBrokerClient を利用（本番 DB と分離）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）に対応。
    - 起動時にプロセス優先度を "high" に設定し、ExecutionEngine をデーモンスレッドで実行。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec など）を指定。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env と .env.local の読み込み優先度を実装（OS 環境変数は保護）。
    - 複雑な .env パースを実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱い等）。
    - Settings クラスを導入（J-Quants / kabu API / LINE / DB / 監視 / システム設定等のプロパティを提供）。
    - 環境変数の検証や既定値、型変換（float, Path, bool 等）を実装。
    - 環境変数自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。

- 設定検証 CLI
  - validate_config.py
    - .env と config/*.yaml の事前検証用 CLI を追加。
    - 必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パスの親ディレクトリチェック、YAML ファイルの存在とパースチェック（PyYAML がインストールされている場合）を実施。
    - `--strict` オプションで警告をエラー扱いにするモードを提供。
    - 本番（live）時向けの注意喚起チェック（LINE 通知設定や Kill Switch 設定）を追加。

- 設定ウィザード CLI
  - config_setup.py
    - 対話式で .env ファイルを作成・更新するウィザードを追加。
    - 秘匿項目のマスク表示、選択肢の検証、既存 .env の読み込み・再利用をサポート。
    - .env のテンプレート書き出し（書式化済み）を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を解析して検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）等。
    - 閾値による PASS/FAIL 判定を実装（デフォルト閾値がソースに定義）。
    - 日付フィルタ（--from, --to）と DB パス上書きオプション（--db）をサポート。
    - P95 計算、DB 存在チェック、テーブル欠如時のフォールバック処理を実装。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナルの選別（スコア降順・同点時タイブレーク）を実装（select_candidates）。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）を実装。全スコアが 0 の場合は等配分へフォールバック。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクターエクスポージャ計算と候補除外ロジックを提供。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear + フォールバック）。

  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash を超過する場合のスケーリング）、cost_buffer を考慮した安全側見積もりを実装。
    - 価格欠損時のスキップ、スケーリング時の端数配分ロジックを実装。

  - portfolio/__init__.py
    - 上記関数群をエクスポートするパッケージ初期化を追加。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティを追加。
    - stdout への StreamHandler と、日次ローテーションの TimedRotatingFileHandler（既定 logs/ ディレクトリ、30 日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する堅牢性を実装。
    - ログレベルとログディレクトリは引数 / 環境変数 / デフォルトの順で解決。

  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度（high/normal/low）設定機能を追加（Windows の優先度クラスと POSIX の nice 値を吸収）。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）を追加。
    - 設定失敗時は警告を出してスキップする挙動。

- 研究用ファクターモジュール（準備）
  - research/factor_research.py
    - モメンタム等のファクター計算の枠組みを追加（DuckDB 接続を想定）。モジュールは関数と定数を定義（実装途中でファイル末尾が切れている箇所あり）。

### Changed
- なし（このリリースは初期追加が主体）

### Fixed
- なし（初期実装に関する既知の仕様を追加）

### Notes / Usage Tips
- 環境変数自動ロード
  - デフォルトでプロジェクトルートの `.env` と `.env.local` を自動読み込みします。テスト等で自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - OS 環境変数は `.env` による上書きから保護されます（`.env.local` を含む）。

- Monitoring と Execution の DB
  - run_monitoring は常に Settings.sqlite_path（"data/monitoring.db" がデフォルト）を使用します。
  - run_execution は `KABUSYS_ENV=paper_trading` の場合に paper_sqlite_path（デフォルト "data/paper_trading.db"）を使用し、本番 DB と完全に分離します。

- ログ
  - デフォルトでは logs/<app_name>.log に日次ローテーションでログが保存されます。`LOG_DIR` 環境変数または setup_logging の引数で変更可能です。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

- CLI
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

### Known limitations / TODO
- research/factor_research.py の実装が途中（ファイル末尾が切れている/未完の箇所あり）。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別単元対応の予定）。
- apply_sector_cap の価格欠損（price == 0.0）の扱いに注意（現状は過少見積りとなる可能性あり、改善のためのフォールバック価格検討予定）。
- run_monitoring のモニタリング DB は常に本番パスを使うため、開発用途での切り替えに注意。

---

（注）本 CHANGELOG はソースコードから推測して作成しています。実際のユーザ向けリリースノートとして公開する場合は、実際の変更履歴・コミットログ・リリーステスト結果に基づいて調整してください。
# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。ここに記載した内容は提供されたコードベースから推測してまとめたリリースノートです。

全般的な注意
- 以下はソースコードの内容から機能追加・挙動を推測して作成した CHANGELOG です。実際のコミット履歴ではありません。

## [Unreleased]

## [0.1.0] - 2026-04-20

初回リリース。日本株自動売買システム「KabuSys」の基本ユーティリティ群、実行スクリプト、設定ツール、ポートフォリオ構築/サイズ決定ロジック、ペーパートレード検証ツール、監視機能などを含む初期実装を追加。

### Added
- 基本バージョン情報
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 実行・運用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト配下 `data/stop_requested.flag` の検出で行う。
    - 監視は KABUSYS_ENV に関係なく本番用の sqlite_path を使用する（監視用 DB 初期化処理を呼び出す）。
    - duckdb 接続を併用。
    - 例外発生時のログ出力と次のポーリングへのフォールバック処理を装備。

  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（デフォルト `data/paper_trading.db`）へ記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ `data/stop_requested.flag` と PID ファイル管理（`data/execution.pid`）に対応。
    - スレッドで実行エンジンを起動し、定期的に停止フラグを監視して安全に停止する実装。

- 設定管理
  - config.py
    - 環境変数の取得をカプセル化する `Settings` クラスを追加。
    - 自動 .env ロード機能（プロジェクトルート探索: .git / pyproject.toml を基準）を実装。優先順位は OS 環境 > .env.local > .env。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 各種設定項目をプロパティで提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, Kill Flag 設定、閾値設定など）。
    - `PAPER_FILL_MODE` の値検証（許容値: "instant", "partial", "never", "reject"）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の許容値チェック（不正なら ValueError）。

- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成・更新するツールを追加。
    - J-Quants トークン、kabu API パスワード、DB パス、ログレベル、Kill Flag など必要項目を対話的に入力可能。
    - 既存 `.env` の読み込み・既存値の再利用、シークレット項目のマスク表示をサポート。

  - validate_config.py
    - 起動前に `.env` および `config/*.yaml` の基礎的な検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML 有無で挙動を分岐）、本番環境向けの追加ガードを実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築 / ポジションサイズ
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定 `select_candidates` を追加（スコア降順、同点は signal_rank でブレーク）。
    - 等金額配分 `calc_equal_weights`、スコア加重 `calc_score_weights` を実装（スコア合計が 0 の場合は等金額にフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap` を実装（当日売却予定銘柄の除外、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた資金乗数 `calc_regime_multiplier` を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームは警告のうえ 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - 株数決定ロジック `calc_position_sizes` を実装。
    - risk_based / equal / score の配分方式に対応。
    - ロット単位（lot_size）で丸め、1銘柄上限・aggregate cap（available_cash）を考慮したスケーリングと残差分配アルゴリズムを実装。
    - cost_buffer（スリッページ/手数料見積り）を考慮した保守的なコスト計算。
    - 価格欠損時のスキップやログ出力を実装。

- 監視・モニタリング DB 初期化
  - monitoring/monitoring_db の初期化呼び出しを run_monitoring/run_execution で行い、監視テーブルが存在することを保証（冪等）。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一ロギング初期化 `setup_logging` を追加。
    - stdout への StreamHandler（stdout 使用）と日次ローテート（TimedRotatingFileHandler）を設定、デフォルトは `logs/` ディレクトリ、30 日保持。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみにフォールバック。

  - utils/process_priority.py
    - プロセス優先度設定 `set_process_priority` を追加（Windows の priority class / POSIX の nice を吸収）。
    - CPU affinity を設定する `set_cpu_affinity` を追加（利用可能コア数の範囲チェックと失敗時の警告）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率(uptime)、注文成立率(fill rate)、送信率(send rate)、レイテンシ（avg/max/P95）、リスク却下数などを算出して PASS/FAIL 判定（閾値はソースコード内定義）。
    - 日付フィルタ（--from/--to）対応、DB パスは引数または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。
    - P95 計算等のユーティリティ実装。

- リサーチ/ファクター（部分実装）
  - research/factor_research.py
    - モメンタム/ボラティリティ等のファクター計算を行うベースを追加（DuckDB 接続を受け、prices_daily / raw_financials を参照する設計）。
    - 設計方針や定数（21/63/126/200 日等）を定義。モジュールは純粋関数群での計算を想定。

- パッケージエクスポート
  - portfolio モジュールの公開 API を __all__ で定義（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

### Changed
- ロギングの挙動
  - 既存ルートロガーのハンドラをすべてフラッシュ/クローズしてから再設定するように変更（重複ハンドラ防止）。

- .env のパース仕様
  - export プレフィックス対応、クォート内のバックスラッシュエスケープやインラインコメントの扱い、クォートなし時のコメント判定ルールなど、より堅牢な .env パーサー実装。

### Fixed
- 環境値の堅牢性
  - MONITOR_POLL_INTERVAL の不正値（0 以下や整数変換失敗）に対し警告を出しデフォルトにフォールバックする処理を追加（time.sleep に渡せない値を防止）。

### Security
- 秘密情報の取り扱い
  - config_setup の対話ウィザードでシークレット項目をマスク表示するなど、秘密情報 (トークン/パスワード) の扱いに配慮。

### Known limitations / Notes
- research/factor_research.py は途中（コメントの末尾で切れている部分あり）で、完全実装が未完の可能性あり。
- run_monitoring/run_execution は外部コンポーネント（SystemMonitor、ExecutionEngine、BrokerClientFactory 等）に依存しており、それらの実装により挙動が決まる。
- デフォルトのファイルパス（data/*.db, logs/）はプロジェクトルート相対で扱われるため、配備時に適切なディレクトリ作成やパーミッション設定が必要。

---

（補足）この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミットメッセージや変更履歴がある場合はそちらを基にした正式な CHANGELOG の作成を推奨します。
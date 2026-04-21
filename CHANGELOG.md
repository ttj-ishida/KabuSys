# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。  

履歴はコードベース（snapshot）から推測して作成しています。実装ファイル名や動作の詳細は当該ソースを参照してください。

## [Unreleased]

（現在のスナップショットに基づく未リリースの変更はありません）

## [0.1.0] - 2026-04-21

初期リリース（推定）。以下の主要機能・ユーティリティ・CLI を実装／追加しました。

### Added
- コア情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `0.1.0` と定義。

- 起動スクリプト
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor をポーリングするループを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 `data/stop_requested.flag` の存在で検知。
    - Monitoring は環境にかかわらず本番用の `sqlite_path`（`Settings.sqlite_path`）を使用して DB に接続。
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine をスレッドで起動／監視するロジック。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient（BrokerClientFactory 経由）を使用し、paper_trading 用 DB（デフォルト `data/paper_trading.db`）へ完全分離して記録。
    - 起動前に `data/stop_requested.flag` の有無をチェックして起動抑止可能。
    - 実行状況用 PID ファイルを利用（`data/execution.pid` など）。

- 設定管理
  - 環境変数/.env 管理モジュールを実装（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロード（無効化フラグあり: `KABUSYS_DISABLE_AUTO_ENV_LOAD`）。
    - .env パーサは `export KEY=val`、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - 各種設定プロパティをラップ：DB パス（DuckDB, SQLite）、LINE トークン、kabu API、Paper Trading 設定（`PAPER_FILL_MODE` 有効値制約）など。
    - `Settings` クラスで `env` / `is_live` / `is_paper` 等を提供。
  - 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。
    - `.env` ファイルの初期作成・更新を支援。シークレットはマスク表示、選択肢・デフォルト対応。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML 利用時の）パース検証、本番時のガードチェック（LINE 通知設定や Kill Switch の自動クリア設定警告）を実行。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング/プロセス制御ユーティリティ
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（毎日ローテーション、30日保持）を設定。
    - ログディレクトリ作成に失敗した際はファイル出力をスキップしてコンソールのみで継続するフェイルバックを実装。
    - ログレベルは引数 > 環境変数(LOG_LEVEL) > デフォルト の優先順で解決。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/macOS/FreeBSD）を吸収する実装。優先度（high/normal/low）設定と、最初 N コアに固定する CPU affinity 機能を提供。
    - 権限不足や未対応環境では警告を出してスキップする安全設計。

- ポートフォリオ構築関連（純関数群）
  - 候補選定とウェイト計算（src/kabusys/portfolio/portfolio_builder.py）。
    - シグナルのスコア降順選定、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - セクター集中制限とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター上限チェック（既存ポジションの時価ベースで比較し、上限を超えるセクターの新規候補を除外、「unknown」セクターは除外対象外）。
    - レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームは警告して 1.0 にフォールバック）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method による発注株数算出（risk_based / equal / score）。
    - 単元株（lot_size、デフォルト 100）丸め、1 銘柄上限（max_position_pct）、投下上限（max_utilization）、コストバッファ考慮、available_cash を超える場合のスケーリングと端数処理を実装。
    - risk_based 方式では損失率（stop_loss_pct）を用いて株数を逆算。

- 研究（ファクター算出）
  - DuckDB 接続を用いたファクター計算モジュール（src/kabusys/research/factor_research.py）。
    - Momentum, Value, Volatility, Liquidity 系の指標を設計に基づいて算出するための骨子／定数を実装（prices_daily / raw_financials テーブル参照を想定、栄養分の足跡あり）。

- 実行／監視用 DB 初期化
  - 監視用 DB 初期化ヘルパー（`init_monitoring_db`）を参照して、起動時に監視テーブル存在保証（冪等）を行う呼び出しを run_monitoring/run_execution で実施。

- ペーパートレード検証ツール
  - Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成立率、送信率、リスク却下数、レイテンシ（平均/最大/P95）等を SQLite の paper_trading DB から集計。
    - 閾値（稼働率 99% など）を用いた PASS/FAIL 判定を実装。
    - コマンドラインオプションで期間指定および DB パス指定可能。

- 実行フローに関する細部
  - 起動時に最初にプロセス優先度を "high" に設定する設計（run_monitoring/run_execution）。
  - ExecutionEngine 起動時に RiskManager の設定（デフォルト値群）を組み立て、初期ポートフォリオ値は broker.get_available_cash() から取得して RiskConfig に渡す。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- シークレット値（J-Quants トークン、kabu API パスワード、LINE トークン）は .env で管理する設計。config_setup は .env を生成する際にコメントで Git にコミットしないよう注意喚起。

### Notes / Behavior highlights (重要な運用注意)
- run_monitoring は KABUSYS_ENV に関係なく常に `Settings.sqlite_path`（本番用 monitoring DB）を使用する実装になっている点に注意。テストやペーパートレードと監視用 DB を分離したい場合は運用上の配慮が必要。
- run_execution は paper_trading 環境の場合に専用 DB（`PAPER_TRADING_SQLITE_PATH`）を利用するため、本番 DB と完全分離される。
- ログディレクトリ作成失敗時はファイル出力が無効化されコンソール出力のみになるため、権限やパスの設定に留意すること。
- process priority / cpu affinity の設定は環境・権限依存で失敗する可能性がある（警告を出してスキップされる）。
- .env の自動読み込みはプロジェクトルートが検出できない場合や `KABUSYS_DISABLE_AUTO_ENV_LOAD` が設定されている場合はスキップされる。

---

タグ:
- [0.1.0]: 初期リリース（上記参照）

（注）本 CHANGELOG は与えられたソースツリーの内容から推測して作成しています。実際のリリースノートには、コミット単位の変更詳細、著者、影響範囲、マイグレーション手順などを追加してください。
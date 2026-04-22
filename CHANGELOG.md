# Changelog

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。  

※ 本リリースはコードベースから推測して作成した CHANGELOG です。実際のコミット履歴とは異なる可能性があります。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-22

初回リリース相当。システム全体のコア機能（設定管理、起動スクリプト、ポートフォリオ構築ロジック、ユーティリティ、検証/ウィザード、Paper Trading 用レポート等）を実装・提供。

### Added
- 全体
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
  - ドキュメント風のモジュールレベル docstring を多数追加し、各モジュールの役割と使用方法を明記。

- 起動スクリプト / デーモン
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止フラグファイル (data/stop_requested.flag) による安全停止に対応。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番DBと分離。
    - BrokerClientFactory 経由でブローカークライアントを切替可能（Mock を想定した paper_trading 対応）。
    - スレッドで ExecutionEngine を起動し、停止フラグ検知で Engine.stop() を呼ぶ安全停止処理を実装。
    - PID ファイル出力サポート（data/execution.pid）。

- 設定管理 / ユーティリティ
  - config.py: Settings クラスを導入し、環境変数・.env 自動読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み（無効化フラグあり）。
    - .env のパースを強化（export プレフィックス対応、クォート内のエスケープ、インラインコメント処理など）。
    - 各種プロパティを提供：duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode（値検証あり）、pid_file_path, kill_flag_path, CPU/Mem/Disk 閾値など。
    - KABUSYS_ENV の検証（development/paper_trading/live のみ許容）や LOG_LEVEL 検証を実装。
  - config_setup.py: 対話式 .env ウィザードを実装。
    - 既存 .env の読み込み・編集をサポート。秘密項目はマスク表示。保存時に注意文を出力。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML がある場合は）パース確認を実施。
    - --strict オプションで警告を失敗（exit(1)）扱いにできる。

- Portfolio / 戦略関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で上位 N を選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合に等配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存ポジションの比率計算、上限超過セクターの新規候補除外）。unknown セクターは上限適用除外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知のレジームは警告を出して 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 重み・候補・資金状況から各銘柄の発注株数を計算（allocation_method: "risk_based"/"equal"/"score"）。
      - 単元株（lot_size）丸め、1銘柄上限・aggregate 上限、cost_buffer（手数料スリッページバッファ）を考慮したスケーリング処理を実装。
      - aggregate cap を超える場合のスケールダウンと remainder に基づく再割当ロジックを含む。

- 研究モジュール
  - research.factor_research: DuckDB 接続を受けてモメンタム等のファクター群を計算する設計（モメンタム、MA200 乖離、ATR、出来高等に関する定義と計算方針を記載）。（ファイルは部分実装）

- モニタリング / Paper Trading レポート
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（平均/最大/P95）等を集計して PASS/FAIL 判定を行う。
    - デフォルトの閾値を定義（稼働率 >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 <= 200ms）。
    - --from/--to/--db オプションをサポート。

- utils
  - utils.logging_setup: 統一的なロギング初期化ユーティリティを提供。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーにセット。
    - 既存ハンドラをクリアして二重登録を防止。
    - ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX を吸収して高/普通/低 優先度切替を提供。
    - CPU affinity を最初の N コアに固定する関数も追加（利用可能なコア数を超える指定は全コア使用にフォールバック）。
    - 権限不足等の例外は警告を出してスキップ。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼ぶことで監視用テーブルの存在を保証（冪等に初期化可能）。

### Changed
- logging 設定
  - StreamHandler の出力先を stderr ではなく stdout に変更（cron / Task Scheduler のリダイレクトを想定して stdout を使用）。
  - ルートロガーの既存ハンドラを安全に flush/close してから削除することで、複数回の初期化時にハンドラが重複しないようにした。

- 設定読み込み順序
  - OS 環境変数 > .env.local > .env の優先順位で自動ロードする挙動を文書化・実装。OS 環境変数は保護され自動上書きされない。

- Process priority
  - Windows と POSIX の差分をラップし、呼び出し側でプラットフォームを意識しなくて良い API に統一。

### Fixed
- .env パーサ
  - export KEY=... 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなどを改善し、より実用的な .env パースに対応。
- init_monitoring_db の呼び出しを冪等に行うようにして、既存DBがあっても安全にスクリプトを起動できるようにした。
- run_monitoring のポーリング間隔取得で不正値（0以下や非数）を検出した場合にデフォルトへフォールバックし、警告を出すように改善（time.sleep に渡す不正値回避）。
- run_execution / run_monitoring における停止フラグ検知ロジックを追加（data/stop_requested.flag による外部停止）。

### Security
- .env ファイル生成テンプレートに対して「絶対に Git にコミットしないこと」の注意を明示した。
- config_setup で秘密項目（API トークン等）はマスクして表示するユーザビリティを実装。

### Notes
- validate_config は PyYAML がない環境でも動作し、YAML パース検証は PyYAML に依存してスキップされる旨を警告する。
- paper_trading 環境は本番 DB と明確に分離され、専用 SQLite を使用する設計（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）。
- 一部モジュール（research.factor_research 等）は設計に関するコメントと部分実装を含み、さらなる実装が想定される。

---

今後の候補（未実装 / 要検討）
- 各モジュールに対するユニットテスト・統合テストの追加。
- position_sizing の lot_size を銘柄毎に持たせるための stocks マスタ導入（コメントに TODO）。
- apply_sector_cap の price 欠損時のフォールバック戦略（前日終値等）の実装。
- ExecutionEngine / Broker クライアントの詳細なエラー復旧戦略・リトライロジックの強化。
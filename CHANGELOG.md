# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初回リリース履歴を、ソースコードから推測して作成しています。

全般的な注意
- バージョン情報は src/kabusys/__init__.py の __version__ = "0.1.0" に基づきます。
- 日付は本ファイル作成日（2026-04-21）を採用しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-21

### Added
- 基本アプリケーションパッケージ（kabusys）。
  - バージョン定義: src/kabusys/__init__.py にて __version__ = "0.1.0" を追加。

- 実行用スクリプト
  - run_monitoring: 監視（SystemMonitor）ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルート/data/stop_requested.flag により制御。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用して DB に接続。
    - SQLite（監視 DB）および DuckDB への接続初期化を行う処理を含む（init_monitoring_db 呼び出し）。
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動と停止制御（stop flag, execution.pid の取り扱い）を実装。
    - スレッドでエンジンを実行し、stop flag を検知して安全に停止するループを実装。

- 設定管理
  - Settings クラス（src/kabusys/config.py）を追加。
    - .env の自動読み込み機構（プロジェクトルートを自動検出し .env → .env.local の順に読み込み、OS 環境変数を保護）。
    - 各種設定プロパティを提供（J-Quants、kabu API、LINE、DuckDB/SQLite パス、paper trading 用設定、監視・しきい値、環境判定フラグなど）。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の有効値チェック等を実装。
    - 環境自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup: 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - よく使う項目を一覧化し、既存 .env の読み込み・編集、秘密項目マスク表示、ファイルへの書き込みをサポート。
    - デフォルト値や選択肢、説明文を用意。

- 設定検証 CLI
  - validate_config: .env と config/*.yaml の静的検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース検証（PyYAML がある場合）を実行。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の危険性警告）を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（pure function 群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順＋signal_rank で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。スコア合計が 0 の場合は等配分にフォールバックし警告。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中制限ロジック（既存ポジションのセクター比率に基づき候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer 加味の安全弁、端数処理ロジックを実装。

- ユーティリティ
  - logging_setup（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR による設定、既存ハンドラのクリーンアップ、ファイル出力不可時のフォールバックを実装。
  - process_priority（src/kabusys/utils/process_priority.py）
    - プラットフォーム差分を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を追加。
    - Windows（psutil の優先度クラス）と POSIX（nice 値）の両対応・権限不足時の警告ハンドリングを実装。

- モニタリング DB 初期化フック
  - init_monitoring_db 呼び出しにより、監視用テーブルが存在することを保証する処理を run_monitoring/run_execution の起動フローに追加（冪等な初期化）。

- Paper Trading 検証ツール
  - tools/paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード（SQLite）から稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均／最大／P95）を算出するレポート生成ツールを追加。
    - CLI オプション --from / --to / --db に対応。閾値による PASS/FAIL 判定（稼働率、成功率、送信率、P95 レイテンシ）を実装。
    - P95 計算ユーティリティ、日付フィルタ生成と SQL クエリを実装。

- 研究用ファクター計算（部分実装）
  - research/factor_research（src/kabusys/research/factor_research.py）
    - モメンタム、移動平均乖離、ATR、出来高系などファクター設計方針と定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - calc_momentum の導入と注釈（実装途中）。（ファイルは導入済みだが、関数実装は途中で切れている可能性あり）

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- （該当なし）

---

メモ（実装上の重要点）
- Settings による環境変数の厳密チェックと .env 自動読み込み機構により、環境依存の初期設定ミスを未然に防ぐ設計になっています。自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を備えています。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値に対するフォールバック処理（デフォルト 60 秒）を備えています。
- run_execution は paper_trading と live を明確に分離しており、ペーパートレード時は本番 DB と完全分離した SQLite を使用します。
- logging_setup は標準出力を stdout に出す点に注意（cron 等で stdout/stderr を一本化する運用を考慮）。

補足
- 本 CHANGELOG は、与えられたソースコードから推測して作成しています。実際のコミット履歴や変更差分がある場合は、そちらに合わせて調整してください。
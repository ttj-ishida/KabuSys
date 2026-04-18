CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

現在のバージョン: 0.1.0 (初回リリース)
リリース日: 2026-04-18

Unreleased
----------
（このファイルはリポジトリの状態から推測して作成しています。将来の変更はここに追記してください。）

0.1.0 - 2026-04-18
------------------

Added
- 基本パッケージ・バージョン
  - パッケージバージョンを設定: `kabusys.__version__ = "0.1.0"` 。

- 実行エントリ / ランチャー
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検出による安全な停止、KeyboardInterrupt による停止対応。
    - 監視は環境設定にかかわらず本番用の SQLite パス（Settings.sqlite_path）を使用する設計。
    - monitor.check_once() の例外はログ出力してループ継続する耐障害性を実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 用の専用 SQLite（`data/paper_trading.db`、環境変数で上書き可）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を経由してブローカークライアントを生成（モックの切替想定）。
    - ExecutionEngine をデーモンスレッドで実行、停止フラグ検出で安全停止・タイムアウト join を実装。
    - 実行時 pid ファイル（data/execution.pid）を利用する設計。

- 設定・環境管理
  - config.py
    - Settings クラスを追加し、環境変数経由で各種設定値を取得・検証する API を提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）。
    - `.env` 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env の自動ロードは OS 環境変数を保護（上書き保護）する仕組みを導入。
    - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）や KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
    - 利便性プロパティ: is_live / is_paper / is_dev などを提供。

  - config_setup.py
    - 対話式 .env ウィザード（CLI）を追加。初期 .env の作成や更新を支援。
    - シークレット入力や選択肢、デフォルト値の提示、保存前の確認を実装。
    - .env 書き込みテンプレートで秘匿すべきこと（Git へコミットしない等）を注記。

  - validate_config.py
    - 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパース（PyYAML がある場合）を実施。
    - `--strict` オプションで警告を失敗扱いにすることが可能。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・同点タイブレーク処理による候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア重み配分（全スコア 0 の場合は等配分にフォールバック）を実装。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮）と候補絞り込みを実装。unknown セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知のレジームは 1.0 にフォールバックし警告ログを出力。

  - portfolio.position_sizing
    - calc_position_sizes: 発注株数決定ロジック（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）に基づく丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、端数配分アルゴリズムを実装。
    - 不十分データ（価格 missing 等）に対するログ出力とスキップ処理を実装。

- ユーティリティ
  - utils.logging_setup
    - 統一ロギング設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーへ設定。既存ハンドラのクリア処理を実装。
    - ログレベルとログディレクトリの解決ルール（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続するフォールバック。

  - utils.process_priority
    - クロスプラットフォームなプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する実装。権限不足や未対応 OS は警告ログでスキップ。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブルの存在を保証（冪等）。

- Paper Trading 検証ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite を参照して検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL する基準を導入（しきい値はソース内定義）。
    - 日付フィルタ（--from / --to）や DB パスの上書き（--db / 環境変数）に対応。
    - レポートは N/A を扱う堅牢な実装。

- リサーチ（ドラフト）
  - research.factor_research
    - ファクター計算モジュールのスケルトンとモメンタム計算の設計定数を追加（momentum, MA200, ATR 等）。
    - DuckDB を利用し prices_daily / raw_financials 参照を想定する設計方針。

Changed
- ログ出力の挙動
  - logging_setup により、デフォルトでログは stdout に出力され、ファイルは日次ローテーションで保持されるように統一。

- .env 自動ロードの挙動
  - 自動ロード時に OS 環境変数を上書きしない（保護）挙動を採用。明示的に .env.local を優先上書きできる仕組みを提供。

Fixed
- 耐障害性の改善
  - run_monitoring のポーリング内で monitor.check_once() が例外を投げてもループを継続するように変更し、監視プロセスの自己回復性を向上。
  - run_execution / run_monitoring の終了処理で DB 接続（sqlite, duckdb）を必ずクローズするよう保護。

- .env パーサの堅牢化
  - export 形式の行、シングル/ダブルクォート値、バックスラッシュによるエスケープ、インラインコメントの扱いなどに対応するパーサを実装。無効行は無視。

Notes / Migration
- 新たに導入された（または利用可能な）環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH,
    LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, PAPER_TRADING_SQLITE_PATH, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID など。
- Monitoring の挙動:
  - run_monitoring は明示的に「監視は環境にかかわらず本番 sqlite_path を使用する」設計になっています。Paper Trading とは DB を共有しない意図的な選択である点に注意してください。
- Paper Trading:
  - `KABUSYS_ENV=paper_trading` の場合、Execution は paper 用 DB を使用し発注は MockBrokerClient 想定（BrokerClientFactory による切替）。
- ログファイル:
  - デフォルトのログディレクトリは `logs/` です。ファイル出力失敗時はコンソールのみで継続します。

Acknowledgements / Implementation details
- 多くのモジュールは「外部サービス（ブローカー / 実際の発注）へ直接アクセスしない」方針で設計されています（テスト・検証の容易さを優先）。DuckDB / SQLite をローカル DB に用いることで分析と監視を分離しています。
- 一部の関数は将来的な拡張を示唆する TODO コメントを含みます（例: 銘柄ごとの lot_size 管理、価格フォールバック戦略など）。

今後の予定（例）
- research.factor_research の完全実装（各ファクター計算ロジックの完成）。
- ExecutionEngine / Broker 関連の詳細実装と e2e テストの追加。
- より詳細なドキュメント（運用手順、監視ダッシュボード、コンフィグ例）の整備。

---

本 CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。実際のコミット履歴や設計意図と若干の差異がある可能性があります。必要であれば、具体的なコミットログやリリースノートに合わせて修正・精緻化できます。
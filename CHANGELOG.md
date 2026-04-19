CHANGELOG.md
=============

この変更履歴は Keep a Changelog のフォーマットに準拠しています。  
コードベースの内容から推測して記載しています。

Unreleased
----------
変更予定 / 既知の TODO（コード中のコメントや TODO に基づく推測）

Added
- 銘柄ごとの単元（lot_size）を銘柄マスタに持たせる拡張（position_sizing の TODO）。
- price が欠損している場合のフォールバック価格（前日終値や取得原価）を利用するロジックの追加（risk_adjustment の TODO）。

Changed
- calc_regime_multiplier の既知レジーム以外の振る舞いの見直し（現在はフォールバックで 1.0 を返すが、将来的に扱いを明確化予定）。

Fixed
- なし（将来のリリースで対応予定の改善点を一覧化）。

0.1.0 - 2026-04-19
------------------

Added
- 基本パッケージ初期実装を追加。
  - パッケージバージョン: __version__ = "0.1.0"
- 実行用エントリポイント / 管理スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時には paper_trading 用 DB を使用し MockBrokerClient を利用する設計（本番 DB と分離）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）に対応。
- 環境・設定管理
  - config.py: Settings クラスで環境変数の管理を集約。自動 .env ロード機能（.env / .env.local、OS 環境変数の保護）、PAPER_FILL_MODE 等のバリデーション、各種パスや閾値（CPU / memory / disk）などをプロパティ化。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。シークレットマスク機能、デフォルト値、オプション項目の扱いをサポート。.env 保存テンプレートを生成。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば）をチェック。--strict モードをサポート。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーの一括設定ユーティリティを追加。stdout へ StreamHandler、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定。既存ハンドラのクリア、ログディレクトリ設定（LOG_DIR 環境変数または引数）を実装。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定を追加（psutil を使用）。Windows と POSIX の差を吸収し、権限不足や未対応環境では警告を出してスキップする安全設計。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計がゼロのときは等分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear を想定）を実装。未知レジームはフォールバック（1.0）。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装（allocation_method="risk_based" / "equal" / "score"）。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、残余の割当てロジックを実装。
- Execution コンポーネントの組み立て
  - run_execution.py 内で BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み合わせによる実行フローを実装。RiskManager のデフォルト構成（max_position_pct 等）と initial_portfolio_value を broker.get_available_cash() から取得。
- 監視関連
  - run_monitoring.py: SystemMonitor の定期チェックループを実装。DB 初期化（init_monitoring_db）を行い、SQLite と DuckDB 接続を確立。例外時はロギングして次ポーリングに進む安全設計。プロセス優先度を最初に High に設定。
- 解析・レポートツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。指定期間（--from/--to）で SQLite（PAPER_TRADING_SQLITE_PATH）から以下を集計:
    - system_status テーブルから稼働率（uptime）、ポーリング総数、エラー数
    - trade_logs テーブルから Created/Filled/Sent に基づく注文成功率・送信率、レイテンシ（AVG/MAX/P95）
    - risk_logs からリスク却下数
    - 基準値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）による PASS/FAIL 判定
- データリサーチ基盤（骨格）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（モメンタム、MA200、ATR、出来高系などの定数と calc_momentum の開始）。DuckDB を利用する設計を示唆。
- その他
  - utils/__init__.py, tools/__init__.py 等のパッケージ初期化ファイルを追加。
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を参照するコードを各所で使用して監視テーブルの存在を保証。

Changed
- .env 読み込みロジックの強化（config.py）
  - export KEY=val 形式、クォートされた値のバックスラッシュエスケープ、行内コメントの扱いなどをサポート。
  - 自動読み込みの優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- run_execution.py / run_monitoring.py の DB 接続周りで明示的に接続を close するように改善（finally でのクローズ）。
- logging_setup: 既にハンドラが設定されている場合は一度クリアしてから再設定することで二重出力を防止。
- logging_setup: 標準出力は stdout を利用（cron 等で stdout/stderr を一本化する運用を想定）。
- process_priority: 権限不足や未対応環境でも例外で停止せず警告に留めるよう改善。

Fixed
- MONITOR_POLL_INTERVAL の不正（数値以外や 0 以下）を検出してデフォルトにフォールバックし、ValueError によるクラッシュを防止（run_monitoring.py）。
- run_execution.py: 起動前に停止フラグが立っている場合はエンジンを起動せずに終了する安全措置を追加。
- paper_verification_report: データ不足やテーブル未存在時に sqlite3.OperationalError を捕捉してレポート生成を継続できるように耐性を追加。
- position_sizing: 価格欠損時にログを出して銘柄をスキップするようにし、価格無しでの誤発注を回避。
- risk_adjustment.apply_sector_cap: "unknown" セクターはセクター上限適用から除外する仕様を明確化。

Security
- config_setup.py で生成される .env テンプレートに注意喚起を記載（.env を絶対に Git にコミットしないこと）。
- 対話式ウィザードではシークレットをマスクして表示。

Notes / Known limitations
- research/factor_research.py は一部実装が途中の状態（calc_momentum の実装途中など）。DuckDB を受け取る設計だが、完全なクエリ実装は含まれていない可能性あり。
- position_sizing の将来的な拡張ポイント（銘柄毎の lot_size マスタや価格フォールバック）がコード内に TODO コメントとして残されている。
- process_priority と set_cpu_affinity は psutil に依存しており、一部 OS や実行環境で期待通りに動作しない場合がある（警告ログでスキップする）。

----

補足:
- 本 CHANGELOG はソースコード内のコメント、関数名、CLI ヘルプ、TODO コメント等から推測して作成しています。必須の変更点や未記載の内部実装は存在する場合があります。必要があれば、各モジュールの実装差分やコミット履歴を元により正確な履歴を作成できます。
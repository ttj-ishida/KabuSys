CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

Unreleased
----------

（ありません）

0.1.0 - 2026-04-18
------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基礎機能を追加。
- 実行用エントリスクリプトを追加:
  - run_execution.py: ExecutionEngine の起動ロジック、ブローカーファクトリ、OrderManager、RiskManager、Reconciler の結合、スレッド実行と停止フラグ監視を実装。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db または環境変数で指定）を使用する分離設計を採用。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を参照する設計。
- 設定管理とウィザード / 検証ツールを追加:
  - config.py: 環境変数の読み込み・解釈を実装（.env/.env.local の自動読み込み、export 形式や引用符・エスケープに対応）。Settings クラスに各種設定プロパティを提供（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等）。
  - config_setup.py: .env の対話式ウィザード（項目定義、既存値の読み込み/上書き、シークレットマスキング、保存）を実装。
  - validate_config.py: 起動前の設定検証 CLI（必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検査、live 環境向けの追加安全チェック）。--strict オプションをサポート。
- ポートフォリオ構築ロジック（純粋関数群）を実装:
  - portfolio/portfolio_builder.py: シグナル選定（score 降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（既存保有を考慮し上限超過セクターの候補除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear を扱い未知はフォールバック）。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株（lot_size）丸め、per-stock と aggregate のキャップ処理、cost_buffer による保守的見積り、スケールダウンと残差分配ロジック。
- 分析インフラ:
  - DuckDB を利用するためのパス設定（Settings.duckdb_path）と接続箇所を用意（Execution / Monitoring で利用）。
- 監視関連:
  - monitoring 側の DB 初期化ユーティリティ呼び出し（init_monitoring_db）を各起動スクリプトで保証（冪等）。
  - 停止フラグ / PID ファイルのパス管理（data/stop_requested.flag, data/execution.pid 等）を統一的に使用。
- ログとプロセス制御ユーティリティ:
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで動作。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows/Linux/Mac 等の差分を吸収し、権限不足等の例外は警告でフォールバック。
- Paper Trading 向け検証ツール:
  - tools/paper_verification_report.py: ペーパートレード用 SQLite からシステム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。閾値（稼働率 99%、成立率 90% など）に基づく PASS/FAIL 判定を実装。--from/--to/--db オプションをサポート。
- research/factor_research.py（ファクター計算モジュール）を実装（モメンタム等の計算ロジック開始。DuckDB 接続を想定）。設計方針と定数を定義。

Changed
- (初版のため変更履歴はなし。実装上の設計/デフォルト値をドキュメント化)
  - Execution 側のデフォルト RiskManager 設定値をコード内で定義（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - run_monitoring はポーリング時に check_once() の例外を捕捉してログ出力し、ループは継続する堅牢化を実装。
  - .env 読み込みロジックの優先順位は OS 環境変数 > .env.local > .env（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
  - .env パースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート無しの # の扱い）に対応するよう堅牢化。
  - logging_setup は stdout（stderr ではなく）へ出力するように設計（cron 等からのリダイレクトを想定）。

Fixed
- ファイルハンドラ作成やログディレクトリ作成に失敗した場合にスクリプトがクラッシュしないように保護（フォールバック: コンソール出力のみ）。
- process_priority / set_cpu_affinity で権限不足や未対応 OS に対して例外を吐かず警告でフォールバックするように修正。

Security
- config_setup の表示/確認時にシークレット項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN 等）をマスクして表示。
- .env の生成時に「.env は絶対に Git にコミットしないこと」と明示。

Known issues / Notes
- research/factor_research.py はファイル末尾で途中（start_da から途切れ）となっているので、モメンタム計算の SQL 実装が未完の可能性あり。今後のリリースで完成予定。
- PAPER_FILL_MODE の有効値チェックを行うが、MockBrokerClient 側での挙動実装に依存するため、ペーパー発注の正確な挙動はブローカ実装次第。
- monitoring は現在「環境に関わらず本番 sqlite_path を使用する」旨がコードコメントにあるため、運用時は監視用 DB 設計に注意すること（意図的な仕様か確認推奨）。
- 一部 TODO コメントあり（例: position_sizing の銘柄別 lot_size 拡張、price 欠損時のフォールバック戦略など）。

Developer notes
- バージョン情報は src/kabusys/__init__.py の __version__ を更新してください。
- 追加の設定検証ルールや config/*.yaml のテンプレート生成は今後の改善候補です。
- ロギングの詳細設定（フォーマット/保持期間 等）は utils/logging_setup.py で一元管理しているため、必要に応じて調整してください。

以上。必要であれば各機能ごとにさらに細かい変更差分（関数ごとの挙動や環境変数一覧）を追記します。どのレベルの詳細を追加しますか？
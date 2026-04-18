CHANGELOG
=========

すべての変更は "Keep a Changelog" の慣習に従って記載しています。  
各エントリは機能追加（Added）、変更（Changed）、修正（Fixed）等に分類しています。

Unreleased
----------

- なし

0.1.0 — 2026-04-18
------------------

Added
- アプリケーション初期リリース。
- 実行エントリおよび運用ユーティリティ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を "high" に設定して実行。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
    - BrokerClientFactory で実環境／モックブローカーを生成（paper_trading に対応）。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag の検知で安全に停止。
    - 実行用 PID ファイルの扱い（data/execution.pid）。
    - RiskManager にデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を設定。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視テーブルの初期化を行う）。
    - stop フラグ（data/stop_requested.flag）でループを終了可能。
- 設定管理・セットアップ・検証
  - config.py: 環境変数・設定管理モジュールを追加。
    - .env の自動ロード（プロジェクトルートを .git / pyproject.toml から検出）。
    - 複数の設定プロパティを提供（J-Quants, kabuAPI, LINE, DuckDB/SQLite パス, PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の検証ロジック（instant/partial/never/reject）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）や KILL_FLAG_CLEAR_ON_START 等をサポート。
    - Settings クラスとデフォルト settings インスタンスを提供。
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 必須項目/任意項目・デフォルト値・シークレット扱いに対応。
    - .env を生成／更新するための入出力ロジックとマスク表示。
    - 保存前の確認プロンプトと注意メッセージ（.env を Git にコミットしない旨）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ有無チェック。
    - config/*.yaml の存在確認・YAML パース検証（PyYAML がなければスキップして警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Switch 設定の警告）。
    - --strict オプションで警告を FAIL 扱いに可能。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: シグナルのスコア降順ソートと上位 N 抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用ロジック（既存保有を考慮し、上限を超えるセクターの候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積り、残差を考慮した追加配分ロジックを実装。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決、既存ハンドラのクリーンアップ、ファイル作成失敗時の graceful fallback。
  - utils/process_priority.py
    - set_process_priority(level): Windows/Linux/Mac を抽象化してプロセス優先度を設定（psutil ベース）。失敗時は警告でスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定するユーティリティ。
- Tools
  - tools/paper_verification_report.py
    - ペーパートレーディング用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を集計。
    - 基準値（稼働率、成功率、送信率、P95 レイテンシ）に対する PASS/FAIL 判定を出力。
    - CLI 引数 --from/--to/--db をサポート。デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
- データ分析基盤（下流で DuckDB を利用）
  - research/factor_research.py（ファクター計算モジュールの基礎を追加。duckdb 接続を受け取りモメンタム等を計算する設計。実装は続く形で整理）

Changed
- 初回リリースのため該当なし。

Fixed
- .env パーサーの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、クォート無のコメント判定など多数の .env 書式に対応。
- ログ出力周りの堅牢化
  - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続する設計にして、起動失敗を回避。
- ポジションサイズ算出の安全弁
  - 価格欠損（0.0）の場合のスキップや aggregate スケールダウン後の再配分ロジックで不正な発注を抑制。

Security
- 機密情報（トークン／パスワード）は .env にて管理し、config_setup の出力ではシークレットをマスクして表示。README や .env 取り扱い注意を促すメッセージを生成。

Notes / Upgrade guide
- 初回リリースのため直接の互換性問題はありません。既存環境から導入する際は以下を確認してください:
  - 必須環境変数 JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD を設定してください（validate_config で事前チェック可能）。
  - PAPER_TRADING 環境を使う場合、PAPER_TRADING_SQLITE_PATH を設定すると本番監視 DB と分離できます。
  - .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - ログはデフォルトで logs/ に出力されます。権限等で作成に失敗する場合はコンソールログのみになります（警告が出ます）。
  - 実運用（KABUSYS_ENV=live）では validate_config の --strict モードで設定を厳格に確認してください。Kill Switch 等の設定（KILL_FLAG_CLEAR_ON_START）に注意してください。

Acknowledgements
- このリリースはシステム設計（監視・実行・ポートフォリオ構築・検証ツール・ユーティリティ群）を最小限の責務に分割して提供します。各モジュールは今後の拡張（戦略ロジック、ブローカ適応、追加メトリクス等）を見越して設計されています。
# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・リサーチ基盤（KabuSys）の一部実装を含みます。  
README は簡易ガイドとして、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめています。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動・ツール）
- 環境変数一覧（重要）
- 停止・Kill スイッチ
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買／リサーチ基盤を想定したモジュール群です。
- 主な要素:
  - ExecutionEngine（発注・リスク管理・オーダー管理）
  - Monitoring（システム・注文・リスク監視、KillSwitch）
  - Portfolio construction / position sizing（銘柄選定・配分）
  - Research（ファクター計算・特徴量解析）
  - AI モジュール（ニュース NLP によるセンチメント評価・市場レジーム判定）
  - ユーティリティ（設定ウィザード・検証スクリプト・ログ設定 等）
- SQLite / DuckDB をローカル DB として使用（監視ログは SQLite、分析は DuckDB）。

---

主な機能（抜粋）
- 設定管理
  - .env/.env.local の自動ロード（プロジェクトルートは .git / pyproject.toml を基準）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）
- 実行 / 監視
  - run_execution: ExecutionEngine を起動（paper_trading 環境は MockBroker を使用）
  - run_monitoring: SystemMonitor を定期ポーリングして監視ログ記録
  - MonitoringEngine: System/Trade/Risk モニタをまとめてポーリングしアラート・KillSwitch 判定
- 監視永続化層
  - monitoring_db: SQLite にテーブルを初期化 / 読書きするユーティリティ
- ポートフォリオ構築
  - 銘柄選定、等金額/スコア加重の重み計算、ポジションサイズ算出、セクター上限適用等
- 研究モジュール
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Information Coefficient）や統計サマリー
- AI（OpenAI）
  - ニュース NLP による銘柄別センチメント（ai.news_nlp.score_news）
  - マクロニュース + ETF MA による市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI 呼び出しはリトライ・バリデーション・フェイルセーフ実装済み
- ツール
  - paper_verification_report: ペーパートレード DB を解析してレポート生成

---

セットアップ手順（開発環境向け）
1. Python 環境
   - Python 3.9+ を推奨
2. 必要パッケージ（例）
   - duckdb, psutil, openai, PyYAML（任意: config 検証時）
   - pip install -r requirements.txt があればそれを使用（本リポジトリには同梱されていない可能性あり）
3. プロジェクトルート
   - リポジトリをクローンすると、プロジェクトルートは .git または pyproject.toml を基準に自動検出されます
4. .env を用意
   - 対話式ウィザードで生成: python -m kabusys.config_setup
   - もしくは手動で .env を作成（次節「環境変数一覧」を参照）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）
6. データディレクトリ作成
   - デフォルトで logs/、data/ が使用されます。自動作成されますがパーミッション等に注意してください。

---

使い方（主要なエントリポイント）
- 設定ウィザード
  - python -m kabusys.config_setup
    - .env を対話式に生成 / 更新します
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
    - KABUSYS_ENV が paper_trading の場合、MockBroker を使用し paper_trading DB に記録します
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルを生成
    - 停止はデータディレクトリに stop_requested.flag を置くか kill.flag により停止トリガーされます
- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
    - SystemMonitor をポーリングし監視ログを SQLite（本番 sqlite_path）に保存
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - PAPER_TRADING_SQLITE_PATH または --db で DB を指定可能

ログ
- 共通ログ設定は kabusys.utils.logging_setup.setup_logging を経由して行われます
- デフォルトログディレクトリ: logs/
- ローテーション: 日次（30日保持）
- コンソールには stdout へ出力されます

---

環境変数一覧（主要なもの）
- 必須（validate_config でチェック）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行関連
  - KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/… デフォルト: INFO）
  - LOG_DIR — ログ保存ディレクトリ（省略時 logs/）
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- Execution / Monitoring
  - PID_FILE_PATH — Execution の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill スイッチの flag ファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" でクリア、デフォルト "0"）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- Paper Trading 動作モード
  - PAPER_FILL_MODE — MockBroker の fill モード（instant / partial / never / reject、デフォルト: instant）
- OpenAI
  - OPENAI_API_KEY — AI モジュール利用時に必要（news_nlp, regime_detector）
- LINE（アラート任意）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- その他
  - KABU_API_BASE_URL — kabuステーション のエンドポイント（デフォルト http://localhost:18080/kabusapi）

.env の自動ロード
- プロジェクト起動時、以下順で自動読み込みされます（OS 環境変数が優先）
  1. OS 環境変数
  2. .env.local（存在する場合、.env より優先して上書き）
  3. .env
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します
- プロジェクトルートが特定できない場合は自動ロードをスキップします

---

停止・Kill スイッチ関連
- stop_requested.flag
  - run_execution / run_monitoring のループは data/stop_requested.flag を監視しています。ファイルが存在すると安全にシャットダウンします。
  - path: data/stop_requested.flag（プロジェクトルート直下の data/）
- kill.flag（KillSwitch）
  - Monitoring の評価で致命的リスクが検出された場合、KillSwitch が data/kill.flag を書き込みます。ExecutionEngine はこのフラグを検出して停止できます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に kill.flag を自動クリアします（運用では 0 推奨）。
- PID ファイル
  - 実行中の ExecutionEngine は PID ファイル（data/execution.pid）を作成します。

---

注意事項 / 運用上のポイント
- Monitoring（run_monitoring）は Monitoring 用 SQLite に対して「常に本番 sqlite_path」を使う実装になっているため、環境に依らず同じ監視 DB を使用する点に注意してください（設計により意図的）。
- Execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- AI モジュールは OpenAI API を使用します。API キーが未設定の場合はエラー（score_* 関数は明示的に検出）となります。AI コールはリトライ・フェイルセーフ設計です。
- PyYAML がない場合、validate_config の YAML ファイル検証はスキップされます（警告が出ます）。
- 一部のユーティリティは psutil を使用しプロセス優先度 / CPU affinity を操作します。権限の制限により設定に失敗することがあります（ワーニングで継続）。

---

ディレクトリ構成（主要ファイルのみ）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・CRUD
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py
  - execution/  (発注エンジン・オーダー管理などの実装が格納されます)
  - portfolio/
    - portfolio_builder.py, risk_adjustment.py, position_sizing.py
  - research/
    - factor_research.py, feature_exploration.py
  - ai/
    - news_nlp.py — ニュース NLP スコアリング
    - regime_detector.py — 市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

（上記は本リポジトリに含まれるモジュールの概観です。細かい実装・追加ファイルはソースツリーを参照してください。）

---

よくあるコマンド例
- 初期 .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または db を直接指定: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

停止（手動）
- 停止フラグを立てる:
  - touch data/stop_requested.flag
- Kill スイッチを確認 / クリア:
  - 存在確認: ls data/kill.flag
  - クリア: rm data/kill.flag もしくは KILL_FLAG_CLEAR_ON_START=1 を利用して起動時クリア（運用注意）

---

貢献 / 拡張メモ
- config/*.yaml の雛形は scripts/generate_config.py 等で生成する想定（validate_config が存在を確認します）
- AI モジュールの OpenAI SDK 呼び出し部分は単体テストしやすいよう切り出し・差し替え可能な実装（テスト時は _call_openai_api をモック推奨）
- DB スキーマは monitoring_db.init_monitoring_db でマイグレーション処理（カラム追加）を簡易的に行います

---

以上がこのコードベースの概要と利用方法の要点です。  
追加で README に載せたい具体的な利用シナリオ（例: Docker 化、systemd ユニット例、CI 設定など）があれば教えてください。必要に応じて追記・テンプレート化します。
README.md

概要
---
KabuSys は日本株の自動売買・研究基盤のためのパッケージ群です。本リポジトリには以下の主要コンポーネントを含みます:
- ExecutionEngine（発注実行）およびそれに付随する注文管理・リスク管理
- Monitoring（システム監視・アラート・Kill Switch）
- Portfolio 構築（銘柄選定、重み付け、ポジションサイズ計算）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュースセンチメント、レジーム判定）
- 各種ユーティリティ（環境設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- 運用向けツール（Paper Trading の検証レポート生成 等）

設計方針のポイント
- 環境（KABUSYS_ENV）により動作モードを切替（development / paper_trading / live）
- Paper Trading は本番 DB と分離（data/paper_trading.db）
- .env をプロジェクトルートから自動ロード（必要に応じ自動ロードを無効化可）
- DuckDB を分析用、SQLite を監視・ログ用に利用
- OpenAI を利用した NLP を内包（外部 API のリトライ・バリデーション実装あり）

機能一覧
---
主な機能（抜粋）:
- 発注実行用エンジン（run_execution.py）
  - 実ブローカー or MockBroker（KABUSYS_ENV=paper_trading）
  - リスク管理、OrderManager、Reconciler
- 監視ループ（run_monitoring.py）
  - システム稼働状況、データ鮮度、注文状態、リスク監視
  - Kill Switch（条件成立時に data/kill.flag を作成）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等配分/スコア配分、ポジションサイズ算出、セクター制限、レジーム乗数
- 研究モジュール（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算、将来リターン、IC 計算
- AI モジュール（kabusys.ai）
  - ニュースを LLM（OpenAI）でセンチメント評価 → ai_scores に格納
  - マクロニュースと MA を合成して market_regime を算出
- 運用ツール
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

動作要件
---
- Python 3.10+
- 主要依存ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証でオプション）
- （プロジェクトに requirements.txt がある場合はそれを利用してください）

セットアップ手順
---
1. リポジトリをクローン
   - git clone <repo>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install duckdb psutil openai PyYAML
     （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数の設定（.env）
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - 生成される .env はプロジェクトルートに保存されます。
   - 自動読み込み:
     - kabusys.config では .env（→ .env.local）を自動で読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
5. 設定チェック（起動前推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

重要な環境変数（代表）
---
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行モード:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB; デフォルト: data/paper_trading.db）
- ログ:
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- 他運用設定:
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）
  - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）。run_monitoring の環境変数）

サンプル .env（抜粋）
---
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

使い方
---
起動スクリプト
- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 挙動:
    - paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 停止は data/stop_requested.flag の作成で行えます（監視コンポーネントや手動でフラグを書き込む）
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - Monitoring 側は環境にかかわらず本番 sqlite_path を使用して監視ログを記録します

運用コマンド
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH を指定して DB を変更可能

停止・Kill Switch
- 実行ループを外部から停止するためのフラグ:
  - data/stop_requested.flag — run_execution/run_monitoring はこのファイルの存在を監視し、検知すると安全に終了します
  - data/kill.flag — KillSwitch（監視モジュール）が条件を満たすと書き込むことで ExecutionEngine 停止を促す（Execution 側は起動時に KILL_FLAG_CLEAR_ON_START を見て自動クリア可）

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（TimedRotatingFileHandler、バックアップ 30 日）
- コンソール出力は stdout に出力されます

開発・デバッグ
- logging 設定:
  - kabusys.utils.logging_setup.setup_logging(app_name="execution") を各起動スクリプトが呼び出します
- process 優先度:
  - kabusys.utils.process_priority.set_process_priority("high") を使用してプロセス優先度を設定します（Windows/Linux の差分を吸収）
- DuckDB/SQLite: research や AI モジュールは DuckDB 接続を受け取り SQL + Python で計算する設計

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py — パッケージ初期化、バージョン
- config.py — Settings クラス（環境変数読み込み、自動 .env ロード、必須チェック）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 環境/構成検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

kabusys/utils/
- logging_setup.py — 統一的なログ設定ユーティリティ
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

kabusys/monitoring/
- monitoring_db.py — SQLite を使った監視ログ永続化層（テーブル作成・CRUD ユーティリティ）
- system_monitor.py — システム状態・データ鮮度監視
- trade_monitor.py — （注文関連監視 — 本ツリーで参照あり）
- risk_monitor.py — ドローダウン / ポジション上限監視
- kill_switch.py — Kill Switch の評価 / フラグ書き込み
- monitoring_engine.py — 各 Monitor の呼び出しとアラート送信連携

kabusys/execution/
- execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等
  （発注実行周りの実装。BrokerClientFactory により実ブローカー / MockBroker を選択）

kabusys/portfolio/
- portfolio_builder.py — 候補選定、重み付け
- position_sizing.py — 株数計算、上限・aggregate cap のスケール処理
- risk_adjustment.py — セクター制限、レジーム乗数

kabusys/research/
- factor_research.py — Momentum / Volatility / Value 計算
- feature_exploration.py — 将来リターン / IC / 統計サマリー

kabusys/ai/
- news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に格納
- regime_detector.py — ETF MA とマクロニュースを合成して market_regime を算出

kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

data/
- monitoring.db（デフォルトの SQLite 監視 DB）
- paper_trading.db（paper_trading 用の SQLite、KABUSYS_ENV=paper_trading時に使用）
- kabusys.duckdb（デフォルトの DuckDB）
- execution.pid, stop_requested.flag, kill.flag 等の運用フラグ・PID ファイル

注意事項 / 運用上のヒント
---
- 本番（KABUSYS_ENV=live）では LINE 通知や Kill Switch の設定を必ず確認してください（validate_config が警告を出します）。
- .env は機密情報を含むため Git にコミットしないでください。
- OpenAI API を使用する機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライロジックとレスポンスの厳密なバリデーションを実装していますが、コストとレイテンシを考慮して運用してください。
- Paper Trading モードは本番 DB と完全に分離されます。テスト時は PAPER_TRADING_SQLITE_PATH の切り替えやレポート生成ツールを利用してください。

貢献
---
バグ報告・機能要望は issue を作成してください。変更を加える場合は main ブランチの方針と既存の設計（.env 自動ロード、DB 分離、フェイルセーフ設計）に沿ってください。

以上。README に書かれていない細かい使用方法や内部 API の仕様は各モジュールの docstring を参照してください。
KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームの一部コードベースです。  
主な機能は次のとおりです。

- ExecutionEngine（発注エンジン）と Monitoring（監視）による運用基盤
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- リスク調整（セクター上限、レジーム乗数）
- Research（ファクター計算、特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- 開発用ツール（ペーパートレード結果の検証レポート生成）

機能一覧
--------
- 実行/監視ランナー
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番 / ペーパートレード切替）
  - run_monitoring.py: SystemMonitor をポーリングして監視データを収集
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
  - Settings クラス: 環境変数読み取り・バリデーション（KABUSYS_ENV, LOG_LEVEL 等）
- 監視 (monitoring)
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db
  - kill.flag と stop_requested.flag による外部停止制御
- 発注・リスク管理（execution） — ブローカー抽象化（MockBroker を含む）
- ポートフォリオ（portfolio）
  - 候補選定・重み計算（equal / score / risk_based）
  - セクター制約・レジーム乗数適用
  - 株数決定（単元株丸め、aggregate cap スケーリング）
- 研究（research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC 計算、統計サマリー
- AI（ai）
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメントスコア化
  - regime_detector: マクロニュース + ETF MA で市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

セットアップ手順
----------------
1. Python 環境
   - 推奨: 仮想環境を作成して有効化（venv / pyenv 等）
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要ライブラリ（最低限）
   - duckdb
   - psutil
   - openai
   - （オプション）PyYAML（config の YAML 検証に使用）
   例:
     pip install duckdb psutil openai PyYAML

   ※ プロジェクトに requirements.txt が無い場合は上のものを個別にインストールしてください。

3. 環境変数設定
   - プロジェクトルートに .env を作成（.env は絶対に Git にコミットしないこと）
   - 対話式ウィザードを使う:
       python -m kabusys.config_setup
   - 必須（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（代表例）
     - KABUSYS_ENV: development | paper_trading | live
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading の専用 DB）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
   - 自動 .env ロード:
     - 起動時にプロジェクトルートの .env/.env.local を自動読み込みします（OS 環境変数優先）
     - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 設定検証
   - 作成後に検証:
       python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

5. ディレクトリ / DB の準備
   - デフォルトの data/ や logs/ は起動時に作成されますが、必要に応じて手動で作成しておくと権限問題を避けられます。

使い方（代表的コマンド）
-----------------------
- 設定ウィザード
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- 監視ループを起動（フォアグラウンド）
    python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視は monitoring DB（SQLITE_PATH）にデータを書き込みます。monitoring は環境にかかわらず sqlite_path を使用します。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループは安全終了します。

- 実行エンジンを起動（フォアグラウンド）
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。（本番 DB と分離）
  - 起動時に data/execution.pid に PID を書き込みます。停止時は stop flag を作ればエンジンに停止命令が送られます。

- ペーパートレード検証レポート
    python -m kabusys.tools.paper_verification_report
  - オプション:
      --from YYYY-MM-DD --to YYYY-MM-DD
      --db PATH （PAPER_TRADING_SQLITE_PATH の代替）

- AI モジュール（プログラムから呼ぶ）
  - 例: ニューススコアリング
      from kabusys.ai.news_nlp import score_news
      import duckdb, datetime
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, datetime.date(2026, 4, 1), api_key="sk-...")

  - regime_detector も同様に duckdb 接続を渡して使用します。

- ログ
  - setup_logging を全スクリプト（run_monitoring / run_execution 等）が使用します。
  - デフォルト出力先: コンソール + logs/<app_name>.log（日次ローテーション、30日保持）
  - 環境変数 LOG_DIR / LOG_LEVEL で制御可能

運用上の注意
------------
- Kill Switch / Stop Flags
  - KillSwitch（data/kill.flag）は監視が検出した重大リスク（例: ドローダウン超過）で ExecutionEngine を停止するために書き込まれます。
  - 外部運用からは stop_requested.flag（data/stop_requested.flag）を作成することで run_* スクリプトに安全停止を促せます。
- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。権限不足などで設定できない場合は警告をログに出します。
- Paper Trading
  - paper_trading モードでは実際の発注は行わず、専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
  - PAPER_FILL_MODE によりモック約定の挙動を制御できます（instant, partial, never, reject）。
- OpenAI API
  - AI モジュールを使う際には OPENAI_API_KEY を設定してください。API 呼び出しは再試行とバックオフの実装がありますが、キー・料金に注意してください。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py                 — パッケージ定義
- config.py                   — Settings クラス・環境変数読み込みロジック（.env 自動ロード）
- config_setup.py             — .env 対話式ウィザード
- validate_config.py          — 設定検証 CLI
- run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py            — ExecutionEngine 起動スクリプト

subpackages:
- ai/
  - news_nlp.py               — ニュースを LLM でスコアリング
  - regime_detector.py        — 市場レジーム判定
- monitoring/
  - monitoring_db.py          — SQLite 永続化層（監視用）
  - system_monitor.py         — システム状態 / データ鮮度監視
  - risk_monitor.py           — ドローダウン・ポジション上限監視
  - trade_monitor.py          — (発注ログ監視等)
  - monitoring_engine.py      — 各 Monitor を束ねる
  - kill_switch.py            — kill.flag 書き込みロジック
  - alert_manager.py          — （アラート送信インターフェース、実装参照）
- portfolio/
  - portfolio_builder.py      — 候補選定・重み計算
  - position_sizing.py        — 株数決定ロジック
  - risk_adjustment.py        — セクター上限・レジーム乗数
- research/
  - factor_research.py        — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py    — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py          — ログ初期化ユーティリティ
  - process_priority.py       — プロセス優先度 / CPU affinity 設定
- monitoring/monitoring_db.py — DB スキーマ初期化と永続化 API（再掲）

補足（実装上の重要ポイント）
----------------------------
- 設定の優先順位: OS 環境変数 > .env.local > .env（自動ロード）。自動ロードは無効化可能。
- DB:
  - DuckDB は分析用（prices_daily, raw_financials 等を想定）
  - SQLite は監視・発注ログ用（monitoring.db、paper_trading.db）
- 冪等性:
  - monitoring_db.init_monitoring_db は既存 DB に対して安全に実行できるよう設計されています（マイグレーション処理含む）。
- テストを書きやすい設計:
  - API 呼び出し（OpenAI 等）は内部でラップしており、テスト時にパッチで差し替え可能です。

ライセンス・貢献
----------------
- この README にはライセンス情報は含まれていません。実際の配布リポジトリでは LICENSE を確認してください。  
- 貢献する場合は issue / PR を通じて設計方針（特に本番売買に関わる部分）を慎重に扱ってください。

以上がこのコードベースの概要と使い方の要点です。特定の機能（例: ExecutionEngine の設定、TradeMonitor の詳細、AlertManager の実装）についてさらに README を拡張したい場合は、対象ファイルを指定していただければ追記します。
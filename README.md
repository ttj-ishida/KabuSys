KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための小規模フレームワークです。  
主要機能は次の通りです。

- 注文実行エンジン（ExecutionEngine）とそれを補助する OrderManager / RiskManager / Reconciler
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- ポートフォリオ構築（候補選定、重み計算、サイズ決定、セクター制限、レジーム調整）
- 研究用モジュール（ファクター計算、将来リターン・IC、統計サマリ）
- AI 支援機能（ニュース NLP によるセンチメントスコアリング、レジーム判定）
- 運用補助ツール（.env ウィザード、設定検証、Paper Trading レポート生成）
- 永続化: DuckDB（分析用）と SQLite（監視・ペーパートレード用）

主な特徴
---------
- 環境分離: KABUSYS_ENV により development / paper_trading / live を切替。ペーパートレード時は専用 SQLite を使用して本番 DB と分離。
- フェイルセーフ: AI 呼び出し失敗時はスコアをゼロにフォールバック、監視で重大事象時は kill.flag を書き込み Execution を停止可能。
- ロギング: 統一的なログ設定（stdout + 日次ローテートファイル）。
- 純粋関数ベースのポートフォリオ/リサーチモジュール（DB 参照を最小化）。
- テスト・デプロイを想定した環境自動ロード・検証ツール付き。

必須/推奨パッケージ
-------------------
（プロジェクトでは外部ライブラリを利用しています。以下をインストールしてください）

- Python 標準ライブラリ: sqlite3, threading, logging, etc.
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証を行う場合に必要）

例:
pip install duckdb psutil openai PyYAML

環境変数（主要項目）
-------------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 動作モード
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB, デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
- ログ・動作制御
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアする場合は "1"）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）
- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector で必要（関数呼び出し時に引数で指定することも可能）
- PAPER_FILL_MODE（paper_trading の MockBroker の約定挙動: instant | partial | never | reject）

注意: .env は機密情報を含むため Git にコミットしないでください。

セットアップ手順
----------------
1. リポジトリをクローンして Python 環境を作成:
   - python 3.9+（コードの型ヒントより互換のある最新 stable を推奨）
   - 仮想環境作成: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージをインストール:
   - pip install duckdb psutil openai PyYAML

3. 初期設定 (.env) を作成:
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - または .env.example を参考に .env を用意し、必須変数を設定

4. 設定検証（起動前チェック）:
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     python -m kabusys.validate_config --strict

5. ディレクトリとファイル:
   - data/、logs/ は自動作成される場合がありますが、必要に応じて作成してください。

使い方（起動・主要コマンド）
----------------------------
- ExecutionEngine を起動（通常運用 / ペーパートレードは KABUSYS_ENV に応じて動作）:
  python -m kabusys.run_execution

  特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動を中止します。
  - 実行中に data/stop_requested.flag が作られるとエンジン停止処理が走ります。
  - PID ファイルは data/execution.pid（デフォルト）に書き込まれます。

- Monitoring を起動（監視ループ）:
  python -m kabusys.run_monitoring

  特記事項:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - Monitoring は環境にかかわらず Settings.sqlite_path（本番 sqlite_path）を使用して監視データを永続化します。
  - 停止フラグ: data/stop_requested.flag を検知してループを終了します。

- .env 設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成（ツール）:
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

  例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- プログラム API（ライブラリとしての利用）
  - AI ニューススコアリング:
    from kabusys.ai import score_news
    score_news(conn, target_date, api_key=None)  # api_key を与えるか OPENAI_API_KEY を環境変数に設定

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=None)

  - ポートフォリオ / リスク / サイズ計算は kabusys.portfolio パッケージ内の関数を直接利用できます。

監視・フラグファイル
-------------------
- 停止フラグ: data/stop_requested.flag — run_execution / run_monitoring がこのファイルを検出すると順次終了処理を行います。
- Kill Switch: data/kill.flag — KillSwitch が書き込みを行い、ExecutionEngine に停止命令を与えます（起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では推奨されません）。
- PID ファイル: data/execution.pid（起動中の ExecutionEngine が PID を記録します）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール構成（抜粋）です。詳細はソースを参照してください。

- kabusys/
  - __init__.py (パッケージ定義)
  - config.py (Settings クラス、自動 .env ロード)
  - config_setup.py (.env 対話ウィザード)
  - validate_config.py (起動前検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - utils/
    - logging_setup.py (ログ設定ユーティリティ)
    - process_priority.py (プロセス優先度 / CPU affinity)
  - execution/  (ExecutionEngine, OrderManager, BrokerFactory 等) — 実装ファイルは別ディレクトリにあります
  - monitoring/
    - monitoring_db.py (SQLite persistence layer)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送信ロジック、存在する場合)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py (OpenAI を用いたニューススコアリング)
    - regime_detector.py (マクロ + ETF MA でレジーム判定)
  - tools/
    - paper_verification_report.py

設計に関する補足
----------------
- データ鮮度や稼働監視は Monitoring サブシステムで自動記録・アラートされます。監視は sqlite を用いて永続化され、duckdb は分析用に用いられます。
- AI モジュールは外部 API（OpenAI）に依存するため、API キー管理と呼び出しのリトライ・バリデーションを内包しています。API 呼び出しで JSON を受け取る設計（厳格な検証）になっています。
- ポートフォリオ関連関数は副作用がなく純粋関数で実装されているため、ユニットテストの容易性や再利用性が高くなっています。

よくある運用上の注意
-------------------
- .env に機密情報（API キー・パスワード）が入るため、必ず .gitignore に追加してバージョン管理に含めないでください。
- KABUSYS_ENV=live の場合は特に設定（LINE 通知、kill flag の自動クリアなど）を慎重に確認してください。validate_config の live 用ガードを参照してください。
- run_monitoring は Monitoring 用の sqlite_path を本番 DB として使用します（KABUSYS_ENV に依存しません）。ペーパートレード実行中に monitoring が本番 DB を上書きしないよう注意してください（設定確認を推奨）。

ライセンス・貢献
----------------
- ライセンス表記やコントリビューションガイドはリポジトリのルートに置いてください（この README では割愛）。

サポート / 連絡
----------------
不具合の報告や質問はリポジトリの Issue を利用してください。開発者向けの追加ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクト内にあれば合わせて参照してください。

以上が簡潔な README です。必要なら起動例、.env テンプレート、依存関係の requirements.txt 例などを追記します。どの項目を詳細化しますか？
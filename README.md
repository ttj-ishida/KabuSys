KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・運用・モニタリングを目的とした Python パッケージ群です。  
主な機能は以下のとおりです。

- Execution: 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- Monitoring: システム状態・注文状況・リスク監視、アラート送信（LINE）、Streamlit ダッシュボード
- Portfolio construction: 候補選定、重み付け、ポジションサイズ計算、セクター制限など
- Research: ファクター計算（Momentum / Volatility / Value）や IC 計算、特徴量探索
- AI: ニュースの NLP によるセンチメント評価（OpenAI）、市場レジーム判定
- Tools: Paper Trading 検証レポート生成などのユーティリティスクリプト

特徴
----
- DuckDB / SQLite をデータ層に利用（prices_daily / raw_financials 等は DuckDB、監視ログは SQLite）
- 環境変数 / .env ファイルで設定を管理（auto load: .env → .env.local。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- 本番 / paper_trading の分離（paper_trading モードはモックブローカー、専用 SQLite DB を使用）
- OpenAI を用いたニュースベースのセンチメント評価とレジーム判定（失敗時はフェイルセーフ）
- モニタリングにより自動で kill.flag を書き、ExecutionEngine 停止シグナルを発行可能
- Streamlit による簡易ダッシュボードを提供

セットアップ手順
---------------
1. Python のセットアップ（推奨）
   - Python 3.10+ を推奨（コード内で typing/構文に近年の機能を使用）
2. 必要パッケージをインストール
   - 例（pip）:
     - pip install duckdb psutil openai requests streamlit
   - 実際の要件はプロジェクトの requirements.txt / pyproject.toml を参照してください。
3. プロジェクトルートに .env を用意（.env.example を参考）
   - 自動読み込み: プロジェクトルート（.git または pyproject.toml のある親階層）から .env/.env.local を探索して読み込みます。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
     - KABU_API_PASSWORD — 必須（kabuステーション API）
     - OPENAI_API_KEY — OpenAI を使う機能で必須（news_nlp, regime_detector）
     - KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")。デフォルト: development
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE Push 用（任意）
     - その他: LOG_LEVEL, PID_FILE_PATH, KILL_FLAG_PATH, PAPER_FILL_MODE など
4. データディレクトリ作成
   - デフォルトのパス（data/）などが必要に応じて存在することを確認してください。

使い方
------

実行系（ExecutionEngine）
- 本番 / 開発 / ペーパートレードを切り替えて実行
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH に書き込みます。
- 起動時に pid_file を書き、プロセス優先度を高く設定します（psutil を利用）。

監視系（Monitoring）
- システムモニタの開始:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite を読み取り専用で表示します。

ツール / レポート
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - レポートは稼働率、注文成功率、送信率、P95 レイテンシ等を出力し PASS/FAIL を判定します。

AI 関連（ニュース NLP / レジーム）
- ニュースセンチメント: kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（raw_news / news_symbols / ai_scores テーブル）を渡して実行
  - api_key を None にすると OPENAI_API_KEY 環境変数を参照
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - prices_daily / raw_news / market_regime を参照し result を market_regime テーブルへ書き込み

監視・リスク制御
- KillSwitch: リスク条件（ドローダウン、ポジション数超過等）を満たすと kill.flag を書き込み、ExecutionEngine に停止シグナルを与えます。
- AlertManager: LINE に対してプッシュ通知を送信（トークン未設定時はログに警告を出し送信はスキップ）。
- RiskMonitor / TradeMonitor / SystemMonitor が定期的に DB を更新・アラート送出します。

設定詳細（Settings）
- 設定は kabusys.config.Settings から取得できます（属性アクセス）。
- 自動 .env 読み込みの挙動:
  - OS 環境変数を優先しつつ、プロジェクトルートの .env を読み込み、.env.local で上書きします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます。

ディレクトリ構成
----------------
簡易ツリー（主要ファイルのみ抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - order_record.py
      - reconciler.py
      - broker_factory.py
      - broker_api.py
      - ...（発注・ブローカー関連）
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/（実データファイルはここに置くことが想定）
      - kabusys.duckdb (default)
      - monitoring.db (default)
      - paper_trading.db (paper trading 用 default)
- pyproject.toml / .git / .env (プロジェクトルートに配置)

運用上の注意
------------
- paper_trading モードは本番 DB と完全分離されるためテスト・検証に安全です（別 SQLite ファイルを利用）。
- OpenAI API 呼び出しは失敗耐性を持ちますが、API キーは適切に管理してください。失敗時はフェイルセーフで処理を続行します（多くは 0.0／スキップでフォールバック）。
- プロセス優先度・CPU affinity の設定はプラットフォーム依存です（psutil が必要）。権限不足や未サポート環境では警告を出してスキップします。
- monitoring は常に「本番の sqlite_path」を使用します（run_monitoring は KABUSYS_ENV に依存せず本番の監視 DB を参照します）。

開発者向け
----------
- 各モジュールは純粋関数／副作用を最小限に保つ設計が意識されています（例: portfolio/* は DB 参照なし）。
- テスト時は Settings の自動 .env 読み込みを無効化するか、環境変数を明示的に設定してください。
- OpenAI API 呼び出しや外部通信部はテストで差し替え可能（関数を patch する設計）。

ライセンス / 貢献
-----------------
（ここにライセンスおよび貢献に関する案内を追記してください。例: MIT, CONTRIBUTING.md へのリンク）

補足
----
README に含めてほしい追加情報（依存関係の固定、CI、テスト実行方法など）があれば教えてください。必要に応じてサンプル .env.example のテンプレートも作成します。
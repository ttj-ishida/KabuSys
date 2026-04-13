README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージです。本リポジトリは以下の主要コンポーネントを含みます。

- Execution Engine: ブローカー経由の発注・リスク管理・自動復旧（Reconciler）
- Monitoring: システム稼働監視、注文滞留・約定異常検知、リスク監視、アラート送信（LINE）
- Research / Data: DuckDB を用いたファクター計算、特徴量解析
- AI 補助機能: OpenAI API を使ったニュースセンチメント評価 / レジーム判定
- Tools: Paper Trading の検証レポートや Streamlit ダッシュボード

主な設計方針:
- 本番・paper_trading を明確に分離（SQLite DB が分かれる）
- ルックアヘッドバイアス防止（日時参照の扱いに注意）
- フェイルセーフ（外部 API 失敗時は安全側にフォールバック）

特徴一覧
--------
- Execution:
  - ブローカー抽象化（BrokerClientFactory）
  - OrderManager による状態遷移と二相永続化設計
  - 起動時の自動リコンシリエーション（Reconciler）
- Monitoring:
  - SystemMonitor: CPU/メモリ/ディスク・プロセス死活・データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常検知
  - RiskMonitor: ドローダウン・ポジション上限の監視とログ化
  - KillSwitch: フラグファイルで ExecutionEngine を安全停止
  - AlertManager: LINE Push による通知（クールダウン機能付き）
  - Streamlit ベースの監視ダッシュボード
- Research:
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・統計サマリツール
- AI:
  - ニュースを LLM（gpt-4o-mini）でセンチメント評価し ai_scores に書込
  - マクロニュースと ETF MA による市場レジーム判定
- Tools:
  - paper_verification_report: Paper Trading DB を解析して Pass/Fail レポートを生成

動作要件
--------
- Python 3.10+
- 主要ライブラリ（例）:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード用)
  - openai (AI 機能用)
- SQLite（標準ライブラリ）を使用
- ネットワーク接続（API 使用時）

セットアップ手順
----------------
1. Python と依存ライブラリをインストール
   - 例:
     - pip install duckdb psutil requests streamlit openai

   ※ requirements.txt がある場合は pip install -r requirements.txt を推奨します。

2. プロジェクトルートに .env を配置（任意）
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

3. 必須環境変数（利用機能により必要なものが変わります）
   - JQUANTS_REFRESH_TOKEN — J-Quants API を使う場合
   - KABU_API_PASSWORD — kabuステーション API を使う場合
   - OPENAI_API_KEY — AI 機能（score_news, score_regime）を使う場合
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE アラートを有効にする場合

4. デフォルトのデータベースパス（必要に応じて .env で上書き可能）
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

設定の補足
----------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading を指定すると ExecutionEngine は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と分離）。
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動を制御）
- PID / kill flag:
  - PID_FILE_PATH（デフォルト data/execution.pid）: ExecutionEngine が自身の PID を書き込むファイル
  - KILL_FLAG_PATH（デフォルト data/kill.flag）: KillSwitch が停止トリガーを書き込むファイル
- MONITOR_POLL_INTERVAL（環境変数）:
  - run_monitoring のポーリング間隔（秒）。デフォルト 60 秒。1 未満や不正な値は無視されデフォルトにフォールバック。

使い方
------
実行スクリプト
- 監視ループ（SystemMonitor を使う最小単位スクリプト）:
  - 実行: python -m kabusys.run_monitoring
  - 説明: Settings によって監視用 SQLite（settings.sqlite_path）を使用。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。
- 実行エンジン（発注プロセス）:
  - 実行: python -m kabusys.run_execution
  - 説明: 起動時にプロセス優先度を high に設定。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient を利用します。
- Streamlit ダッシュボード:
  - 実行: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: 監視データベースを読み取り専用で表示します。
- Paper Trading 検証レポート:
  - 実行: python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
  - 説明: 稼働率 / 注文成功率 / レイテンシ等を集計して PASS/FAIL を判定します。

ライブラリ API（プログラムからの呼び出し例）
- AI スコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection
    - target_date: datetime.date（スコアリング対象日）
    - api_key: OpenAI API キー（未指定時は環境変数 OPENAI_API_KEY を参照）
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

監視・アラート
- AlertManager は LINE token と user_id を与えると LINE Push に通知します。未設定の場合はログのみ。

注意事項
----------
- 型アノテーションや union 型 (|) を使用しているため Python 3.10 以上を推奨します。
- DuckDB/SQLite へ書き込む際はファイルロックやバックアップに注意してください（特に本番環境）。
- OpenAI 呼び出しはレート制限やネットワーク障害を考慮した実装になっていますが、API キーの管理は厳重に行ってください。
- デフォルトで監視は本番 sqlite_path を使用する設計です（run_monitoring は KABUSYS_ENV に関わらず本番 DB を参照します）。

ディレクトリ構成
----------------
（主要ファイル・ディレクトリを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / .env 読み込みと Settings
    - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py                   — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py            — 市場レジーム判定（OpenAI + MA）
    - monitoring/
      - __init__.py
      - monitoring_db.py              — SQLite 永続化層（monitoring DB）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他: broker_factory, execution_engine, order_repository など)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - data/ (モジュール: pipeline, stats 等は DuckDB 操作用)
    - utils/
      - process_priority.py

付録: よく使うコマンド例
---------------------
- 依存インストール（例）:
  - pip install duckdb psutil requests streamlit openai
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- 実行プロセス起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

お問い合わせ / 貢献
------------------
バグ報告・機能提案は Issue を立ててください。コントリビューションの際は各モジュールのテスト方針に沿ってユニットテストを追加してください。

--- 
以上。必要であれば README にサンプル .env 内容や具体的な起動例（systemd / Docker 構成）を追記します。どの情報を追加したいか指示してください。
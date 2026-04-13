KabuSys — 日本株自動売買システム
================================

このリポジトリは、KabuSys（日本株向け自動売買システム）の主要コンポーネント群（実行エンジン、監視、リサーチ、ポートフォリオ構築、AI ユーティリティ等）を含みます。ここではコードベースの概要、機能、セットアップ手順、主要な使い方、ディレクトリ構成を日本語でまとめます。

前提
---
- Python 3.10 以上（typing の | 演算子などを使用）
- SQLite（標準ライブラリ sqlite3 を使用）
- 外部パッケージ（後述）を pip でインストールしてください。

プロジェクト概要
---
KabuSys は以下の主要機能を持つモジュール群で構成されています。

- Execution（発注／約定管理）：OrderManager / ExecutionEngine / Reconciler などにより注文ライフサイクルを管理。KABUSYS_ENV により paper_trading（モック）と本番を切り替え可能。
- Monitoring（監視）：SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine による定期ポーリング、監視ログ保存、LINE 通知、kill.flag による停止シグナル送信。
- Research（ファクター計算・特徴量解析）：DuckDB 上の prices_daily/raw_financials を参照して各種ファクター（モメンタム・バリュー・ボラティリティ等）や統計量を算出。
- AI（ニュース NLP／レジーム判定）：OpenAI API を用いたニュースセンチメント評価（ai_scores への書込み）／市場レジーム判定。
- Portfolio（銘柄選定・配分・株数計算）：候補抽出、重み付け、セクター制限、ポジションサイズ計算（単元丸め含む）。
- Tools（運用補助）：Paper Trading の検証レポート生成スクリプト、Streamlit ダッシュボード等。
- Utilities：プロセス優先度・CPU affinity 設定や環境変数読み込み支援など。

主な機能一覧
---
- 監視（system/trade/risk）のポーリングと永続化（SQLite）
- LINE によるアラート（cooldown 管理）
- kill.flag による ExecutionEngine の安全停止シグナル（drawdown やポジション上限で発動）
- ExecutionEngine の起動時リコンシリエーション（ブローカーとローカル差分の同期）
- Paper Trading モード（本番 DB と分離された data/paper_trading.db に記録）
- DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー 等）
- OpenAI を使ったニュースセンチメントと市場レジーム判定（フェイルセーフなリトライ処理）
- Streamlit を使った監視ダッシュボード表示
- Paper Trading 向け検証レポート生成（稼働率・注文成功率・レイテンシ等）

セットアップ手順
---
1. リポジトリをクローンし、仮想環境を作成する（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールする（requirements.txt があればそれを利用してください）。
   代表的な依存パッケージの例:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

   例:
   - pip install duckdb psutil requests openai streamlit

3. 環境変数の設定:
   プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとスキップ）。
   主要な環境変数（例）:
   - KABUSYS_ENV=development | paper_trading | live
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant | partial | never | reject
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - MONITOR_POLL_INTERVAL=60  （監視ポーリング間隔 秒）
   - LOG_LEVEL=INFO
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...

   .env の記述は bash 形式（KEY=VALUE）で、コメントや export 形式もサポートします（詳細は kabusys.config 内の実装参照）。

4. データディレクトリ作成:
   - mkdir -p data

5. DB 初期化:
   - 監視用のテーブル等は、監視スクリプトや実行スクリプト起動時に自動で init_monitoring_db が呼ばれて作成されます。

使い方（主要スクリプト）
---
以下は主要な実行方法の例です。プロジェクトルートで実行してください（src を PYTHONPATH に含めるか、パッケージとしてインストールしてから実行してください）。

1. 監視ループの起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 説明:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（デフォルト 60 秒）。
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視データは共通).
     - 起動時にプロセス優先度を "high" に設定しようとします（権限により失敗して警告が出る場合あり）。

2. 実行エンジンの起動（Execution）
   - python -m kabusys.run_execution
   - 説明:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用の DB（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と分離されます。
     - 起動時にプロセス優先度を "high" に設定しようとします。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
   - 出力: 標準出力にレポートを印字（稼働率・注文成功率・レイテンシ・判定）

4. Streamlit ダッシュボード（監視）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - 監視用 SQLite DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

5. AI 関連（ニューススコアリング・レジーム判定）
   - ライブラリ API を直接呼び出す想定:
     - from kabusys.ai import score_news
     - score_news(conn, target_date, api_key=None)  # api_key を渡さない場合は OPENAI_API_KEY を参照
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=None)
   - 実行には OpenAI API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライとエラー時のフォールバックを備えています。

設定と運用のポイント
---
- KABUSYS_ENV には "development" / "paper_trading" / "live" のいずれかを設定してください。paper_trading は実注文を送らないモードで、専用 DB に記録されます。
- MONITOR_POLL_INTERVAL は監視ポーリング間隔（秒）。0 以下や非整数は無効で、デフォルト 60 秒にフォールバックします。
- PID ファイル（既定 data/execution.pid）をプロセスが書き込み、SystemMonitor はその PID を確認してプロセスの生存を判定します。古い（stale）PID ファイルは自動的に削除されリスクイベントとしてログ化されます。
- KillSwitch は RiskMonitor の結果に基づき data/kill.flag を作成します。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にクリアできます（設定に依存）。
- OpenAI の呼び出しは 429 / タイムアウト / ネットワーク断 / 5xx に対して指数バックオフでリトライしますが、API キー未設定時は例外を出します（呼び出し側で捕捉してください）。

よくあるトラブルシューティング
---
- プロセス優先度設定で AccessDenied 警告:
  - 権限が必要です。警告が出ても処理自体は継続されます。
- DuckDB / SQLite のパスが正しくない:
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI の API エラー:
  - OPENAI_API_KEY を正しく設定してください。API のレート制限やネットワーク問題はログに出力され、可能な限りリトライされます。

ディレクトリ構成（抜粋）
---
以下は主要ファイル／モジュールの構成（src/kabusys 以下）です。プロジェクトはパッケージ形式で配置されています。

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数読み込み・Settings
  - run_monitoring.py              # SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               # ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py          # プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py             # SQLite テーブル定義・永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 Execution 関連モジュール: broker_factory, execution_engine, order_repository など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py

（注）実際のファイルや追加モジュール（data/、strategy/ 等）はリポジトリ内の完全なソースを参照してください。

貢献・拡張のヒント
---
- DuckDB テーブル（prices_daily / raw_financials / raw_news 等）のスキーマが想定通りであることを確認してください。
- position_sizing の lot_size を将来的に銘柄毎に対応させる拡張が想定されています（コメント参照）。
- AI モジュールのテスト時は _call_openai_api をモックすると簡単にユニットテストできます（コード内に注記あり）。

ライセンス・注意
---
- 本リポジトリはサンプル実装です。実運用時はリスク管理・テスト・外部 API 使用料等を十分に考慮してください。
- 金融取引の自動化は法規制や利用規約に影響されます。実運用前に十分なレビューを行ってください。

以上。必要であれば README に記載するサンプル .env のテンプレや、実行シーケンス図、要求される requirements.txt の具体例なども作成します。どの情報を追加しましょうか？
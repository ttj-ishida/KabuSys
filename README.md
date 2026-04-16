KabuSys
=======

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模なプラットフォームです。本リポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築ユーティリティ、ファクター研究、AI（ニュースセンチメント／レジーム判定）などの主要コンポーネントを含んでいます。  
コードは純粋関数・明確な境界で設計され、ローカル SQLite / DuckDB をデータ永続化層に利用します。

主な特徴
--------
- ExecutionEngine / OrderManager を用いた発注フロー（実装は broker 抽象化あり）
- Paper Trading モード（本番 DB と完全に分離された data/paper_trading.db を使用）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と通知（LINE）
- Kill Switch：条件により data/kill.flag を書き込み、Execution を安全に停止
- Streamlit ベースの監視ダッシュボード
- ファクター計算・研究モジュール（DuckDB を使用した定量ファクター群）
- AI モジュール（OpenAI を用いたニュースセンチメント・レジーム判定）
- Paper Trading の検証レポート生成ツール

セットアップ
-----------
前提
- Python >= 3.10（ソース中に union 型記法（A | B）を使用）
- SQLite（標準ライブラリ）
- DuckDB（Python パッケージ）
- psutil, requests, openai, streamlit など（下記参照）

推奨手順（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトで requirements.txt があれば pip install -r requirements.txt を利用）

3. プロジェクトルートに .env を作成（自動読み込みが有効な場合）
   - 自動読み込みは Settings モジュールがプロジェクトルート（.git または pyproject.toml を基準）を検出した場合に行います。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須 / 推奨環境変数
- 必須（実行に必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- OpenAI を使う機能を利用する場合
  - OPENAI_API_KEY

- 環境切替
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、Broker は Mock を使い、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。

- データベース / パス関連（デフォルト値は括弧内）
  - SQLITE_PATH (data/monitoring.db)
  - DUCKDB_PATH (data/kabusys.duckdb)
  - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
  - PID_FILE_PATH (data/execution.pid)
  - KILL_FLAG_PATH (data/kill.flag)

- 監視・ログ
  - MONITOR_POLL_INTERVAL（秒）: run_monitoring のポーリング間隔（デフォルト 60）
  - LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL）

- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト "instant"）

その他
- LINE 通知を有効にするには LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を設定してください（AlertManager が使用）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます。

使い方（実行例）
----------------

1) 監視プロセスを起動
- モジュール実行:
  - python -m kabusys.run_monitoring
- 概要:
  - SystemMonitor を初期化し、MONITOR_POLL_INTERVAL（デフォルト 60 秒）ごとに check_once() を呼ぶループを回します。
  - start 時にプロセス優先度を "high" に設定しようとします（psutil が必要）。
  - 停止はデーモン側で data/stop_requested.flag が作成されると検出して終了します。
- 環境変数でポーリング間隔を上書き:
  - export MONITOR_POLL_INTERVAL=30

2) 実行エンジン（ExecutionEngine）を起動
- python -m kabusys.run_execution
- 特記事項:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と分離）。
  - 起動時は data/stop_requested.flag の存在をチェックし、存在すれば起動せず終了します。
  - 実行中は PID を data/execution.pid に書きます。
  - 停止は data/stop_requested.flag を作成することで行えます（Monitoring の kill_switch 等からも行われる）。

3) Streamlit ダッシュボード（監視 UI）
- 起動コマンド（プロジェクトルートから）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 監視用 SQLite を読み取り専用で開き、ダッシュボードを表示します。MonitoringEngine がデータを書き込むことで KPI を可視化できます。

4) Paper Trading 検証レポート生成
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
- 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）などを表示し PASS/FAIL を判定します。

5) AI モジュール（ニューススコア / レジーム判定）
- ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡し、OpenAI API を呼び出して ai_scores テーブルに書き込みます。API キーは引数または OPENAI_API_KEY を利用。
- レジームスコア: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

重要な運用フラグ
----------------
- data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルの存在を見て安全に停止します（外部から停止要求を出す仕組みとして利用）。
- data/kill.flag
  - KillSwitch が条件を満たすと書き込むファイル。ExecutionEngine 側で検出すれば安全に停止できます。
- data/execution.pid
  - ExecutionEngine の PID を格納。SystemMonitor はこの PID を見てプロセスが生きているかチェックする。

データベース初期化 / マイグレーション
-----------------------------------
- monitoring.monitoring_db.init_monitoring_db(conn) が監視用テーブル群を作成します。冪等であり、既存 DB に対する軽微なマイグレーション（カラム追加）も行います。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / .env の読み込み・Settings
- run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py             — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- ai/
  - news_nlp.py                 — ニュース → センチメント（OpenAI）
  - regime_detector.py          — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py            — SQLite 監視 DB 永続化層
  - system_monitor.py           — システム・データ鮮度監視
  - trade_monitor.py            — 注文滞留・約定異常監視
  - risk_monitor.py             — ドローダウン・ポジション上限監視
  - kill_switch.py              — KillSwitch（kill.flag 制御）
  - alert_manager.py            — LINE 通知ラッパー
  - monitoring_engine.py        — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py      — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py        — 候補選定・等配分/スコア配分
  - position_sizing.py          — 株数算出・単元丸め・資金配分
  - risk_adjustment.py          — セクターキャップ / レジーム乗数
- research/
  - factor_research.py          — Momentum/Value/Volatility 等のファクター計算（DuckDB）
  - feature_exploration.py      — 将来リターン / IC / 統計サマリ
- execution/
  - order_manager.py            — 発注状態機械（OrderManager）
  - reconciler.py               — 起動時リコンシリエーション
  - （その他 broker 抽象化・order_repository 等）
- data/                         — データファイル配置想定（DB, pid, flag 等）
- utils/
  - process_priority.py         — プロセス優先度・CPU affinity ユーティリティ

実運用上の注意
--------------
- 実際のライブ取引を行う場合は broker 実装（kabuステーション等）の堅牢性・例外処理・リスク管理を十分に検討してください。本コードは学習用途・プロトタイプ向けです。
- OpenAI API を利用する機能は料金発生・レスポンス遅延・エラーを扱う実装が入っていますが、API キーの取り扱い・リトライポリシーは運用要件に合わせて調整してください。
- process priority / cpu affinity の設定は psutil の権限やプラットフォーム依存で失敗する場合があります。警告ログを確認してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）検出によるため、配布後やインストール後の挙動に注意してください。

貢献・拡張アイデア
-------------------
- Broker 実装の充実（複数ブローカー対応、注文タイプや委託手数料モデルの追加）
- ストラテジー用の Signal Pipeline と scheduler の分離
- 資金管理（複数口座・複合戦略）や単元株対応の拡張
- UI の改善（ダッシュボードのチャート追加、アラート履歴の永続化）

ライセンス
----------
（この README にはライセンス情報は含まれていません。プロジェクトに対応する LICENSE ファイルを参照してください。）

以上。必要であれば README にサンプル .env.example のテンプレートや想定 requirements.txt を追加します。どの情報を追記しましょうか？
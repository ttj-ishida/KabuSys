# KabuSys

日本株自動売買システムの一部コンポーネント（モニタリング、実行エンジン、ポートフォリオ構築、リサーチ、AI ユーティリティ等）。この README はリポジトリ内の主要機能と起動・利用方法をまとめたものです。

注意: 実際のトレード実行や外部 API（kabuステーション、J-Quants、OpenAI 等）を利用するための API キーや資格情報は環境変数で管理します。実運用前に .env を準備して下さい。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買インフラで、主に以下の役割を持つモジュール群で構成されています。

- Execution: 発注・注文状態管理・リコンシリエーション（ExecutionEngine, OrderManager, Reconciler 等）
- Monitoring: システム状態・注文状況・リスク（ドローダウン・ポジション上限）監視、アラート送信、kill switch
- Portfolio: 候補選定・重み算出・ポジションサイズ計算・セクター制限などの純粋関数群
- Research: ファクター計算・将来リターン・IC 計算・統計サマリー
- AI: ニュースの NLP によるスコアリング（OpenAI）と市場レジーム判定
- Tools: Paper Trading の検証レポート生成、Streamlit ダッシュボード等
- Utils: プロセス優先度や環境設定のユーティリティ等

---

## 主な機能一覧

- システム監視（CPU/メモリ/ディスク、Execution プロセスの存否、データ鮮度チェック）
- 注文監視（滞留注文検出、約定価格の異常検出）
- リスク監視（ドローダウン、ポジション数上限）
- Kill Switch：閾値超過時にフラグファイルを書き ExecutionEngine を安全停止
- LINE を用いたアラート通知（AlertManager）
- ExecutionEngine（本番 / Paper Trading 切替対応、MockBroker 使用可）
- リコンシリエーション（再起動後の注文同期とポジション差分検出）
- ポートフォリオ構築ユーティリティ（候補選定、等重・スコア重み、ポジションサイズ計算）
- Research（momentum/value/volatility のファクター計算、IC/統計）
- AI コンポーネント（ニュースセンチメントスコア、レジーム判定）
- Paper Trading 検証レポート出力ツール
- Streamlit ベースの監視ダッシュボード

---

## 前提 / 必要環境

- Python 3.9+（コードは型注釈・新しい機能を想定）
- 外部パッケージ:
  - duckdb
  - psutil
  - requests
  - openai（AI 機能使用時）
  - streamlit（ダッシュボード使用時）
- SQLite（ローカル DB ファイルを使用）
- （任意）kabuステーションや他ブローカーのアクセス情報

requirements.txt があればそれを利用してください。無い場合は上記パッケージをインストールしてください。

例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン/取得する
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/Mac) または .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - または上記の主要パッケージを個別にインストール
4. .env を作成（.env.example を参考に必要な環境変数を設定）
   - 自動ロード: config モジュールはプロジェクトルート（.git か pyproject.toml のある階層）から .env / .env.local を自動読み込みします。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. data ディレクトリ等の作成（必要に応じて）
   - デフォルトの DB パス等は data/ 以下を参照します（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）
  - paper_trading: Execution は MockBrokerClient を使い data/paper_trading.db を使用（本番 DB と分離）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須の箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須の箇所あり）
- OPENAI_API_KEY: OpenAI API キー（AI 関連で必須）
- PAPER_FILL_MODE: paper trading の約定シミュレーションモード（instant/partial/never/reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視等で使用する SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: Execution 側の pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag パス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知に使用

※ Settings クラス（kabusys.config）で上記の多くが参照されます。必須値は未設定だと ValueError が発生します（_require を参照）。

---

## 実行方法（使い方）

いくつかの主要スクリプト・起動方法を示します。

1. Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - 特記事項:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは本番 DB 想定）
     - 実行時にプロセス優先度を "high" に設定します
     - 停止は data/stop_requested.flag の作成で検知、または Ctrl+C

2. ExecutionEngine（発注エンジン）を起動
   - python -m kabusys.run_execution
   - 特記事項:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が選択され paper_trading 用 DB に記録します（data/paper_trading.db）
     - 起動時に data/execution.pid を使って実行中プロセスの存否をチェック
     - data/stop_requested.flag があると起動を行わず終了します
     - 停止指示は data/stop_requested.flag の作成（監視側から停止されることを想定）

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定:
     - --db PATH（または環境変数 PAPER_TRADING_SQLITE_PATH）
   - 出力: 標準出力に PASS/FAIL 判定などの指標を表示

4. Streamlit 監視ダッシュボード（可視化）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードでは positions / recent orders / system status / dashboard 集計を表示

5. AI 関連（プログラムから呼び出す）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY を使用

プログラム的な利用例（Python から）:
from kabusys.monitoring import SystemMonitor
# sqlite3 / duckdb のコネクションを渡して check_once() を呼ぶなど

---

## 停止 / 強制停止の仕組み

- stop_requested.flag
  - run_monitoring.py、run_execution.py は data/stop_requested.flag の存在を監視し、見つかればループを抜けて終了します。
- kill.flag
  - KillSwitch はリスク閾値超過時に data/kill.flag を書き込みます。Execution 側はこのフラグを検出して安全停止を実施します。
- execution.pid
  - 実行エンジンは PID を data/execution.pid に書き、SystemMonitor は PID ファイルを見てプロセス存在チェックを行います。stale PID は検出されると削除され、リスクログとして記録されます。

---

## 開発者向けノート / 実装上のポイント

- config._find_project_root は __file__ を起点に .git か pyproject.toml を探してプロジェクトルートを特定します。これにより CWD に依存せず .env 自動読込が可能です。
- MonitoringDB.init_monitoring_db はテーブル作成と簡易マイグレーション（カラム追加）を行います。冪等です。
- Portfolio / PositionSizing / RiskAdjustment の関数群は純粋関数（DB非依存）でユニットテストが容易な設計になっています。
- AI モジュールは OpenAI の JSON Mode を利用する前提で実装されています。API 呼び出し部分（_call_openai_api など）はテスト時にモック化することを想定しています。
- process_priority.set_process_priority は Windows / POSIX の差分を吸収し、失敗時は警告を出してスキップします。
- DuckDB は prices_daily, raw_financials, raw_news 等の大規模分析用テーブルを扱います。Research モジュールは DuckDB 接続を受け取り SQL を実行して計算を行います。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- run_monitoring.py
- run_execution.py

src/kabusys/ai/
- news_nlp.py
- regime_detector.py
- __init__.py

src/kabusys/monitoring/
- monitoring_db.py
- monitoring_engine.py
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- alert_manager.py
- streamlit_dashboard.py
- __init__.py

src/kabusys/execution/
- order_manager.py
- reconciler.py
- (その他 execution 関連モジュール: broker_factory, execution_engine, order_repository 等)

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/tools/
- paper_verification_report.py
- __init__.py

src/kabusys/utils/
- process_priority.py
- __init__.py

（上記は主要ファイルの抜粋です。実際のファイル一覧はリポジトリを参照してください。）

---

## よくある運用上の注意

- Paper Trading と本番 DB は分離する（KABUSYS_ENV=paper_trading では paper_sqlite_path が使用されます）。
- 監視ログは常に本番の sqlite_path を参照します（監視の性質上、環境に依存しないよう設計）。
- OpenAI API の呼び出しにはレート制限・ネットワーク例外に対するリトライ処理を実装していますが、API キーの管理とコストに注意してください。
- streamlit で DB を読み込む際には読み取り専用モードで接続しています。MonitoringEngine が DB を更新中でも安全に参照できるように設計されていますが、運用中の注意は必要です。
- .env の自動ロードはデフォルトで有効ですが、CI やテストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要であれば、README に「システムアーキテクチャ図」「API 仕様」「DB スキーマの詳細」「実運用チェックリスト」などを追加できます。どの追加情報が必要か教えてください。
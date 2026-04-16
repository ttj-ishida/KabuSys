# KabuSys

日本株向け自動売買システムのコードベース（簡易 README）。  
このドキュメントはプロジェクトの概要、主な機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／監視／リサーチを目的とした Python 製のシステムです。  
主な目的は次の通りです。

- シグナルから発注を行う ExecutionEngine（本番／ペーパートレード対応）
- 実行系の監視（System / Trade / Risk）とアラート送信（LINE）
- PaperTrading の検証・レポート生成ツール
- DuckDB を用いたファクター計算・リサーチユーティリティ
- OpenAI を用いたニュース NLP によるセンチメント算出およびレジーム判定

設計上の特徴：
- 環境変数 / .env による設定管理（自動ロード機能あり）
- Paper Trading 用に本番 DB と分離された専用 SQLite（data/paper_trading.db）
- モジュールは純粋関数／副作用を分離する方針（単体テストしやすい設計）

---

## 機能一覧

- Execution（発注）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler（起動時リコンシリエーション）
  - Paper trading モード（MockBrokerClient）と本番モードの切り替え
  - リスク管理（RiskManager）

- Monitoring（監視）
  - SystemMonitor（CPU/メモリ/Disk、プロセス生存チェック、データ鮮度）
  - TradeMonitor（滞留注文、約定異常価格検出）
  - RiskMonitor（ドローダウン、ポジション上限監視）
  - KillSwitch（条件により Execution を停止するフラグファイル生成）
  - AlertManager（LINE への Push 通知）
  - MonitoringEngine（複数モニタのポーリング統合）
  - SQLite ベースの監視ログ（monitoring_db）

- AI / NLP
  - news_nlp: OpenAI（gpt-4o-mini 等）でニュースをスコアリングして ai_scores に保存
  - regime_detector: MA200 とマクロニュースを組み合わせた日次レジーム判定

- Research
  - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC、統計サマリ

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（期間指定可）
  - streamlit_dashboard: 監視ダッシュボード（read-only で monitoring.db を表示）

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   - git clone <repo-url>
   - （プロジェクトルートは .git または pyproject.toml を含むディレクトリとして自動検出されます）

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要パッケージ（手動インストール例）:
     - pip install duckdb psutil openai requests streamlit

   注意: sqlite3 は標準ライブラリに含まれます。

4. data ディレクトリを作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに `.env` として必要な環境変数を置くと自動で読み込まれます（.env.local は上書き可）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 例 (.env):
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development   # development | paper_trading | live
     - PAPER_FILL_MODE=instant  # instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...

6. 初回 DB テーブル作成
   - monitoring 用の SQL テーブルは実行スクリプトが自動で作成します（init_monitoring_db が実行されます）。
   - DuckDB 側の価格・財務データ等は別途データパイプラインで準備してください（prices_daily / raw_financials 等）。

---

## 主要な環境変数（要約）

- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し MockBrokerClient が使われます。
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能の利用に必須）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- PID_FILE_PATH、KILL_FLAG_PATH 等は Settings クラスで参照可能（デフォルトは data 以下）

自動 .env の読み込み:
- OS 環境変数 > .env.local > .env の順でロードされます。
- OS 環境変数は上書きされません（.env.local の override は可能ですが protected されます）。

---

## 使い方（実行例）

- ExecutionEngine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中に stop フラグ（data/stop_requested.flag）が作成されると安全に停止します。
    - 実行中は data/execution.pid に PID を書きます。

- Monitoring（監視）起動:
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings.env にかかわらず monitoring は本番 sqlite_path を使用してログを記録します（monitoring 用 DB の共有に注意）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
    - 実行中に data/stop_requested.flag があると監視ループを終了します。

- Streamlit ダッシュボード（read-only）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で可視化します（monitoring.db が存在しない場合は警告が出ます）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定可能:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - --db PATH または PAPER_TRADING_SQLITE_PATH 環境変数

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI の API キーが必要（OPENAI_API_KEY）。
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime などの関数 API を呼び出して使用します。
  - 外部 API 呼び出しは冗長制御（リトライ、バックオフ）を行いますが、API キー未設定時は明示的にエラーになります。

---

## 運用補助（フラグ・PID）

- 停止フラグ（プロセス側で監視）
  - data/stop_requested.flag: run_execution / run_monitoring のループを終了させるためのファイル。存在するだけで停止されます。
- Kill Switch（自動停止トリガ）
  - KillSwitch は条件を満たすと Settings.kill_flag_path（デフォルト: data/kill.flag）へ理由を記載したファイルを書き込み、ExecutionEngine 側で検出して停止します。
  - KillSwitch.clear() に相当する操作は単純にファイルを削除すれば OK（例: rm data/kill.flag）。
- PID ファイル
  - Execution 起動時に data/execution.pid にプロセス PID を書きます。SystemMonitor はこの PID を用いて Execution の生存確認を行います。

---

## よくあるトラブルと注意点

- process priority / CPU affinity の設定はプラットフォーム依存で、権限不足（root 権限が必要な場合）で失敗することがありますが、警告を出して処理を継続します。
- LINE 通知は channel token / user id が未設定だと送信をスキップします（ログのみ）。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）はデータ投入パイプラインで準備してください。Research / AI モジュールはこれらを参照します。
- Paper trading を使う際は PAPER_TRADING_SQLITE_PATH を確認し、本番 DB と混ざらないようにしてください。
- MONITOR_POLL_INTERVAL に 0 や負数を設定すると無効値扱いでデフォルトにフォールバックします。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py  — Paper Trading レポート生成
- execution/
  - broker_api.py / broker_factory.py / execution_engine.py / order_manager.py / order_repository.py / reconciler.py / risk_manager.py / ...
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- ai/
  - news_nlp.py
  - regime_detector.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - process_priority.py
- data/ (実行環境で作成される想定)
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag

---

## 開発者向けメモ

- 設定の自動読み込みは config._find_project_root() で .git または pyproject.toml を基準に行っています。パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動読み込みを制御できます。
- モジュールは外部 API 呼び出しを行う箇所を限定的に実装しており、テストしやすいように API 呼び出し部分を差し替え可能な設計です（例: news_nlp._call_openai_api はテストでモック可能）。
- MonitoringDB.init_monitoring_db は冪等であり、既存 DB に対する簡単なマイグレーション（カラム追加）にも対応します。

---

必要であれば、README に含める具体的な .env.example、systemd / supervisor 用のユニットファイル雛形、あるいは docker-compose 定義なども作成します。どの情報を追加したいか教えてください。
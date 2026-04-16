# KabuSys

KabuSys は日本株自動売買のためのライブラリ／小型フレームワーク群です。本リポジトリは戦略構築、発注エンジン、監視、バックテスト／研究補助、AI を用いたニュース解析などをモジュール化して提供します。

この README はコードベース（src/kabusys 下）の主要コンポーネント、セットアップ、実行方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

主な目的と設計方針：
- 日本株向け自動売買システムのコア機能をモジュール化（Portfolio Construction、Position Sizing、Risk 管理、Order 管理、Reconciliation 等）。
- DuckDB / SQLite を利用したデータ処理・持続化。
- 監視（Monitoring）コンポーネントにより稼働状況 / 注文異常 / リスクを検出し、LINE に通知や ExecutionEngine 停止（kill flag）を行う。
- Paper Trading 環境を完全に本番 DB から分離して検証可能。
- OpenAI（gpt-4o-mini 等）を使ったニュース NLP による銘柄センチメント評価やマクロレジーム判定を提供（API キー必須）。
- テストしやすい設計（副作用の低い純粋関数群、DB 初期化は冪等、API 呼び出しは差し替え可能）。

---

## 主な機能一覧

- portfolio/
  - 候補選定、重み計算（等配分・スコア配分）
  - セクター上限適用、レジーム乗数算出
  - 株数算出（risk_based, equal, score）
- research/
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計測、統計サマリー、ランク変換
- execution/
  - OrderManager、ExecutionEngine（起動スクリプトあり）
  - Reconciler（起動時の自動復旧）
  - Broker 抽象化（paper/live 切替）
- monitoring/
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB（SQLite スキーマと永続化 API）
  - AlertManager（LINE 通知、クールダウン機構付き）
  - KillSwitch（条件により ExecutionEngine 停止フラグを書き込み）
  - Streamlit ダッシュボード（監視用 UI）
- ai/
  - news_nlp: raw_news を LLM に投げて銘柄別センチメントを ai_scores に書き込む
  - regime_detector: マクロ＋MA200 を用いた日次レジーム判定
- tools/
  - paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. Python 環境を作成（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合の例）
   ```
   pip install duckdb psutil openai requests streamlit
   ```
   ※ 実際の依存はプロジェクトで必要なモジュールに応じて増減します。テスト用に unittest.mock を使うことが想定されています。

4. データディレクトリの作成（デフォルトの DB 保存場所用）
   ```
   mkdir -p data
   ```

5. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（既存 OS 環境変数は上書きされません。`.env.local` は上書き可）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   代表的な環境変数（例）:
   - KABUSYS_ENV=development | paper_trading | live
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...  # AI 機能利用時に必須
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - LOG_LEVEL=INFO
   - PAPER_FILL_MODE=instant | partial | never | reject
   - MONITOR_POLL_INTERVAL=60  # run_monitoring 用（秒）

6. DB スキーマ初期化（Monitoring 用）
   - 監視系 SQLite DB スキーマは init_monitoring_db() で作成されます。Monitoring 起動時に自動作成されますが、手動で実行することもできます:
     ```
     python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; init_monitoring_db(sqlite3.connect('data/monitoring.db'))"
     ```

---

## 使い方（主要スクリプト・モジュール）

- 実行（Execution）エンジン起動
  - run_execution は ExecutionEngine を起動します。paper_trading 環境では MockBrokerClient を使い data/paper_trading.db に記録します。
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 停止方法:
    - data/stop_requested.flag を作成すると安全に停止します（同様にスクリプトは起動時にこのファイルが既に存在すると起動しません）。
    - kill.flag（Settings.kill_flag_path）を KillSwitch などが書き込むと ExecutionEngine に停止シグナルが送られます。
  - 実行時のプロセス優先度は set_process_priority("high") によって上げられます（権限がない場合は警告でスキップ）。

- 監視（Monitoring）起動
  - monitoring のポーリングループを起動します（MONITOR_POLL_INTERVAL で間隔を調整）。
    ```
    python -m kabusys.run_monitoring
    ```
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は MonitoringDB（SQLite）へログを書き込みます。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（設計上の注意）。

- Streamlit ダッシュボード（監視）
  - ローカルで監視 DB を可視化するには:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- Paper Trading 検証レポート
  - Paper Trading DB（デフォルト data/paper_trading.db）を入力として検証レポートを出力します。
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB パス指定:
    ```
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を設定してから利用します。
  - 使い方は関数呼び出しベース:
    - ニューススコアリング:
      ```
      from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news

      conn = duckdb.connect('data/kabusys.duckdb')
      score_news(conn, date(2026, 4, 10), api_key='YOUR_KEY')
      ```
    - レジーム判定:
      ```
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, date(2026, 4, 10), api_key='YOUR_KEY')
      ```
  - LLM 呼び出しはリトライ / バックオフ / レスポンス検証が組み込まれています。API キーが未設定だと ValueError を投げます。

---

## 環境変数 / 設定の挙動

- .env / .env.local 自動読み込み
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` / `.env.local` を自動ロードします。
  - OS 環境変数は保護され、`.env` による上書きは行われません。`.env.local` は override=True として既存の設定を上書きします（ただし OS 環境変数は保護）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- Settings クラス（kabusys.config.Settings）
  - アプリケーションで使う設定は Settings / settings インスタンス経由で取得します（例: settings.env, settings.sqlite_path, settings.paper_sqlite_path など）。
  - 設定値が不正な場合は ValueError を投げる設計です。
  - PAPER_FILL_MODE は instant / partial / never / reject のいずれかでなければならない等のバリデーションが入っています。

---

## 停止・警告フラグの取り扱い

- stop_requested.flag
  - run_monitoring と run_execution はプロジェクトの data/stop_requested.flag の存在を監視して安全に停止します。
- kill.flag
  - KillSwitch は特定のリスク条件（ドローダウン超過、ポジション上限等）を満たした場合に `data/kill.flag` に理由を書き込み、ExecutionEngine 停止を促します。
  - ExecutionEngine は起動時に kill.flag の存在を検査し、あれば起動しません（起動時のクリーンアップ設定により削除される場合もあります）。

---

## ディレクトリ構成（抜粋）

（この README は src/kabusys 配下の主要ファイルをベースにしています）

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数／.env ロードと Settings
    - run_monitoring.py  — SystemMonitor ポーリング起動スクリプト
    - run_execution.py   — ExecutionEngine 起動スクリプト

    - ai/
      - news_nlp.py         — ニュースセンチメント（OpenAI 呼び出し）
      - regime_detector.py  — マクロ＋MA200 によるレジーム判定
      - __init__.py

    - monitoring/
      - monitoring_db.py    — SQLite スキーマ & 永続化 API（MonitoringDB）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
      - __init__.py

    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 Broker / Engine / order_repository 等のモジュール)

    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py

    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py

    - tools/
      - paper_verification_report.py
      - __init__.py

    - utils/
      - process_priority.py
      - __init__.py

- data/   （実行時に DB・PID・flag ファイル等を置く想定）
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite, paper_trading 専用)
  - kabusys.duckdb (DuckDB)
  - execution.pid
  - stop_requested.flag
  - kill.flag

---

## 補足・運用上の注意

- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading にすると run_execution は専用の paper_trading DB を使います（settings.paper_sqlite_path）。
- 監視（Monitoring）は KABUSYS_ENV にかかわらずデフォルトで本番 monitoring.db を使う設計になっています。運用時は設定に注意してください。
- OpenAI の呼び出しは外部ネットワーク依存かつコストがかかるため、API キー管理とレート管理に注意してください。AI モジュールはリトライやフェイルセーフの仕組みを持っていますが、誤設定は運用問題を引き起こす可能性があります。
- psutil によるプロセス優先度設定や CPU affinity は OS・権限に依存します。権限がない場合は警告ログ出力でスキップされます。
- DB マイグレーションは簡易的に init_monitoring_db 内でカラム追加チェックを行っています。より複雑なマイグレーションが必要な場合は別途スクリプトを用意してください。

---

必要であれば、README にサンプル .env.example、詳しい起動例（systemd / docker-compose など）や開発・テスト手順を追記できます。追加したい項目があれば教えてください。
# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群（軽量プロトタイプ）。  
このリポジトリは、シグナル → ポートフォリオ構築 → 発注 → 監視 に関わる機能を含んでいます。  
主要コンポーネントとして ExecutionEngine（発注実行）、Monitoring（監視）、Research（ファクター計算）、AI（ニュース NLP / レジーム判定）、Portfolio（銘柄選定・ポジションサイズ）などを提供します。

---

## 特徴（機能一覧）

- Execution
  - OrderManager / OrderRepository を用いた発注ワークフロー
  - ブローカーファクトリ（paper_trading では MockBrokerClient を使用）
  - Reconciler による起動時リコンシリエーション（再起動後の自動同期）
  - RiskManager（発注前チェック）を備えた ExecutionEngine（起動スクリプトあり）

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格監視
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringDB：SQLite による監視ログ永続化（テーブル自動作成・マイグレーション対応）
  - AlertManager：LINE Push による通知（クールダウン管理）
  - KillSwitch：条件に応じたフラグファイル作成で ExecutionEngine 停止を指示
  - Streamlit ダッシュボード（監視結果の可視化）

- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、統計サマリ
  - 銘柄選定（スコア順 / 等配分）、重み計算、セクター制約、ポジションサイズ計算

- AI（OpenAI）
  - ニュースを集約して LLM による銘柄別センチメントスコアを付与（ai_scores へ保存）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（market_regime へ保存）
  - API 呼び出しはリトライ / フェイルセーフ実装済み

- ユーティリティ
  - 設定管理（.env 自動ロード、必須チェック）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 用の検証レポート生成ツール

---

## セットアップ手順

1. Python (推奨: 3.10+) を用意する。

2. 依存パッケージをインストールする（例: pip）。
   必要パッケージ（抜粋）:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit

   例:
   ```
   pip install duckdb psutil openai requests streamlit
   ```

3. プロジェクトルートに .env/.env.local を置いて必要な環境変数を設定するか、OS 環境変数で設定します。  
   自動ロードはデフォルトで有効（プロジェクトルートは .git または pyproject.toml で検出）。  
   自動ロードを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. 主要な環境変数（代表例）
   - 必須（Execution の一部で必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI 関連（AI 機能を使う場合）:
     - OPENAI_API_KEY
   - 動作モード:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
       - paper_trading: MockBroker を使い DB は data/paper_trading.db に分離
   - DB / ファイルパス:
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH: ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH: Kill フラグ（デフォルト: data/kill.flag）
   - その他:
     - LOG_LEVEL (DEBUG/INFO/...)
     - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）

5. データフォルダを作成:
   ```
   mkdir -p data
   ```

---

## 使い方（主要な実行例）

- Monitoring（ポーリング監視）を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数でポーリング間隔を上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 起動時にプロセス優先度を "high" にセットします。監視は常に本番 sqlite_path を使用します（KABUSYS_ENV に依存せず）。

- ExecutionEngine（発注実行）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合:
    - MockBrokerClient を使用
    - DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離
  - Execution 起動時もプロセス優先度を "high" に設定します。

- Streamlit ダッシュボード（監視）:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 既に監視 DB が存在しない場合はエラーメッセージが表示されます（MonitoringEngine を先に起動してください）。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで DB パス指定可（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）。

- AI 機能（プログラム内利用）
  - ニュース NLP（ai_scores に書き込み）:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key が None の場合は OPENAI_API_KEY 環境変数を使用
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要な設計・挙動メモ

- 設定読み込み:
  - .env, .env.local はプロジェクトルート（.git または pyproject.toml）を基に自動ロードされます（OS 環境変数が優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化。

- DB 初期化:
  - monitoring 系の起動スクリプトは init_monitoring_db() を呼び、テーブルを冪等的に作成・マイグレーションします。

- Process / Priority:
  - run_monitoring/run_execution は起動時に set_process_priority("high") を呼びます（Windows/Linux の差を吸収）。

- Paper Trading:
  - paper_trading モードでは発注は MockBrokerClient にルーティングされ、DB は paper_trading 用に分離されます。PAPER_FILL_MODE で約定挙動を制御。

- AI API: OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証を行い、失敗時はフェイルセーフ（スコア 0 やスキップ）で継続する設計です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（KABUSYS_ENV 等）
  - run_monitoring.py
    - Monitoring のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・監視ログ操作クラス MonitoringDB
    - system_monitor.py — システム / データ鮮度チェック
    - trade_monitor.py — 注文滞留 / 約定異常検知
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - alert_manager.py — LINE Push 通知
    - kill_switch.py — kill.flag の管理
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ... （発注関連ロジック）
  - portfolio/
    - portfolio_builder.py — 銘柄選定
    - position_sizing.py — 株数計算
    - risk_adjustment.py — セクター制約・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py — ニュースの LLM スコアリング（ai_scores 書込）
    - regime_detector.py — マクロ+MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力ツール

- data/
  - デフォルトの DB / pid / flag ファイル置き場（事前に作成しておくことを推奨）
    - kabusys.duckdb (DUCKDB_PATH)
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - execution.pid (PID_FILE_PATH)
    - kill.flag (KILL_FLAG_PATH)

---

## よく使うコマンドまとめ

- 監視開始:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行（発注）開始:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README にサンプル .env.example、起動ユースケース（運用時の systemd ユニット / Docker run 例）や詳しい環境変数一覧・推奨パッケージバージョンを追記します。どの情報を優先して追加しますか？
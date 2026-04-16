# KabuSys

日本株向けの自動売買 / 研究・監視フレームワーク（抜粋）。  
このリポジトリは注文実行エンジン、監視コンポーネント、ポートフォリオ構築のユーティリティ、ファクター計算 / リサーチ、AIベースのニュースセンチメント評価などを含みます。

---

## プロジェクト概要

KabuSys は以下の機能を備えた内製自動売買基盤のコンポーネント群です（コードはモジュール化され、テストやモック差替えを想定した設計になっています）:

- ExecutionEngine（発注管理、リスク管理、ブローカ接続、再同期）
- Monitoring（システム状態監視、注文監視、リスク監視、アラート送信）
- Portfolio construction（候補選定、重み付け、株数算出、セクター制限等）
- Research（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI モジュール（ニュースセンチメント評価、レジーム判定） — OpenAI API を利用
- 運用用ユーティリティ（プロセス優先度設定、Streamlit ダッシュボード、検証レポート生成等）

設計方針の例:
- DuckDB / SQLite を使ったローカル DB（本番と paper_trading を分離可能）
- ルックアヘッドバイアス回避（日時参照の扱いに注意）
- フェイルセーフ: API 失敗時にはデフォールト値で継続する箇所が多い
- テスト容易性のため内部の API 呼び出しは差し替え可能

---

## 主な機能一覧

- 発注管理・状態同期（Reconciler、OrderManager、OrderRepository）
- リスク管理（RiskManager、RiskMonitor）
- 監視（SystemMonitor、TradeMonitor、MonitoringEngine）
- アラート通知（LINE push via AlertManager）
- Streamlit による監視ダッシュボード（read-only 接続）
- Paper Trading 用の分離 DB と MockBroker サポート
- Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）
- AI を使ったニュースセンチメント（kabusys.ai.news_nlp）とレジーム判定（kabusys.ai.regime_detector）
- ファクター計算・特徴量探索（kabusys.research）
- ポートフォリオ構築モジュール（選定・重み算出・ポジションサイズ計算）

---

## セットアップ手順

前提
- Python 3.10 以降（型注釈に `|` 演算子を使用しているため）
- SQLite は標準で利用可能
- DuckDB、psutil、requests、openai、streamlit 等が必要

例: 仮想環境を作って依存をインストールする手順（一例）

1. リポジトリを取得
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   必要な主要パッケージ（最小セット）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

   例:
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```

4. 環境変数 (.env) を用意
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動読込は無効化可能）。

   代表的な環境変数:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

5. data ディレクトリを作成
   ```bash
   mkdir -p data
   ```

注意:
- Paper Trading（KABUSYS_ENV=paper_trading）では MockBroker を使い、paper_trading 用の SQLite に記録され本番 DB と分離されます。
- 設定読み込みは .env → .env.local の順で OS の環境変数を上書きしません（詳細は `kabusys.config` を参照）。

---

## 使い方（よく使うコマンド）

- 監視ループ（SystemMonitor の単独起動）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: `export MONITOR_POLL_INTERVAL=30`）。
  - 停止は Ctrl+C、またはプロジェクトルートの data/stop_requested.flag を作成すると安全に終了します。
  - 監視は Settings.sqlite_path（デフォルト: data/monitoring.db）を常に使用します（環境に無関係に監視 DB は本番パスを参照する設計）。

- 実行エンジン（ExecutionEngine）起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の際は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録し、MockBroker を使用します（本番と完全分離）。
  - engine の PID ファイルは data/execution.pid（設定で変更可）に出力されます。
  - data/stop_requested.flag が既にある場合は起動をスキップします。停止は stop フラグ書き込みで行います。

- Paper Trading 検証レポート（コマンドラインツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。`--db` でパスを指定できます。
  - 出力は標準出力へテキストレポート（稼働率、注文成功率、レイテンシ等）。

- Streamlit 監視ダッシュボード（読み取り専用）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - DB は読み取り専用で開きます。MonitoringEngine を先に起動してデータを作成してください。

- AI 関連（ニューススコア・レジーム判定）
  - ニューススコアリング / レジーム判定は OpenAI API キーが必要です。実行はモジュールを直接呼び出す（スクリプトは同梱されていません）。
  - 例: Python スクリプトから `kabusys.ai.score_news(conn, target_date, api_key=...)` / `kabusys.ai.regime_detector.score_regime(...)` を呼ぶ。

- kill / stop フラグ
  - 実行エンジン停止のために `data/kill.flag`（KillSwitch） を生成できます。これは ExecutionEngine に停止を指示するためのフラグです（KillSwitch クラスが制御）。
  - 停止要求フラグ（run_*.py が参照するもの）: data/stop_requested.flag

---

## 主要設定項目（Settings 抜粋）

（詳細は `src/kabusys/config.py` を参照）

- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG | INFO | WARNING | ...
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各種外部 API 認証
- OPENAI_API_KEY: OpenAI（AI モジュール使用時）
- PAPER_FILL_MODE: paper_trading 時の約定振る舞い（instant | partial | never | reject）
- SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH: DB ファイルパス
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のパス
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値

Settings は環境変数に依存し、必須変数がない場合は起動時に例外を送出します（`_require`）。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールのファイル構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
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
      - (その他 broker / engine / repository 関連モジュール)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/ (運用時に使用する SQLite / DuckDB / フラグファイル等)
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用)
      - kabusys.duckdb
      - execution.pid, kill.flag, stop_requested.flag, etc.

（実際のリポジトリにはさらに execution/broker_api や data/pipeline 等のモジュールが含まれます）

---

## 運用上の注意・補足

- Paper Trading モードは本番 DB と完全分離するよう設計されています。運用時は KABUSYS_ENV を正しく設定してください。
- OpenAI API 呼び出しはレート制限や 5xx を想定したリトライ実装がありますが、API キーの管理・コストに注意してください。
- Monitoring は監視 DB（SQLite）へ常に書き込むため、ストレージの容量やパスのアクセス権に注意してください。
- プロセス優先度設定や CPU affinity の操作は psutil を使って行います。権限不足などで失敗する可能性があるため、警告ログを確認してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- Streamlit のダッシュボードは DB を read-only で開きます。MonitoringEngine 実行中に閲覧してください。

---

## 参考（よくあるコマンド例）

- 開発用起動（監視）
  ```bash
  KABUSYS_ENV=development python -m kabusys.run_monitoring
  ```

- Paper Trading 実行
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

README はコードの主要な運用・導入方法を示すための簡易ガイドです。詳しい実装や追加の設定は各モジュール（`src/kabusys/*`）の docstring とソースコードをご参照ください。必要であれば、環境変数のサンプル（.env.example）や requirements.txt の追記も対応します。
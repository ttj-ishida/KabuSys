# KabuSys

KabuSys は日本株自動売買システムのコンポーネント群を含むリポジトリです。戦略のリサーチ／ファクター計算、ポートフォリオ構築、発注エンジン、監視（Monitoring）、AI（ニュースセンチメント／レジーム判定）などをモジュール化して提供します。

以下はこのコードベースの概要、主な機能、セットアップ方法、実行例、ディレクトリ構成です。

---

## プロジェクト概要

- 目的: 日本株の自動売買・研究パイプラインを構成するライブラリ群と実行スクリプト群。
- 設計方針:
  - DuckDB / SQLite を用いたデータ格納・処理（ローカルで完結する分析ワークフロー）。
  - 実行エンジン（ExecutionEngine）と監視（Monitoring）を分離し、安全性（リコンシリエーション、キルスイッチ、リスク監視）を重視。
  - AI（OpenAI）を用いたニュースセンチメント・レジーム判定機能を組み込んでいるが、APIキー未設定時はフェイルセーフで動作可能。
  - Paper Trading 環境では本番DBと分離された専用 SQLite を使用。

---

## 主な機能一覧

- execution
  - 起動時自動復旧・リコンシリエーション（Reconciler）
  - Order 管理（OrderManager, OrderRepository）
  - Risk 管理（RiskManager: 設定は Execution 側で組み立て）
  - Broker クライアント抽象化（Mock / 実ブローカー切替）

- monitoring
  - SystemMonitor: CPU・メモリ・ディスク・プロセス状態・データ鮮度監視
  - TradeMonitor: 注文の滞留（stale）・約定異常価格検出
  - RiskMonitor: ドローダウン監視・ポジション上限監視とダッシュボード更新
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル生成
  - AlertManager: LINE Messaging API を用いた通知（クールダウン機能あり）
  - MonitoringEngine: 各 Monitor を統合してポーリング実行
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）

- research / data
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC（Information Coefficient）計算、特徴量統計
  - DuckDB を用いた SQL + Python 実装

- portfolio
  - 候補選定、等配分・スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - 株数決定（単元株丸め、リスクベース配分、aggregate cap）

- ai
  - news_nlp.score_news: raw_news を LLM（OpenAI）でセンチメント評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF MA とマクロニュースセンチメントを合成して market_regime を書き込む

- tools
  - paper_verification_report: Paper Trading 用の検証レポート生成 CLI

---

## 事前要件（概略）

- Python 3.9+（コードは型ヒントで modern Python を想定）
- 必須 / 推奨パッケージ（例）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード実行時)
  - openai (AI 機能使用時)
- SQLite（標準ライブラリで利用可）
- ネットワーク接続（LINE API / OpenAI 利用時）

プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを参照してください。無い場合の例：

```
pip install duckdb psutil requests streamlit openai
```

開発時は仮想環境（venv / conda）を推奨します。

---

## 環境変数（主なもの）

Settings クラスで参照する主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能使用時)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (AlertManager 使用時)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (monitoring 用 DB, default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- KABUSYS_ENV: development | paper_trading | live (default: development)
- PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の動作設定, default: instant)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（.env 自動ロードを無効化）

.env / .env.local はプロジェクトルートから自動読み込みされます（OS 環境変数が優先）。自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローンし、ルートに移動。

2. 仮想環境を作成・有効化（例）:

   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール:

   ```
   pip install -r requirements.txt   # もし用意されていれば
   # または最低限:
   pip install duckdb psutil requests streamlit openai
   ```

4. 環境変数を用意:
   - プロジェクトルートに .env を作成する（.env.example があれば参照）。
   - 必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定。

5. データディレクトリを作る:

   ```
   mkdir -p data
   ```

6. DuckDB / SQLite の初期テーブルは各モジュールが接続時に作成・マイグレーションを行います（例: monitoring_db.init_monitoring_db）。

---

## 実行方法（代表例）

注意: ソースは `src/` 配下にあるため、実行時に PYTHONPATH=src を渡すかパッケージをインストール（pip install -e .）してください。

- Monitoring（ポーリング監視ループ）を起動:

  ```
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```

  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。無効値は 60 にフォールバック。
    - 監視は Settings.sqlite_path (monitoring DB) を使用します（環境に関係なく本番 sqlite_path を参照）。

- ExecutionEngine（発注エンジン）を起動:

  ```
  PYTHONPATH=src python -m kabusys.run_execution
  ```

  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、data/paper_trading.db に記録されます（本番 DB と分離）。

- Streamlit ダッシュボードを起動:

  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

  - 引数 --db で読み取り専用 DB パスを指定できます（既定: data/monitoring.db）。

- Paper Trading 検証レポート:

  ```
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  - --db オプションで SQLite パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数も参照）。

- AI 機能（プログラム内部 API の使用例）:

  Python スクリプトや対話環境から DuckDB 接続を作成して利用します。

  例: ニューススコアリング（score_news）を呼ぶ

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 4, 01), api_key="YOUR_OPENAI_KEY")
  print("wrote", n_written, "scores")
  ```

  レジーム判定:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  ```

---

## よくあるトラブルと注意点

- PID ファイル / プロセス優先度:
  - run_monitoring/run_execution は起動時にプロセス優先度を上げようとします（psutil を利用）。権限がないと警告になりますが継続します。
  - PID ファイルの読み書き権限に注意してください（Settings.pid_file_path）。

- .env 自動ロード:
  - プロジェクトルートは .git または pyproject.toml を基準に探索されます。ルートが特定できない場合は自動ロードがスキップされます。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- OpenAI / LINE:
  - OpenAI API キーがないと AI 機能は動作しません（明示的に例外を投げるか、safe fallback により 0.0 を用いる箇所あり）。
  - LINE トークン / ユーザID が未設定の場合、アラートはログにのみ出ます。

- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離します。PaperTrading 用の挙動（fill mode など）は PAPER_FILL_MODE で制御できます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py — 環境変数/Settings 管理、.env ロードロジック
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI 経由）
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite テーブル初期化・永続化 API
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - kill_switch.py, alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py, reconciler.py, ... （発注・リコンシリエーション関連）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py

（上記は主要ファイルの抜粋です。詳細はソースを参照してください）

---

## 開発時のヒント

- ソース直下（src）を PYTHONPATH に含めることで `python -m kabusys.run_monitoring` などが使えます。
- DuckDB のスキーマは research / ai モジュールで参照するテーブル（prices_daily, raw_financials, raw_news 等）を前提としています。データの投入手順は別途のデータパイプライン（kabusys.data.pipeline 等）を参照してください。
- 単体テストでは .env 自動ロードを無効化したり、OpenAI 呼び出しをモックするために各モジュールの小さな差し替えポイント（関数）を用意しています。

---

必要であれば、README に使う具体的な requirements.txt の候補、サンプル .env.example、または各コンポーネント（ExecutionEngine の起動オプションや設定項目）のより詳しい使い方を追記できます。どの情報を優先して追加しますか？
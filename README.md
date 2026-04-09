# KabuSys

日本株の自動売買・研究・監視フレームワーク（ライブラリ群）。  
ポートフォリオ構築、ポジションサイジング、ファクター計算、AI を使ったニュースセンチメント、監視エンジン、発注エンジンなどの主要機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- DuckDB に保存した市場データ（prices_daily / raw_financials / raw_news 等）を使ったファクター計算・研究
- ポートフォリオ候補選定、配分計算、ポジションサイズ決定（等重/スコア重み/リスクベース）
- LLM（OpenAI）を用いたニュースセンチメント / マクロセンチメント評価
- 発注フロー（OrderManager / ExecutionEngine / Broker API プロトコル）と再起動時のリコンシリエーション
- 監視・アラート（LINE push）・ダッシュボード（Streamlit）・kill-switch による安全停止

設計方針としては「DB 参照は明示」「本番 API 呼び出しはクライアント層に閉じる」「ルックアヘッドバイアス防止」等が反映されています。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート判定）
  - 環境変数からの Settings オブジェクト（J-Quants, kabu API, LINE, DB パス 等）

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定: スコア降順で上位 N を選択
  - 重み計算: 等配分・スコア加重
  - ポジションサイジング: risk-based / equal / score、単元株丸め、aggregate cap

- リスク調整（kabusys.portfolio.risk_adjustment）
  - セクター集中上限適用
  - 市場レジームに応じた投下資金乗数

- 研究（kabusys.research）
  - momentum / volatility / value のファクター計算（DuckDB 接続を受け取る純粋関数）
  - 将来リターン計算 / IC（Spearman） / 統計サマリー

- AI（kabusys.ai）
  - ニュース NLP（OpenAI）で銘柄別センチメントを算出し ai_scores テーブルへ書き込み
  - 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）

- 監視（kabusys.monitoring）
  - MonitoringDB（SQLite）スキーマ・永続化ユーティリティ
  - System / Trade / Risk Monitor、AlertManager（LINE push）
  - KillSwitch（flag ファイルによる停止）
  - Streamlit ダッシュボード（監視データ表示）

- 発注・実行（kabusys.execution）
  - BrokerAPIProtocol（プロトコル・モデル）定義
  - OrderManager（状態遷移・永続化）、Reconciler（復旧）
  - ExecutionEngine（シグナル処理 + WebSocket drain）

---

## セットアップ手順

前提

- Python 3.10 以上（型ヒントで | を使用）
- Git が使える環境

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .\.venv\Scripts\activate
     ```

3. 必要パッケージをインストール
   本リポジトリに requirements.txt が無い場合の例:
   ```
   pip install duckdb openai requests psutil streamlit
   ```
   （テスト: pytest などを追加でインストールしてください）

4. 環境変数の用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env`（および必要なら `.env.local`）を置くと、自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（必須機能を使う場合）
   - KABU_API_PASSWORD: kabu ステーション API パスワード
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE: paper trading の模擬成行挙動（instant/partial/never/reject）

   ※ .env の書式は shell 形式（export KEY=val, コメント等）に対応しています。

---

## 使い方（主要ユースケース）

以下は代表的な使い方サンプルです。実行前に必要な DB / テーブルを準備してください。

- Settings を使う（Python）
  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)            # Path オブジェクト
  print(settings.kabu_api_base_url)      # kabu API のベース URL（デフォルト有り）
  ```

- DuckDB 接続を渡してファクター計算（研究）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 3, 20))
  ```

- OpenAI を使ってニュースにスコアを付与（news_nlp）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
  written = score_news(conn, date(2026, 3, 20), api_key="sk-xxxx")
  print(f"wrote scores for {written} stocks")
  ```

- 市場レジーム判定（regime_detector）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20), api_key="sk-xxxx")
  ```

- 監視 DB 初期化（SQLite）
  ```python
  import sqlite3
  from kabusys.monitoring import init_monitoring_db

  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  conn.close()
  ```

- Streamlit ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- MonitoringEngine を単体で1回だけ実行（テスト）
  ```python
  import sqlite3
  import duckdb
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine
  from kabusys.monitoring.monitoring_db import MonitoringDB

  monitoring_conn = sqlite3.connect("data/monitoring.db")
  duck_conn = duckdb.connect("data/kabusys.duckdb")

  sys = SystemMonitor(monitoring_conn, duck_conn)
  # TradeMonitor は OrderRepository など依存があるため、テスト時はモック実装を渡す
  trade = TradeMonitor(monitoring_conn, order_repo=mock_repo)
  risk = RiskMonitor(monitoring_conn)
  ks = KillSwitch(flag_path=settings.kill_flag_path)
  am = AlertManager(settings.line_channel_access_token, settings.line_user_id)
  engine = MonitoringEngine(sys, trade, risk, interval_sec=60, kill_switch=ks, alert_manager=am)

  engine.run_once()
  ```

- ExecutionEngine（本番フロー）
  ExecutionEngine は Broker 実装（BrokerAPIProtocol）、OrderRepository、RiskManager、OrderManager、DuckDB 接続等の実体が必要です。テストではモックを用いて `_process_signals()` や `_drain_push_queue()` を直接呼ぶことができます。実際の起動はアプリケーション固有のランチャーを用意してください。

---

## 重要な挙動・運用メモ

- .env の自動読み込み順序:
  OS 環境変数 > .env.local > .env
  既に OS にあるキーは .env により上書きされません（保護）。自動読み込みはプロジェクトルートを .git または pyproject.toml から探索して行います。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- kill.flag:
  ExecutionEngine と KillSwitch はファイルベースの停止フラグ（デフォルト: data/kill.flag）を使用します。起動時に flag があり、環境変数 `KILL_FLAG_CLEAR_ON_START=1` が設定されていない場合は起動を拒否します。

- AI 呼び出しのフェイルセーフ:
  OpenAI API 呼び出しは 429 / タイムアウト / 5xx に対して指数バックオフでリトライしますが、最終的に失敗した場合はフォールバック（macro_sentiment=0.0 等）し、例外でプロセス全体を停止しない設計です。

- DuckDB / SQLite への書き込みは冪等性を考慮（DELETE→INSERT、BEGIN/COMMIT）している箇所が多くあります。

---

## ディレクトリ構成（概要）

以下は主要ファイルと簡単な説明です。パッケージのトップは src/kabusys です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / .env 自動読み込み、Settings クラス
  - portfolio/
    - portfolio_builder.py — 候補選定、等重/スコア重み計算
    - position_sizing.py — 単元丸め・リスクベースの株数計算
    - risk_adjustment.py — セクター上限、レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value ファクター計算
    - feature_exploration.py — forward returns, IC, summary
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores に書き込む
    - regime_detector.py — マクロ + ETF MA200 によるレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ作成・MonitoringDB クラス
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検知
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 制御
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - broker_api.py — Broker API のデータモデル・例外・プロトコル定義
    - order_repository.py — （DB 層：orders）※ファイル内実装参照
    - order_record.py — 注文状態と遷移
    - order_manager.py — OrderManager（作成・送信・同期・キャンセル）
    - reconciler.py — 起動時リコンサイル
    - execution_engine.py — Signal Queue と push ドレインの実装
    - risk_manager.py — 実行時の Gate 検査（利用可能性のある実装）
  - monitoring/（上記）
  - data/（外部：DuckDB / SQLite の配置先のデフォルトを参照）
  - その他モジュール（research, portfolio, ai 等は上記参照）

---

## 開発・テストのヒント

- unit テストでは OpenAI 呼び出し・ブローカー呼び出しを patch/mocking して API 実行を回避して実行してください。news_nlp._call_openai_api や regime_detector._call_openai_api は差し替えやすいよう設計されています。
- DuckDB はローカルファイルで軽量に使えます。研究処理は SQL と Python の組合せで実行されるため、データ投入後に個別関数を直接呼んで挙動検証ができます。
- MonitoringDB の初期化は init_monitoring_db(conn) を使ってください。既存 DB に対するマイグレーション（例: dashboard.peak_value カラム追加）も処理されます。

---

もし README に追加したい具体的な情報（例: 実際の .env.example、requirements.txt、CI 手順、実際の Broker 実装ガイドなど）があれば教えてください。必要に応じてサンプルスクリプトや運用手順（デプロイ / Supervisor / systemd での常駐など）も追記します。
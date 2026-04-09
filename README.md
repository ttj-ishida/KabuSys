# KabuSys

日本株の自動売買・リサーチ・監視を目的とした小規模なフレームワークです。  
戦略のファクター計算、ポートフォリオ構築、発注エンジン、監視／アラート、AI を使ったニュースセンチメント等の機能をモジュール化して実装しています。

---

## プロジェクト概要

KabuSys は以下の主要機能を持ちます。

- DuckDB に格納された価格・財務データからファクターを計算する研究モジュール（momentum, volatility, value など）
- ポートフォリオ候補選定・重み付け・株数決定・セクター制約等のポートフォリオ構築パイプライン
- 発注管理（OrderManager / ExecutionEngine）とブローカー API 抽象（Protocol）
- 起動時リコンシリエーション（Reconciler）でクラッシュ後の整合性回復
- 監視機構（System/Trade/Risk Monitor）、LINE 通知による AlertManager、kill.flag による停止
- AI（OpenAI）を用いたニュースセンチメント評価（news_nlp）およびマクロレジーム判定（regime_detector）
- Streamlit を用いた監視ダッシュボード（read-only）

設計方針として「副作用を最小にした純粋関数部分」と「DB/外部 API への接続層を分離」することで、テストと安全性を考慮しています。

---

## 主な機能一覧

- research:
  - calc_momentum, calc_volatility, calc_value — DuckDB 上の prices_daily / raw_financials を参照してファクター計算
  - calc_forward_returns, calc_ic, factor_summary — 特徴量探索・IC 計算等
- portfolio:
  - select_candidates, calc_equal_weights, calc_score_weights — 候補抽出・配分
  - calc_position_sizes — 株数決定（risk_based / equal / score）
  - apply_sector_cap, calc_regime_multiplier — セクター・レジーム関連制約
- ai:
  - score_news — raw_news を OpenAI で評価して ai_scores に書き込み
  - score_regime — ETF 1321 の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime を書き込み
- execution:
  - OrderManager, ExecutionEngine, Reconciler — 発注管理・実行エンジン・再同期
  - broker_api — ブローカーインターフェース定義、例外クラス、データモデル
- monitoring:
  - MonitoringDB — SQLite ベースの監視ログ保存
  - SystemMonitor / TradeMonitor / RiskMonitor — 各種監視ロジック
  - AlertManager — LINE Push 通知（クールダウン付き）
  - KillSwitch / MonitoringEngine — 全体監視と自動停止処理
  - streamlit_dashboard.py — 監視ダッシュボード（read-only）

---

## セットアップ手順（開発環境）

以下は基本的なセットアップ例です。プロジェクトルートに移動して実行してください。

1. Python 環境（推奨: 3.10+）を準備
   - 仮想環境を作成・有効化
     - python -m venv .venv && source .venv/bin/activate  (Unix)
     - python -m venv .venv && .venv\Scripts\activate     (Windows)

2. 依存パッケージをインストール（requirements.txt が無い場合は以下を目安に）
   - pip install duckdb openai requests psutil streamlit

   ※ 実行に必要な最低限のライブラリはコード中の import から推測しています。実環境では必要に応じて他のパッケージを追加してください。

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（詳しくは下記「環境変数」参照）。
   - テストなどで自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. モニタリング DB 初期化（SQLite）
   - Python REPL またはスクリプトから init_monitoring_db を呼ぶ:
     - from kabusys.monitoring.monitoring_db import init_monitoring_db
       import sqlite3
       conn = sqlite3.connect("data/monitoring.db")
       init_monitoring_db(conn)

---

## 主要な環境変数（.env 例）

settings モジュール（kabusys.config.Settings）で参照される代表的な変数:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必要)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (AlertManager / LINE 通知)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (monitoring DB default: data/monitoring.db)
- PAPER_FILL_MODE (instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (1 で起動時に kill.flag をクリア)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development|paper_trading|live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を set すると .env の自動ロードを無効化

簡易的な .env の例:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: config.py はプロジェクトルートを __file__ を基点に探索して `.env` / `.env.local` を自動読み込みします（CWD に依存しません）。プロジェクトルートが特定できない場合は自動ロードをスキップします。

---

## 使い方 (代表的な例)

- research モジュールの利用（DuckDB 接続が必要）:
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
```

- AI ニューススコアリング（OpenAI API キー必要）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を env に設定するか api_key 引数で渡す
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
count = score_regime(conn, target_date=date(2026, 3, 20))
```

- 監視ダッシュボード起動（Streamlit）:
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
（streamlit 実行時に引数 --db で監視 DB を指定できます）

- MonitoringEngine のテスト実行（1 回だけチェック）:
```python
from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine
# 各モニタのインスタンス化に必要な DB/クライアントを渡す
engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(...), alert_manager=AlertManager(...))
engine.run_once()  # テスト目的に 1 回だけ実行
```

- ExecutionEngine（本番セッション実行例）:
  - ExecutionEngine の起動には BrokerAPI 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続などを用意する必要があります。config に target_date を渡して run_session() を呼びます。
  - 実運用前に kill.flag などのファイルパス、PID 管理や監視 DB の初期化を確認してください。

---

## モジュール / ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — .env / 環境変数読み込みと Settings
- ai/
  - news_nlp.py — ニュースを OpenAI で評価し ai_scores に書き込む
  - regime_detector.py — マクロ + MA200 による市場レジーム判定
- research/
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定、スケーリング、lot 単位丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- execution/
  - broker_api.py — Broker API の型・Protocol・例外・データモデル
  - order_manager.py — 注文状態遷移・送信ロジック
  - execution_engine.py — シグナル処理と WebSocket ドレイン
  - reconciler.py — 起動時リコンシリエーション
- monitoring/
  - monitoring_db.py — SQLite テーブル定義 + MonitoringDB
  - system_monitor.py — CPU / メモリ / データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — DD / ポジション上限監視と dashboard 更新
  - alert_manager.py — LINE へのプッシュ通知
  - kill_switch.py — kill.flag の書き込み/削除
  - monitoring_engine.py — 各 Monitor をまとめてポーリング
  - streamlit_dashboard.py — Streamlit での監視ダッシュボード

その他: execution/ に OrderRepository、order_record、risk_manager 等のモジュール（コードベース全体の一部）

---

## テスト・デバッグのヒント

- Settings の自動 .env ロードを無効にしたい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI を使う機能は外部 API 呼び出しを行うため、unit テストでは _call_openai_api をモックすることを推奨
  - news_nlp と regime_detector はそれぞれ内部で _call_openai_api を呼ぶので、patch してレスポンスをシミュレートできます
- DuckDB を用いた research 関数は副作用がなく入力（conn, target_date）に依存するためユニットテストが容易
- MonitoringDB.init_monitoring_db は冪等であり、既存 DB に対してカラム追加（簡易マイグレーション）も行います

---

## ライセンス / 貢献

この README はコードベースのドキュメント生成目的に作成しています。実際にリポジトリで運用する場合は LICENSE、CONTRIBUTING、CI 設定や requirements.txt / pyproject.toml を追加して下さい。

---

この README はコード内の docstring と実装に基づいて作成しました。さらに具体的な実行例・CI 用コマンドや Dockerfile 等の支援が必要であれば教えてください。
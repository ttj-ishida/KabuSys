# KabuSys

日本株向けの自動売買／リサーチ／監視ライブラリ群。  
ポートフォリオ構築、ポジションサイズ計算、ファクター計算、ニュース NLP、実行エンジン、監視エンジンなどをモジュール化して提供します。

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- 日次の銘柄選定（シグナル）→ 発注フロー（ExecutionEngine）
- ポートフォリオ構築（候補選定・重み付け・リスク調整・株数算出）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ニュースを LLM（OpenAI）でスコア化する NLP パイプライン
- 市場レジーム判定（ETF MA + マクロニュースの LLM 判定）
- 監視（システム／注文／リスク）とアラート（LINE Push）
- SQLite / DuckDB を利用したデータ永続化・分析

設計方針として、DB への読み書きや外部 API 呼び出しを明示的に分離し、テスト可能でクラッシュ耐性のある実装を目指しています。

---

## 主な機能一覧

- 設定管理（.env 自動読み込み、環境変数アクセス） — kabusys.config
- ポートフォリオ:
  - 候補選定（score / rank ベース）
  - 等金額・スコア加重配分
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（risk_based / equal / score）
- リサーチ:
  - モメンタム / ボラティリティ / バリュー計算（DuckDB ベース）
  - 将来リターン計算・IC（Information Coefficient）や統計サマリー
- AI:
  - ニュースセンチメントの LLM スコア化（OpenAI）
  - 市場レジーム判定（ETF MA + マクロニュース）
- 実行:
  - OrderManager / ExecutionEngine（発注の状態遷移・リコンシリエーション対応）
  - Broker API 抽象化プロトコル（テスト用モック実装可）
- 監視:
  - MonitoringDB（SQLite）によるログ永続化
  - System/Trade/Risk Monitor、KillSwitch、AlertManager（LINE）
  - Streamlit ダッシュボード（監視用 UI）

---

## 前提・依存ライブラリ

- Python 3.10+
- ランタイム依存（代表例）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボード用)

インストールは pyproject.toml / requirements.txt がある想定です。手動例:

```
python -m venv .venv
source .venv/bin/activate
pip install -e .            # または pip install -r requirements.txt
```

---

## 環境変数 / 設定

- 自動で .env をプロジェクトルートから読み込みます（.git または pyproject.toml を起点）。読み込み優先度:
  1. OS 環境変数
  2. .env.local（override=True）
  3. .env（override=False）
- 自動読み込みを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（コードから抽出）:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — Monitoring DB（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — PaperTrading の fill モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite DB
- PID_FILE_PATH — 実行プロセス PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で有効）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — environment (development | paper_trading | live)
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

設定値は Python から以下で参照できます:

```py
from kabusys.config import settings
token = settings.jquants_refresh_token
db_path = settings.duckdb_path
```

必須環境変数が未設定の場合は ValueError が発生します。

---

## セットアップ手順（手順例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存関係インストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

3. 環境変数設定
   - `.env.example` があればコピーして `.env` を作成し、必要な値を設定してください。
   - もしくは OS 環境変数として設定。

   例 (.env):
   ```
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=yourpassword
   JQUANTS_REFRESH_TOKEN=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   ```

4. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

5. 監視 DB 初期化（SQLite）
   ```py
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db
   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

---

## 使い方（主な実行例）

- Streamlit ダッシュボード（監視 UI）:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ニューススコア生成（AI）
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定（AI）
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監視エンジン（テスト的に 1 回だけ実行）
  ```py
  import sqlite3
  import duckdb
  from kabusys.monitoring import (
      SystemMonitor, TradeMonitor, RiskMonitor,
      MonitoringEngine, AlertManager, KillSwitch, init_monitoring_db
  )

  # DB 準備
  mconn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(mconn)
  dconn = duckdb.connect("data/kabusys.duckdb")

  sys = SystemMonitor(mconn, dconn)
  # TradeMonitor は OrderRepository を要求します。テストではモックを渡す必要があります。
  trade = TradeMonitor(mconn, order_repo=your_order_repo)
  risk = RiskMonitor(mconn)
  kill = KillSwitch(flag_path=Path("data/kill.flag"))
  alert = AlertManager(channel_access_token="", user_id="")  # 空ならログのみ

  engine = MonitoringEngine(sys, trade, risk, interval_sec=60, kill_switch=kill, alert_manager=alert)
  engine.run_once()  # 1回だけ実行（テスト用）
  ```

- ExecutionEngine（本番セッション実行）
  実運用では BrokerAPI の実装（kabu station client）と OrderRepository 等を注入して run_session を呼びます。主要な流れは:
  1. 起動時に Reconciler で注文同期
  2. signal_send_start の時刻にシグナル処理（Gate1/2 を経て発注）
  3. push drain（WebSocket 受信）で約定処理と Gate3 チェック
  4. 市場クローズで終了。PID ファイル管理、kill.flag のチェックを行う

  実行例（概略）:
  ```py
  engine = ExecutionEngine(
      broker=your_broker_impl,
      repo=your_order_repo,
      risk_manager=your_risk_manager,
      order_manager=your_order_manager,
      duckdb_conn=duckdb.connect("data/kabusys.duckdb"),
      config=EngineConfig(target_date=date.today()),
      reconciler=your_reconciler,
  )
  engine.run_session()
  ```

注意: Execution エンジンには多数の依存（Broker 実装、OrderRepository、RiskManager 等）が必要です。ユニットテストではこれらをモック化して部分実行してください。

---

## 主要ディレクトリ構成

（src/kabusys 以下の主要ファイルと簡潔説明）

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数 / .env 読み込み / Settings
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定、等重・スコア重み計算
  - position_sizing.py — 株数決定、aggregate cap、lot 単位丸め
  - risk_adjustment.py — セクター上限、レジーム乗数
- src/kabusys/research/
  - factor_research.py — momentum / volatility / value の計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- src/kabusys/ai/
  - news_nlp.py — raw_news を LLM でスコア化して ai_scores に書込
  - regime_detector.py — ETF MA + マクロニュースでレジーム判定
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル初期化 + MonitoringDB ラッパ
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 管理（停止シグナル）
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 複数 Monitor を束ねる
  - streamlit_dashboard.py — 監視用 Streamlit UI
- src/kabusys/execution/
  - broker_api.py — Broker API のデータモデル / Protocol / 例外
  - order_manager.py — 注文の作成・送信・同期・キャンセル（state machine）
  - reconciler.py — 再起動時のリコンシリエーション
  - execution_engine.py — Signal Queue ベースの発注エンジン
  - その他（order_repository 等は別ファイルとして想定）
- src/kabusys/monitoring/__init__.py, src/kabusys/research/__init__.py, src/kabusys/ai/__init__.py, src/kabusys/portfolio/__init__.py — エクスポート集合

---

## 開発・貢献

- コードはモジュール単位でユニットテストを書きやすい設計（依存注入・プロトコル使用）になっています。外部 API 呼び出し部分はモック化してテストしてください。
- .env のサンプル（.env.example）がある場合はそれを参考に環境変数を整えてください。
- 自動ロード動作を無効化したいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。

---

何か特定のコンポーネント（例: ExecutionEngine の統合例、OrderRepository 実装例、テスト用モックの書き方）について README に追記したい場合は、用途に応じてサンプルコードや手順を追加します。どの部分を詳しく載せますか？
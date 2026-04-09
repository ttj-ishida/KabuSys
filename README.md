# KabuSys

日本株自動売買システム（ライブラリ群／監視・研究・発注エンジンのコア実装）。

このリポジトリは、シグナルからポートフォリオ構築、ポジションサイズ算出、発注管理、監視、ファクター研究、ニュースセンチメント（LLM）評価までを含む一連のコンポーネントを提供します。モジュールは可能な限り純粋関数・テスト可能なインターフェースで設計されており、実際のブローカー呼び出しはプロトコル経由で差し替え可能です。

---

## 主な機能

- 環境変数管理（.env / .env.local 自動ロード）
- ポートフォリオ構築
  - シグナル選定（スコア順）
  - 等加重 / スコア加重のウェイト計算
  - セクター上限フィルタ
  - レジーム乗数（bull/neutral/bear）
  - ポジションサイズ計算（risk-based / equal / score、単元丸め、aggregateキャップ）
- 研究用ファクター計算
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- ニュース NLP（OpenAI）によるセンチメントスコア化（ai_scores への書込）
  - バッチ送信、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定（ETF + マクロニュース + LLM 統合）
- 発注・実行管理
  - OrderManager / OrderRepository / Reconciler / ExecutionEngine
  - BrokerAPI の Protocol に基づく差し替えが可能
- 監視（Monitoring）
  - System / Trade / Risk の各モニタ
  - SQLite による永続化（MonitoringDB）
  - LINE Push によるアラート（AlertManager）
  - kill.flag による外部停止シグナル
  - Streamlit ベースの監視ダッシュボード

---

## 動作要件（推奨）

- Python 3.10+
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（最新 v1 系を想定）
- requests
- psutil
- streamlit（監視ダッシュボード起動時）
- SQLite（標準ライブラリで利用可能）

必要パッケージはプロジェクトに requirements.txt がある場合はそれを使うか、下記を参考にインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
```

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo>
```

2. 仮想環境の作成（任意だが推奨）
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # 存在する場合
# または必要パッケージを個別にインストール
pip install duckdb openai requests psutil streamlit
```

3. .env ファイルを用意
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を配置すると自動で読み込まれます。
- `.env.local` は `.env` を上書きする優先度で読み込まれます。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

主な環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用必須トークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで必要）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用
- LINE_USER_ID — LINE 通知先ユーザ ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — Monitoring DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / LOG_LEVEL / KABUSYS_ENV 等

.env の書式は一般的な KEY=VALUE に対応し、export プレフィックスやクォート／エスケープも処理します。

4. DB の初期化（監視 DB）
```python
# Python から
import sqlite3
from kabusys.monitoring.monitoring_db import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
conn.close()
```

---

## 簡単な使い方

- 設定の取得（任意のモジュール／スクリプト内）
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

- Streamlit 監視ダッシュボード起動
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- ニュースセンチメントスコア生成（ai/news_nlp）
```python
import duckdb
import sqlite3
from datetime import date
from kabusys.ai.news_nlp import score_news

duck_conn = duckdb.connect("data/kabusys.duckdb")
# score_news は DuckDB 接続（raw_news 等）を参照します
n_written = score_news(duck_conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"書き込み銘柄数: {n_written}")
```

- レジーム判定（ai/regime_detector）
```python
from kabusys.ai.regime_detector import score_regime
# duck_conn は DuckDB 接続
score_regime(duck_conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 研究関数（例: モメンタム計算）
```python
from kabusys.research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
```

- 監視エンジン（テスト実行）
```python
from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, AlertManager, KillSwitch
# 必要なコネクション・依存を作成して MonitoringEngine を組み立て、run_once() や run() を呼ぶ
```

- ExecutionEngine（本番的な実行）
ExecutionEngine は broker 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続など多数の依存を必要とします。ユニットテストやローカル実行ではモック／スタブを使って個別機能をテストしてください。

---

## 自動環境ロードの動作

- 起動時に環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` が設定されていない場合、プロジェクトルート（.git または pyproject.toml を持つ）を起点に `.env`、続いて `.env.local` を読み込みます。
- 読み込み順の優先度: OS 環境 > .env.local > .env
- `.env.local` は override=True のため既存の OS 環境を上書きしません（ただし .env を上書きします）。
- ファイルが見つからない・読み込めない場合は警告を出しながらスキップします。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ情報
- config.py — 環境変数 / 設定管理
- portfolio/
  - portfolio_builder.py — 候補選定・等/スコア重み
  - position_sizing.py — 株数決定・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- ai/
  - news_nlp.py — ニュースの LLM スコアリング（ai_scores 書込）
  - regime_detector.py — 市場レジーム判定（ETF + マクロ + LLM）
- monitoring/
  - monitoring_db.py — SQLite スキーマと MonitoringDB クラス
  - system_monitor.py — システム／データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション制限監視
  - kill_switch.py — kill.flag 制御
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 監視ループ統合
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - broker_api.py — Broker API のデータモデル / Protocol / 例外
  - order_manager.py — 発注 FSM（OrderManager）
  - reconciler.py — 再起動時のリコンシリエーション
  - execution_engine.py — Signal Queue Pull 型発注エンジン
  - （その他 OrderRepository / order_record 等が想定されるモジュール）
- monitoring, research, portfolio, ai, execution 以下にユーティリティや DB 操作の実装が含まれます。

---

## テスト / 開発メモ

- 多くの関数は純粋関数または明確な I/O（DB/外部API）インターフェースで設計されており、ユニットテストの差し替えが容易です（例: OpenAI 呼び出し箇所は内部関数を patch してモック可能）。
- ExecutionEngine / OrderManager 周りはクラッシュ耐性・2 相永続化の設計があるため、再現性の高い統合テストが望ましいです。
- DuckDB と SQLite を使ったテストデータを用意して CI で検証してください。

---

その他の詳細（設計ドキュメント、PortfolioConstruction.md、StrategyModel.md 等）はリポジトリ内の関連ドキュメントを参照してください。

質問や補足したい項目があれば教えてください。README の内容を特定の運用手順（例: docker 化、CI/CD、サンプル設定ファイル）に合わせて拡張できます。
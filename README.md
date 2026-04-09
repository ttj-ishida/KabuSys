# KabuSys README

以下はこのコードベース（KabuSys）の概要・セットアップ・使い方をまとめた README です。

注意: 本リポジトリは自動売買 / 研究用のライブラリ群のコア実装を含みますが、ブローカークライアントや一部外部データ投入処理は具象実装を想定しています。実運用には環境変数・DB データ・ブローカー実装が必要です。

## プロジェクト概要
KabuSys は日本株向けの自動売買・研究・監視を目的としたモジュール群です。主な目的は以下です。

- ファクター計算・リサーチ（DuckDB 上の過去株価・財務データを利用）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- 市場レジーム判定・ニュースセンチメント評価（OpenAI を用いた NLP）
- 発注エンジン（ExecutionEngine）・注文管理（OrderManager / OrderRepository）
- 監視機能（システム/注文/リスク監視、LINE 通知、Streamlit ダッシュボード）
- 起動時リコンシリエーション（Reconciler）や KillSwitch による安全停止

コードは純粋関数的な部分（リサーチ、ポートフォリオ計算等）と、DB/外部 API を扱う部分（AI 呼び出し、監視、発注）で分離されています。

## 主な機能一覧
- research
  - calc_momentum / calc_volatility / calc_value：DuckDB 上の prices_daily / raw_financials を用いたファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量探索・IC 計算
- portfolio
  - select_candidates / calc_equal_weights / calc_score_weights：候補選定・重み計算
  - calc_position_sizes：単元株丸め・リスクベースや重みベースの株数計算
  - apply_sector_cap / calc_regime_multiplier：セクター上限・レジーム乗数
- ai
  - news_nlp.score_news：ニュース記事を LLM（OpenAI）でスコア化して ai_scores テーブルへ書き込み
  - regime_detector.score_regime：ETF（1321）MA とマクロニュースを統合して市場レジーム判定
- execution
  - ExecutionEngine：Signal Queue を取り込んで発注・push ドレインを行うセッションエンジン
  - OrderManager：OrderState マシンを扱う外向け API（create/send/sync/cancel）
  - Reconciler：起動時リコンシリエーション・ポジション突合
- monitoring
  - MonitoringDB：SQLite ベースの監視ログ永続化（テーブル作成ユーティリティあり）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager：監視・アラート一式
  - streamlit_dashboard.py：Streamlit を使った監視ダッシュボード

## 必要環境 / 依存パッケージ
- Python 3.10+ 推奨（typing の表記に | を使用）
- 必要な Python パッケージ（少なくとも以下）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (監視ダッシュボード実行時)
- SQLite は標準ライブラリで提供されます。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
```

（テストや静的解析を行う場合は pytest 等を追加してください）

## 環境変数 / .env
設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動ロード）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須): J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN: LINE push 通知用トークン（AlertManager）
- LINE_USER_ID: LINE 通知先ユーザ ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: Paper Trading の fill_mode（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 sqlite DB パス
- PID_FILE_PATH: PID ファイル保存パス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値
- KABUSYS_ENV: environment 切替 (development|paper_trading|live)
- LOG_LEVEL: ログレベル (DEBUG|INFO|...)


.env の例（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=secret
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

読み込み順序: OS 環境 > .env.local > .env（.env.local は .env を上書き）。プロジェクトルートは `.git` または `pyproject.toml` を探索して特定します。

## セットアップ手順（簡易）
1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo>
```

2. 仮想環境作成・依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
```

3. .env を作成（上記を参照）
4. 監視 DB 初期化（SQLite）:
```python
# 例: scripts/init_monitoring_db.py
import sqlite3
from pathlib import Path
from kabusys.monitoring.monitoring_db import init_monitoring_db

Path("data").mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
conn.close()
```
実行:
```bash
python scripts/init_monitoring_db.py
```

5. DuckDB（prices_daily, raw_financials, raw_news 等）には必要なテーブル・データを投入してください。これらは外部データ供給が必要です（CSV インポートや ETL パイプラインを別途作成してください）。

## 使い方（主要なモジュールの利用例）

- settings（環境設定）
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.is_live)
```

- research（ファクター計算）
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect(str(settings.duckdb_path))
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
```

- AI スコアリング（ニュース）
```python
from kabusys.ai.news_nlp import score_news
# conn: duckdb connection、target_date: date、OPENAI_API_KEY を環境変数に設定済み
written = score_news(conn, target_date)
print(f"wrote {written} ai scores")
```

- レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date)
```

- 監視エンジン（テスト的に 1 回実行）
```python
from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, AlertManager, KillSwitch
# conn: sqlite3 connection、duckdb_conn: duckdb connection
sys_mon = SystemMonitor(sqlite_conn, duckdb_conn)
trade_mon = TradeMonitor(sqlite_conn, order_repo)
risk_mon = RiskMonitor(sqlite_conn)
kill_switch = KillSwitch(settings.kill_flag_path)
alert_mgr = AlertManager(settings.line_channel_access_token, settings.line_user_id)
engine = MonitoringEngine(sys_mon, trade_mon, risk_mon, interval_sec=60, kill_switch=kill_switch, alert_manager=alert_mgr)
engine.run_once()  # テスト用: 1回だけ実行
```

- Streamlit ダッシュボード
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- ExecutionEngine（概念）
ExecutionEngine をそのまま動かすには BrokerAPIProtocol 実装（ブローカークライアント）、OrderRepository（SQLite 実装）、RiskManager 等の具象が必要です。これらを注入して `ExecutionEngine.run_session()` を呼びます。コード中に詳細なフロー（Gate 1-3、push drain、kill_switch、PID ファイル操作）が実装されています。

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Volatility / Value 計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - portfolio/
    - __init__.py
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・丸め・キャップ処理
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - execution/
    - broker_api.py           — Broker API プロトコル・モデル・例外
    - execution_engine.py     — Signal-driven 発注エンジン
    - order_manager.py        — Order State Machine API
    - reconciler.py           — 起動時リコンシリエーション
    - ...（他に order_repository 等が存在する想定）
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite テーブル初期化・ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py

## 注意事項・運用上のポイント
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索して行われます。テスト時に自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI を利用する機能（news_nlp, regime_detector）は API キーが必須です。API 呼び出しは再試行やフォールバック（失敗時は安全側の値）を取る設計になっていますが、API 利用量・レート制限に注意してください。
- ExecutionEngine や発注周りはブローカー実装に依存します。テスト用にモック実装を用意することを推奨します。
- monitoring の SQLite スキーマは init_monitoring_db で作成できます。DuckDB 側の tables（prices_daily / raw_financials / raw_news / signals / portfolio_targets / ai_scores / market_regime 等）は別途 ETL で用意してください。
- KillSwitch は file flag（デフォルト data/kill.flag）を用いるため、運用上の誤検出・残留に注意し、必要なら KILL_FLAG_CLEAR_ON_START を使って起動時に自動クリアする設定を検討してください。

---

これで README のサンプルは終わりです。追加で以下が必要であれば教えてください：
- 実行例（ミニマルなモックブローカーを使った実行スクリプト）
- DuckDB テーブル DDL / CSV インポート例
- CI / テスト実行手順（pytest）
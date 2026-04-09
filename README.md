# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量フレームワークです。  
ポートフォリオ構築、銘柄スコアリング、ニュース NLP によるセンチメント評価、市場レジーム判定、監視ダッシュボード、発注エンジン（ExecutionEngine）等の主要機能をモジュール化して提供します。

---

## 主な特徴（機能一覧）

- 環境変数・.env 自動ロード（プロジェクトルート検出）
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額配分、スコア加重配分
  - セクター集中制限、レジーム乗数適用
  - ポジションサイズ計算（リスクベース / weight ベース）
- リサーチ（DuckDB ベース）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ
- AI 統合
  - ニュース記事を OpenAI（gpt-4o-mini）に投げて銘柄別センチメントを算出（ai_scores 書込）
  - マクロニュース + ETF MA による日次市場レジーム判定（bull/neutral/bear）
  - 再試行・エラーハンドリング・レスポンス検証を内蔵
- 監視・アラート
  - SQLite ベースの監視 DB（system_status, trade_logs, positions, risk_logs, dashboard）
  - System / Trade / Risk モニタ、アラート（LINE Push 経由）
  - kill.flag による実行停止シグナル
  - Streamlit ダッシュボード（read-only）
- 発注・実行
  - Broker API 抽象化（Protocol）と OrderManager（状態遷移／永続化）
  - ExecutionEngine（シグナル処理 + WebSocket push ドレイン）
  - 起動時リコンシリエーション (Reconciler)
- テストしやすい設計
  - DB/外部 API 呼び出しを分離し、モック/patch を容易に想定

---

## 要件（概略）

- Python 3.10+
- 主要依存ライブラリ（抜粋）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit
- 標準ライブラリ: sqlite3, logging, datetime, pathlib など

（プロジェクト配布時に requirements.txt / pyproject.toml を用意する想定です）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（例）
   ```
   pip install duckdb openai requests psutil streamlit
   ```

4. 環境変数設定
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成。
   - 利用する主なキー例：
     - JQUANTS_REFRESH_TOKEN=
     - KABU_API_PASSWORD=
     - OPENAI_API_KEY=
     - KABU_API_BASE_URL=（例: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN=
     - LINE_USER_ID=
     - DUCKDB_PATH=（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH=（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH=（Paper trading DB）
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...

   自動ロードの挙動：
   - OS 環境変数 > `.env.local` > `.env`
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 監視 DB 初期化（SQLite）
   - Python REPL またはスクリプトで実行例：
     ```python
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()
     ```
   - `data/` ディレクトリを作成しておくことを推奨します。

6. DuckDB 用データ準備
   - prices_daily / raw_financials / raw_news などのテーブルを DuckDB にロードしておく必要があります（リサーチ/AI モジュールで使用）。

---

## 使い方（主な例）

### 設定（Settings）を読む
```python
from kabusys.config import settings
print(settings.kabu_api_base_url)
print(settings.duckdb_path)
```

### Streamlit ダッシュボード（監視）
起動コマンド（監視 DB のパスを指定）:
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

### 監視エンジンを単発実行（テスト用）
```python
import sqlite3, duckdb
from kabusys.monitoring import (
    SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine, init_monitoring_db
)
# 接続準備
mon_conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(mon_conn)
duck_conn = duckdb.connect("data/kabusys.duckdb")
# 必要な依存オブジェクトを作成（OrderRepository などはモックでも可）
# ここでは最小構成の例（TradeMonitor は order_repo を必要とする点に注意）
system_monitor = SystemMonitor(mon_conn, duck_conn)
# trade_monitor, risk_monitor は実装依存で用意する
engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(Path("data/kill.flag")), alert_manager=AlertManager(...))
engine.run_once()  # テスト用に1回だけ実行
```

### ニュース NLP スコアリング（AI）
OpenAI API キーを環境変数 `OPENAI_API_KEY` にセットした上で呼び出します。
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written} ai_scores")
```
- api_key を明示的に渡すことも可能： `score_news(conn, date, api_key="sk-...")`
- 実行時は raw_news / news_symbols / ai_scores テーブルが必要です。

### 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を参照
```

### リサーチ関数の利用例
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

### ExecutionEngine（本番発注エンジン）
ExecutionEngine を動かすには以下の実装が必要です（インターフェース/protocol）：
- BrokerAPIProtocol（ブローカークライアント）
- OrderRepository（SQLite を使った永続層）
- RiskManager（Gate チェック）
- OrderManager（OrderRepository と Broker を組み合わせて生成）
- duckdb 接続、EngineConfig 等

実際の起動サンプル（概念）：
```python
from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
engine = ExecutionEngine(
    broker=my_broker_impl,
    repo=my_order_repo,
    risk_manager=my_risk_manager,
    order_manager=my_order_manager,
    duckdb_conn=my_duck_conn,
    config=EngineConfig(target_date=date.today())
)
engine.run_session()
```
注意：本番で実行する前に kill.flag の有無、PID 管理、再起動時のリコンシリエーション設定などを十分確認してください。

---

## テスト／デバッグのヒント

- 自動 .env ロードを無効化する:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI 呼び出しや外部 API は unit tests で patch / mock しやすい設計になっています。
  - 例: news_nlp._call_openai_api を patch して期待レスポンスを返す
- DuckDB / SQLite はファイルベースなのでテスト用に一時ファイル（tmpdir）を用意して切り替え可能

---

## ディレクトリ構成（抜粋）

プロジェクトは `src/kabusys` 配下にモジュールが整理されています。主な構成:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定・重み計算
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
    - position_sizing.py           — 株数決定・調整
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Volatility/Value 等
    - feature_exploration.py       — 将来リターン・IC・統計
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — マクロ + MA によるレジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite スキーマ + DB 操作
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py                — Broker API データモデル・Protocol・例外
    - order_manager.py
    - order_repository.py          — (存在を仮定、注文永続化)
    - order_record.py              — (存在を仮定、状態遷移モデル)
    - reconciler.py
    - execution_engine.py
    - risk_manager.py              — (存在を仮定)
  - monitoring/                     — 上記参照

（実際のファイルはさらに細分化されています。ここでは主要ファイルを抜粋）

---

## 注意事項 / 運用上のポイント

- AI（OpenAI）呼び出しは API コストとレート制限に注意して運用してください。リトライや部分失敗の保護ロジックがありますが、運用ポリシーを定めることを推奨します。
- ExecutionEngine の本番稼働にはブローカー API の堅牢な実装テスト・DR（障害復旧）計画が必須です。kill.flag / PID / リコンシリエーション機構を理解したうえで運用してください。
- DuckDB に投入するデータ（prices_daily / raw_financials / raw_news 等）は正確な時刻・データ整合を保ってください。リサーチ・レジーム判定はルックアヘッドバイアス対策が組み込まれていますが、データ準備が不適切だと誤った判断につながります。

---

必要であれば、この README をベースに「運用手順書」「環境変数一覧（.env.example）」や「開発者向けセットアップ手順（詳細）」を作成します。追加で欲しい項目があれば教えてください。
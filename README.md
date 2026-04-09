# KabuSys

バージョン: 0.1.0

日本株向けの自動売買／リサーチ基盤のモジュール群です。ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、LLM を用いたニュース評価などを含みます。ライブラリは純関数的に設計された計算ロジックと、DB/ブローカー/外部 API を呼び出す実装層に分離されています。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 環境変数（主な設定）
- 使い方（簡単なサンプル）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株自動売買を支援するためのライブラリ群です。特徴は以下の通りです。

- DuckDB を用いた時系列データ処理（prices_daily / raw_financials 等を前提）
- 純粋関数として実装されたファクター計算・ポートフォリオ構築ロジック（テスト容易）
- ブローカー抽象（Protocol）を介した発注エンジン（ExecutionEngine / OrderManager）
- 再起動時のリコンシリエーション（Reconciler）で注文・ポジションを自動復旧
- OpenAI 等の LLM を用いたニュースセンチメント評価・市場レジーム判定
- SQLite を用いた監視ログ永続化 + Streamlit ダッシュボード、LINE 通知によるアラート

設計上の意図として、計算ロジックは DB/外部 API に依存しない形で実装され、外側の接続部分を差し替えてテストしやすくなっています。

---

## 主な機能一覧
- research
  - calc_momentum / calc_volatility / calc_value：DuckDB 上でファクターを計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量探索・IC 計算
- portfolio
  - select_candidates / calc_equal_weights / calc_score_weights：候補選定と重み付け
  - calc_position_sizes：株数決定（等金額・スコア・リスクベース）
  - apply_sector_cap / calc_regime_multiplier：セクター集中抑制・レジーム補正
- execution
  - OrderManager / ExecutionEngine：注文作成→送信→同期→キャンセルの管理
  - Reconciler：起動時の注文・ポジション照合と自動復旧
  - BrokerAPIProtocol：ブローカー依存部分を抽象化
- ai
  - score_news：ニュース記事を LLM（OpenAI）でセンチメント評価し ai_scores に書き込み
  - score_regime：ETF(1321)のMAやマクロニュースを組み合わせて市場レジーム判定
- monitoring
  - MonitoringDB：監視用 SQLite スキーマと CRUD
  - SystemMonitor / TradeMonitor / RiskMonitor：各種監視ロジック
  - AlertManager：LINE Push によるアラート送信（クールダウン機能付き）
  - streamlit_dashboard.py：監視ダッシュボード（Streamlit）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で | 演算子を使用しているため）
- git リポジトリ（プロジェクトルート検出に .git や pyproject.toml を利用）

推奨手順（UNIX 系シェルの例）:

1. リポジトリをクローン / ワーキングディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存ライブラリをインストール
   主要依存（少なくとも）:
   - duckdb
   - openai
   - psutil
   - requests
   - streamlit

   例:
   ```
   pip install duckdb openai psutil requests streamlit
   ```

   ※ requirements.txt が提供されていれば `pip install -r requirements.txt` を使用してください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env`／`.env.local` を置くことで自動読み込みされます（後述）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 監視 DB の初期化（SQLite）
   Python REPL かスクリプトで:
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db
   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

---

## 環境変数（主な設定）
config.py により .env / .env.local / OS 環境変数から取得されます。自動ロードの優先順位は OS 環境 > .env.local > .env です。.env.local は .env を上書きできます。

主要な環境変数（例・用途）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (LLM 呼び出し / ai.score_news, ai.score_regime)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (AlertManager 用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視DB デフォルト: data/monitoring.db)
- PAPER_FILL_MODE (paper trading のモック挙動: instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (1 にすると起動時に kill.flag を自動クリア)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

.env の例（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=Uxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

自動読み込みの挙動
- 実行時に config モジュールがプロジェクトルートを探索し、.env を読み込み（未設定のキーのみ）、次に .env.local を読み込み（既存の OS 環境変数を保護しつつ上書き可能）します。
- 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。

---

## 使い方（簡単な例）

注意: 多くの機能は DuckDB やブローカークライアント、SQLite 接続等を引数で受け取るため、呼び出し前に適切な接続／クライアントを用意してください。

- ファクター計算（例: モメンタム）
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
# records は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
```

- ニュースセンチメント（AI）スコアを生成して DB に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {count}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
# DuckDB 接続 conn を用意
score_regime(conn, date(2026,3,20), api_key="sk-...")
```

- 監視ダッシュボード起動（Streamlit）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AlertManager（LINE）利用例
```python
from kabusys.monitoring import AlertManager
am = AlertManager(channel_access_token="...", user_id="U...")
am.notify("テスト通知", level="INFO", category="TEST")
```

- ExecutionEngine / OrderManager / Broker を組み合わせた実行は簡単なサンプルでは済まないため、実際のブローカークライアント（BrokerAPIProtocol 実装）と各リポジトリを作成して組み立ててください。主要な流れは ExecutionEngine.run_session() に従います。

---

## ディレクトリ構成（主なファイル）
（リポジトリ内 src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理
  - portfolio/
    - __init__.py
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数決定・スケールダウン
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Volatility / Value
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース -> LLM センチメント -> ai_scores
    - regime_detector.py         — レジーム判定（MA + マクロ NLP）
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite スキーマ + MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py              — ブローカー API モデル・Protocol
    - order_manager.py
    - order_repository.py        — (存在する想定) DB 永続化
    - order_record.py            — Orders の状態管理
    - reconciler.py
    - execution_engine.py
    - risk_manager.py
  - monitoring/                  — 上記モジュール
  - その他: data パイプラインや stats ユーティリティ（kabusys.data.*）を参照

---

## 注意事項 / 補足
- LLM（OpenAI）を利用する機能は API キーが必要です。API 呼び出しのエラーは基本的にフェイルセーフ設計（例: macro_sentiment=0.0）になっていますが、キー未設定時は例外が発生します。
- Execution 系はブローカー実装（BrokerAPIProtocol）と SQLite の OrderRepository 等、周辺実装が必要です。テスト用にモック実装を作成して単体テストを行ってください。
- config モジュールは .env の簡易パーサを独自実装しています。特殊な .env フォーマットを用いる場合は注意してください（クォート、エスケープ、コメントの扱いを行っています）。
- Streamlit ダッシュボードは監視DBを read-only で開くことを想定しています（起動中の MonitoringEngine が書き込みを行う）。

---

この README はコード内のドキュメントや設計コメントに基づいて作成しています。詳細な利用方法や運用フローは実際のブローカークライアント実装や運用環境に合わせて拡張してください。必要であれば、各モジュールごとの詳しい API 仕様やサンプルコードを追記できます。
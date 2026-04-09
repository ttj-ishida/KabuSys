# KabuSys

日本株向けの自動売買システム（モジュール群）。リサーチ（ファクター計算/特徴量探索）、ポートフォリオ構築、発注エンジン、監視・アラート、LLM を使ったニュースセンチメント／レジーム判定などを含む設計済みコンポーネント群です。純粋関数群と DB 永続化層を分離した構成で、テスト容易性・再現性に配慮しています。

---

## 主な機能

- ファクター計算（モメンタム / バリュー / ボラティリティ / 流動性）
- ファクター探索（将来リターン計算、IC 計算、統計サマリー）
- ポートフォリオ構築（候補選定、等金額・スコア加重配分、リスク調整、単元丸め）
- ポジションサイズ計算（risk-based / equal / score、aggregate cap、lot 単位制約）
- 市場レジーム判定（ETF MA200 + マクロニュースの LLM センチメント合成）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント評価 → データベース書き込み）
- 発注エンジン（Signal Queue Pull 型、OrderManager、OrderRepository、Reconciler）
- 監視周り（System / Trade / Risk Monitor、監視 DB、LINE 通知、kill flag）
- Streamlit ベースの監視ダッシュボード

---

## 動作要件

- Python 3.10 以上（型アノテーションの union 演算子 `|` を利用）
- 主要依存パッケージ（例）:
  - duckdb
  - openai (OpenAI Python SDK)
  - requests
  - psutil
  - streamlit

推奨インストール（仮想環境内）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
```

（プロジェクトがパッケージ化されている場合は `pip install -e .` を使えます。）

---

## セットアップ手順

1. リポジトリをクローンする
```bash
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境を作る・有効化して依存をインストール（上記参照）

3. 環境変数を準備する
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（プロジェクトルートは `.git` または `pyproject.toml` を基準に推定）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。
   - 主要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
     - KABU_API_PASSWORD — 必須（kabuステーション API 用パスワード）
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - OPENAI_API_KEY — OpenAI 呼び出しで必要（ai.score_news / score_regime 等）
     - LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用（未設定時は送信をスキップ）
     - LINE_USER_ID — LINE 通知先ユーザ ID
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH — 各種パス（デフォルトを利用可）
     - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH — Paper Trading 用設定
     - KABUSYS_ENV — environment: development | paper_trading | live
     - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL

   - サンプル `.env`（最低限の例）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     OPENAI_API_KEY=sk-...
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. 監視 DB の初期化（SQLite）
```python
# 任意のスクリプトまたは Python REPL で
import sqlite3
from kabusys.monitoring.monitoring_db import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
conn.close()
```

---

## 使い方（代表例）

- Streamlit ダッシュボード起動
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- DuckDB を使ったファクター計算（Python スクリプト例）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
```

- OpenAI によるニューススコア生成（ai_scores テーブルへ書き込む）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print(f"written: {n_written}")
```

- 市場レジーム判定（market_regime テーブルへ書き込む）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, date(2026, 3, 20), api_key="sk-...")
```

- 監視エンジン単発実行（テスト用）
```python
from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager
# 各種インスタンス化（SQLite/duckdb/OrderRepository/Broker 等を渡す必要あり）
engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(...), alert_manager=AlertManager(...))
engine.run_once()  # 1回だけ実行（ユニットテスト向け）
```

- ExecutionEngine（本番セッション実行）
  - ExecutionEngine は BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB コネクション等を受け取って動作します。run_session() がセッションのエントリポイントです（PID 書き込み、kill.flag チェック、WebSocket push drain 等を行います）。
  - テスト時は内部の `_process_signals()` や `_drain_push_queue()` を直接呼ぶ設計です。

---

## 重要な挙動メモ

- .env の自動ロード
  - プロジェクトルート（.git または pyproject.toml の所在）から `.env` → `.env.local` の順に読み込みます。
  - OS 環境変数が優先され、`.env.local` は既存 OS 環境変数を上書きせず `.env` より優先して読み込まれます（._load_env_file の override/protected ロジック）。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数に設定してください（テストでの制御向け）。

- OpenAI API の呼び出し
  - news_nlp / regime_detector は OpenAI SDK を使います。API 呼び出しはリトライやバックオフ、レスポンスバリデーション（JSON mode の厳格な解析）を実装しています。
  - テストでは内部関数（例: _call_openai_api）をモックすることでネットワーク依存を切り離せます。

- kill.flag
  - ExecutionEngine はプロセス起動時に kill.flag の存在を検査します（`settings.kill_flag_clear_on_start` が 1 の場合はクリアして起動可能）。
  - KillSwitch はファイル作成による停止シグナル発行と冪等な操作（既存なら書き直さない）を行います。

---

## ディレクトリ構成（主要ファイル・概要）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数/設定管理（.env 自動ロード、Settings クラス）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
    - risk_adjustment.py — セクター上限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
    - position_sizing.py — 株数決定、単元丸め、aggregate cap（calc_position_sizes）
  - research/
    - factor_research.py — momentum/value/volatility ファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI） → ai_scores 書き込み
    - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース LLM）
  - monitoring/
    - monitoring_db.py — SQLite によるテーブル定義・CRUD ヘルパー（MonitoringDB）
    - risk_monitor.py — ドローダウン・ポジション数監視（RiskMonitor）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度の監視（SystemMonitor）
    - trade_monitor.py — 注文滞留・約定異常の監視（TradeMonitor）
    - alert_manager.py — LINE Push 通知（AlertManager）
    - kill_switch.py — kill.flag の作成/検査
    - monitoring_engine.py — 各モニタを束ねるループ（MonitoringEngine）
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - broker_api.py — Broker API のデータモデル・例外・Protocol
    - order_manager.py — 発注ワークフロー（OrderManager）
    - execution_engine.py — Signal Pull / WebSocket drain を統括するエンジン
    - reconciler.py — 起動時の注文/ポジション再照合
    - ほか（order_repository, order_record, risk_manager 等が存在する想定）
  - data/ (参照・外部モジュール)
    - pipeline / stats 等（DuckDB 利用ユーティリティや正規化ユーティリティ参照）
  - monitoring/ などの __init__.py で主要クラスをエクスポート

（上記は主要モジュールの要約です。実装ファイルや追加ユーティリティが別途存在する場合があります。）

---

## 開発・テストメモ

- LLM 呼び出しはネットワークに依存するためユニットテストでは API 呼び出しラッパー（例: _call_openai_api）をモックしてください。
- DuckDB / SQLite を使った関数は DB 接続を引数に受け取る設計なので、テスト用にメモリ DB を用意して deterministic に検証できます。
- 環境変数自動ロードはプロジェクトルート探索に基づくため、テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると副作用を抑えられます。

---

必要であれば、README に「コマンド例」「.env.example のフルテンプレート」「よくあるトラブルシュート（OpenAI レート制限、DuckDB パス問題）」などを追加します。どの情報を詳しく載せたいか教えてください。
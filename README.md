# KabuSys

日本株向けの自動売買／リサーチ／監視フレームワーク（ライブラリ群）。  
DuckDB / SQLite をデータ層に、kabuステーション / OpenAI を外部サービスに利用する設計です。  
本 README はコードベース（src/kabusys 以下）に基づく概要、機能、セットアップと簡単な使い方を日本語でまとめたものです。

注意: 本リポジトリはライブラリ／フレームワーク群を提供します。実際に取引を行うにはブローカー実装や運用用ラッパーが別途必要です。

---

## 主な機能（抜粋）

- 環境変数 / .env 自動読み込みと Settings 管理（kabusys.config）
  - 自動読み込み順: OS 環境変数 > .env.local > .env
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等額/スコア加重の重み計算
  - セクター上限適用、レジーム乗数、株数算出（単元丸め、リスク制限）
- リサーチ（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を使用）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI（kabusys.ai）
  - ニュース NLP による銘柄別センチメントスコア付与（OpenAI API 経由）
  - 市場レジーム判定（ETF MA + マクロニュースの LLM センチメント合成）
  - API 呼び出しは冪等性・リトライ・エラーハンドリングを考慮
- 監視（kabusys.monitoring）
  - SQLite ベースの監視 DB（init_monitoring_db）
  - System / Trade / Risk の各種モニタとアラート（LINE Push 経由）
  - kill.flag 管理、Streamlit ベースの監視ダッシュボード
- 発注・実行（kabusys.execution）
  - OrderManager / ExecutionEngine / Reconciler 等の状態管理ロジック
  - ブローカー API 用 Protocol 定義、OrderRequest/OrderStatus/Position モデル
  - リコンシリエーション（再起動後の同期）ロジック

---

## 必要な環境変数（主要）

下記は本システムで参照される環境変数の主な一覧と説明（必須/任意、デフォルト）:

- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（任意）
- LINE_USER_ID — LINE 通知先 user_id（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading のフィルモード（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — 実行 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（1 でクリア）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値（%）
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env / .env.local をプロジェクトルートに置くと自動ロードされます（自動ロードはプロジェクトルート検出に .git または pyproject.toml を利用）。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発環境の一例）

1. Python 環境（推奨: 3.10+）を用意
2. 仮想環境作成および有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb openai psutil requests streamlit
   - （必要に応じて dev 用に pytest 等を追加）
4. データディレクトリ作成
   - mkdir -p data
5. 環境変数を設定（.env を作成するか環境変数で設定）
6. 監視 DB 初期化（SQLite コネクションを渡して実行）
   - 例: Python REPL / スクリプト内で
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     import sqlite3
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
7. DuckDB ファイルに必要なテーブル（prices_daily, raw_financials, raw_news 等）を用意

注: 本リポジトリに requirements.txt や pyproject.toml がない場合は上記の主要ライブラリを個別にインストールしてください。プロジェクト配布時は pyproject.toml を使うことを想定しています。

---

## 簡単な使い方（例）

以下は代表的なモジュールの呼び出し例です。実運用では各種経路（ブローカ実装、DB コネクション、OrderRepository、RiskManager 等）を実装して注入する必要があります。

- Settings（環境設定）の取得
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_paper, settings.log_level)
```

- AI: ニューススコア算出（OpenAI API キー必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# target_date に対してニュースを集約＆スコアを ai_scores テーブルに書き込む
count = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

- AI: レジームスコア算出（ETF + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
count = score_regime(conn, date(2026,3,20), api_key="sk-...")
```

- Research: ファクター計算（DuckDB 接続が必要）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from datetime import date
moms = calc_momentum(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
```

- Monitoring: Streamlit ダッシュボード起動
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Monitoring DB 初期化（スクリプト内）
```python
import sqlite3
from kabusys.monitoring.monitoring_db import init_monitoring_db
conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
```

- ExecutionEngine（概念）
  - 実際にセッション運用するには BrokerAPIProtocol を満たすクライアント、OrderRepository（SQLite 実装等）、RiskManager、OrderManager、Reconciler、DuckDB 接続を構築して ExecutionEngine に注入します。
  - エントリポイント例（擬似）:
```python
engine = ExecutionEngine(broker=broker_impl,
                         repo=order_repo,
                         risk_manager=risk_manager,
                         order_manager=order_manager,
                         duckdb_conn=duck_conn,
                         config=EngineConfig(target_date=date.today()))
engine.run_session()
```
  - 詳細は src/kabusys/execution 以下のドキュメント（コード内コメント）を参照してください。

---

## .env 読み込みの挙動

- プロジェクトルートは __file__ の親ディレクトリ群を辿り、.git または pyproject.toml を基準に探索します。プロジェクト配布後でも正しく動作するように CWD に依存しません。
- 自動読み込み優先度: OS 環境変数 > .env.local > .env
  - .env.local は .env を上書き可能（override=True）。
  - OS 環境変数は protected として上書きされません。
- 自動ロードを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースは Bash 風の export KEY=val、引用符、インラインコメントを考慮します。

---

## 主要なディレクトリ構成（src/kabusys）

- src/kabusys/
  - __init__.py (パッケージ定義、__version__)
  - config.py (環境設定・Settings)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - research/
    - factor_research.py (mom/vol/value 等)
    - feature_exploration.py (将来リターン、IC、統計)
  - portfolio/
    - portfolio_builder.py (候補選定、重み計算)
    - position_sizing.py (株数算出、スケーリング)
    - risk_adjustment.py (セクター上限、レジーム乗数)
  - monitoring/
    - monitoring_db.py (SQLite スキーマ + DB ラッパー)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (LINE Push)
    - monitoring_engine.py (統合ポーリング)
    - streamlit_dashboard.py (監視ダッシュボード)
  - execution/
    - broker_api.py (データモデル、Protocol、例外)
    - order_manager.py (発注のワークフロー)
    - execution_engine.py (Signal Queue Pull 型発注エンジン)
    - reconciler.py (リコンシリエーション)
    - （その他 ordering / repository 等はプロジェクトにより追加）
  - monitoring、portfolio、research、ai の __init__.py による主要関数のエクスポート

---

## 運用上の注意点 / ベストプラクティス

- DuckDB / SQLite のデータ鮮度とバックアップを運用で管理してください。
- OpenAI API を利用する処理（news_nlp / regime_detector）は API 制限や課金に注意。APIキーの管理は慎重に。
- 本システムの ExecutionEngine は実際の発注を伴います。バックテストや Paper Trading 環境で十分に検証した上でライブ運用してください。
- kill.flag / PID ファイルでプロセス管理と安全停止制御を行います。起動時の kill.flag の扱いは KILL_FLAG_CLEAR_ON_START で制御可能です。
- 監視アラートは LINE Push を利用可能ですが、トークン未設定時はログ出力のみになります。

---

この README はコード内の docstring / コメントに基づき要点をまとめたものです。各機能の詳細な使い方や運用手順については該当モジュール（src/kabusys/ 以下）のドキュメント文字列を参照してください。追加で API 実装例やサンプルスクリプトが必要であればお知らせください。
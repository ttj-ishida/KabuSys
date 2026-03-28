# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants）での市場データ収集、ニュースのNLPスコアリング（OpenAI）、ファクター計算、監査ログ・発注履歴管理などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤・研究基盤で必要なコンポーネント群をモジュール単位で提供します。主な目的は以下です。

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- DuckDB ベースのETL / データ保存（冪等操作）
- ニュース収集と LLM によるセンチメントスコアリング（OpenAI）
- 市場レジーム判定、ファクター計算、特徴量解析
- 監査ログ（signal → order_request → execution）の初期化・管理
- データ品質チェックとカレンダー管理

設計上、バックテストでのルックアヘッドバイアスを避けるために日付参照は外部から渡す設計になっています（datetime.today() を直接参照しない）。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存・認証・レート制限・リトライ）
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS 取得、安全対策・前処理）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化 / DB 作成（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを集約して OpenAI で銘柄別センチメントを算出し ai_scores に書き込み
  - regime_detector.score_regime: ETF (1321) の MA200 乖離 + マクロニュースの LLM センチメントで市場レジームを判定・保存
- research/
  - ファクター計算（Momentum, Value, Volatility）
  - 特徴量解析（forward returns, IC, summary, rank）
- config
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を参照）
  - 環境変数ラッパー（settings オブジェクト）

その他、Slack や kabu API 関連の設定を環境変数で管理する仕組みを持ちます。

---

## セットアップ手順

1. Python 環境を用意（推奨: Python 3.10+）

2. 仮想環境作成・有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 依存パッケージをインストール（必要に応じて requirements を用意してください）。主要な依存例:
   - duckdb
   - openai
   - defusedxml
   - その他標準ライブラリのみで実装された箇所もあります

   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従ってください）
   
4. パッケージを開発モードでインストール（リポジトリルートが src/ を含む構成の想定）
   - pip install -e .

5. 環境変数設定
   - プロジェクトルートに `.env` や `.env.local` を置くと自動で読み込まれます（kabusys.config がロード時に検出して読み込み）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で使用）。

   推奨される主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=...
   - OPENAI_API_KEY=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   .env.example を参考に作成してください（リポジトリに例がある場合）。

---

## 使い方（主要な API とサンプル）

以下はいくつかの典型的な呼び出し例です。いずれも duckdb の接続オブジェクト（kabusys.data 用）を渡して使います。

- DuckDB 接続の例:
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

### ETL の実行（日次 ETL）
Python スクリプト例:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

### ニュースのスコアリング（OpenAI）
- OpenAI API キーは環境変数 OPENAI_API_KEY を設定するか、api_key 引数で渡します。
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

### 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

### 監査ログ DB の初期化
- 監査用の専用 DuckDB を作る場合:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの duckdb 接続
```

### カレンダー・営業日ヘルパー
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print("is trading:", is_trading_day(conn, d))
print("next trading day:", next_trading_day(conn, d))
```

注意:
- OpenAI 呼び出し部分はネットワーク/API レートの影響を受けます。テストでは内部の呼び出しをモックする仕組みが用意されています（関数単位で差し替え可能）。
- ETL / 保存関数は冪等（ON CONFLICT ...）を想定しています。

---

## .env の例（テンプレート）
.example:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# OpenAI
OPENAI_API_KEY=sk-...

# kabu API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 動作環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成

リポジトリ（src/kabusys）内の主なファイル/モジュール構成は以下の通りです（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - calendar_management.py
      - etl.py
      - pipeline.py
      - stats.py
      - quality.py
      - audit.py
      - jquants_client.py
      - news_collector.py
      - etl.py (ETL の公開)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（その他ファイル）
    - (strategy/, execution/, monitoring/ などのサブパッケージが __all__ に含まれる想定)

各モジュールは責務毎に分割されており、data/* は主に DuckDB の ETL と保存、品質管理、カレンダーを扱います。ai/* は LLM を用いたニュース解析や市場レジーム判定、research/* はファクター計算や統計解析です。

---

## 注意事項 / 運用メモ

- 環境変数は .env / .env.local を優先して自動読み込みします（kabusys.config）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出しはリトライ・バックオフ等の保護がありますが、API キーと利用量に注意してください。テストでは API 呼び出しをモックすることを推奨します。
- J-Quants API のレート制限（120 req/min）を守るため、jquants_client にレートリミッタを実装しています。大量取得時は時間を分散してください。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、コード側で空チェックを行っています。
- 監査ログテーブルは削除しない前提で設計されています（ON DELETE RESTRICT）。Timestamp は UTC を使用します。

---

もし README に追加したい具体的な使用例やサンプルスクリプト（CLI、systemd ジョブ、Airflow DAG 例など）があれば、目的に合わせた章を追記します。
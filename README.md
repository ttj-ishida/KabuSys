# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）を備え、研究・シグナル生成・監査ログまでをサポートするモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python パッケージです。

- J-Quants API からの株価・財務・カレンダー等の差分取得と DuckDB への冪等保存（ETL）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）と NLP による銘柄別センチメントスコアリング（OpenAI）
- 市場レジーム判定（ETF + マクロニュースの LLM センチメントを合成）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化
- リサーチ用ファクター計算と特徴量解析ユーティリティ

設計上の特徴として、ルックアヘッドバイアス対策（日時参照の限定）や API リトライ・レート制御・冪等性を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存関数、認証・レート制御）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS 取得と前処理、SSRF 対策、記事ID冪等化）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: ニュースを集約して OpenAI に投げ、銘柄別センチメントを ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF (1321) の MA200 乖離 + マクロニュース LLM を合成し market_regime に書込
- research
  - ファクター計算（momentum, value, volatility）や特徴量解析（forward returns, IC, rank, summary）
- 設定管理（kabusys.config.Settings）
  - .env / .env.local の自動ロード（プロジェクトルート判定）と環境変数参照ラッパー

---

## 前提・依存

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml

pip 例:
```
pip install duckdb openai defusedxml
```

（プロジェクト配布用に setup/pyproject があれば `pip install -e .` などで依存を管理してください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. Python 仮想環境を作成・有効化（任意）
```
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows
```

3. 必要パッケージをインストール
```
pip install duckdb openai defusedxml
```

4. 環境変数設定（.env / .env.local をプロジェクトルートに配置することが可能）
- 自動ロードの挙動:
  - プロジェクトルートは `.git` または `pyproject.toml` を親ディレクトリから探索して決定
  - 自動で `.env` → `.env.local` を読み込む（OS 環境変数が優先）
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

主な環境変数（必須/任意とデフォルト）:
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API のパスワード（自動取引を行う場合）
- 任意（デフォルト値あり）
  - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用
  - DUCKDB_PATH: "data/kabusys.duckdb"
  - SQLITE_PATH: "data/monitoring.db"
  - PID_FILE_PATH: "data/execution.pid"
  - KILL_FLAG_PATH: "data/kill.flag"
  - KILL_FLAG_CLEAR_ON_START: "0" or "1"
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV: "development" | "paper_trading" | "live" (デフォルト "development")
  - LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL" (デフォルト "INFO")
- OpenAI API:
  - OPENAI_API_KEY: News/NLP や regime 判定で使用。関数に api_key を渡すことも可能。

5. データディレクトリ作成（必要に応じて）
```
mkdir -p data
```

---

## 使い方（主要な利用例）

以下はコードレベルの利用例です。DuckDB 接続は `duckdb.connect(path)` を使用します。

- 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)   # Path object
print(settings.env)
```

- ETL（日次パイプライン）の実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 個別 ETL ジョブ（例: 株価差分ETL）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_prices_etl

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

- ニュース収集（RSS）取得
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"])
```

- ニュース NLP スコア生成（OpenAI APIキーは環境変数 OPENAI_API_KEY か api_key 引数）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数使用
print(f"{n_written} 件書き込みました")
```

- 市場レジームスコア計算
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- カレンダー更新ジョブ（J-Quants から差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
```

- 監査ログスキーマの初期化（独立DBを作る例）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# audit_conn は監査用 DuckDB 接続
```

- J-Quants API を直接利用（認証・取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))
```

---

## 開発時の注意 / 実装上のポイント

- ルックアヘッドバイアス防止:
  - 多くの関数が内部で `datetime.today()` を参照しない設計（target_date を引数で渡す）。
  - prices/news のクエリは target_date より前のデータのみを使うなどの配慮あり。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE または ON CONFLICT DO NOTHING を利用して重複を避ける。
- API 呼び出しの堅牢性:
  - J-Quants や OpenAI 呼び出しはリトライ・バックオフ・レート制御を実装。
  - OpenAI のレスポンスパース失敗時はフェイルセーフとして 0.0 を返す等の安全措置あり。
- セキュリティ:
  - ニュース取得は SSRF 対策・プライベートアドレス拒否・XML の defusedxml 利用・レスポンスサイズ制限あり。

---

## ディレクトリ構成

パッケージルート: src/kabusys

主要ファイル・ディレクトリ（抜粋）

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - quality.py
  - stats.py
  - calendar_management.py
  - news_collector.py
  - audit.py
  - audit 初期化ユーティリティ（init_audit_db / init_audit_schema）
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- その他: strategy / execution / monitoring など（パッケージ API 用に __all__ に登録）

（上記はソースコメントを基にした主要構成です。プロジェクト内にさらに補助モジュールが含まれる場合があります。）

---

## よくある質問 / トラブルシューティング

- .env が自動で読み込まれない
  - プロジェクトルートが `.git` または `pyproject.toml` を基準に探索されます。ルートが特定できない場合は自動ロードをスキップします。自動ロード自体を無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。
- OpenAI のレスポンスがパース不能でスコアが取れない
  - モジュールはパース失敗時に 0.0 を返すフェイルセーフを持ちます。ログを確認し、APIキー・モデル利用制限・レスポンス形式を確認してください。
- DuckDB のテーブルがない / スキーマ初期化したい
  - 監査ログ用は `init_audit_schema` / `init_audit_db`、その他のスキーマ初期化はプロジェクトの schema 初期化ユーティリティを参照してください（リポジトリの別モジュールに存在する可能性があります）。

---

## 貢献・ライセンス

この README では記述していませんが、貢献する場合は PR と Issue を通じてお願いします。ライセンス情報はリポジトリルートの LICENSE を参照してください。

---

必要なら、具体的な実行スクリプト例・Docker 化・CI 設定テンプレート・.env.example を追加で作成できます。どの情報を優先して追加しますか？
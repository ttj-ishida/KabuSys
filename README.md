# KabuSys

日本株向けのデータ基盤・リサーチ・AI支援・監査を備えた自動売買補助ライブラリ群です。  
このリポジトリは主に以下の領域をカバーします。

- データETL（J-Quants からの株価・財務・カレンダー取得）
- ニュース収集・NLP による銘柄センチメント算出
- LLM を用いたマクロセンチメントと市場レジーム判定
- ファクター計算・特徴量探索（リサーチ用）
- データ品質チェック
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- kabuステーション等への発注層のための設定管理 など

## 主な機能一覧

- 環境変数 / .env 自動ロードと Settings（kabusys.config）
- J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB への冪等保存
- ETL パイプライン（差分取得・バックフィル・品質チェック）: data.pipeline.run_daily_etl など
- ニュース収集（RSS）: data.news_collector.fetch_rss、テキスト前処理
- ニュース NLP（銘柄ごとのセンチメント）: ai.news_nlp.score_news（OpenAI）
- 市場レジーム判定: ai.regime_detector.score_regime（ETF 1321 とマクロニュースの組合せ）
- 研究用ファクター計算・統計ユーティリティ: research.*（momentum/value/volatility、zscore_normalize 等）
- データ品質チェック: data.quality.run_all_checks（欠損・スパイク・重複・日付不整合）
- 監査ログ初期化 / DB: data.audit.init_audit_schema / init_audit_db
- DuckDB によるオンプレ DB ファイル管理（デフォルト path を設定可能）

## セットアップ手順

前提
- Python 3.9+（コード中で typing の新表記を使用）
- system に pip があること

1. リポジトリをクローン（またはパッケージ化された形で配置）
2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows (PowerShell では別コマンド)
   ```
3. 依存パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   必要に応じて他パッケージ（urllib 等は標準）を追加してください。

4. 開発時インストール（ローカル編集を反映する場合）
   ```bash
   pip install -e .
   ```
   （setup.py / pyproject.toml がある前提での開発インストール）

5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config）。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数（必須のもの、デフォルト有りのものを含む）
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 呼び出し時に省略可）
     - KABU_API_PASSWORD (必須) — kabu API 用パスワード
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）

   .env の書式は shell の KEY=VALUE や export KEY=VALUE に対応し、クォートやコメントの扱いも考慮されています。

## 使い方（主要な例）

以下は各主要機能の簡単なコード例です。実行前に必要な環境変数（APIキー類）を設定してください。

1) Settings の利用（設定値の読み出し）
```python
from kabusys.config import settings

print(settings.duckdb_path)  # Path object
print(settings.env)          # development / paper_trading / live
token = settings.jquants_refresh_token  # J-Quants リフレッシュトークン
```

2) DuckDB 接続を開いて日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しないと今日が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントのスコア生成（OpenAI API 必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を None にすると環境変数 OPENAI_API_KEY が使われます
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("書き込んだ銘柄数:", n_written)
```

4) 市場レジーム判定（ETF 1321 とマクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

5) 監査ログ用スキーマの初期化 / 専用 DB を作成する
```python
from kabusys.data.audit import init_audit_db, init_audit_schema
import duckdb
from pathlib import Path

# 監査専用ファイルを初期化して接続を得る
conn = init_audit_db(Path("data/audit.duckdb"))

# 既存接続に対してスキーマを追加する場合
conn2 = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn2, transactional=True)
```

6) J-Quants API を直接使う（トークン取得 / データ取得）
```python
from kabusys.data import jquants_client as jq

# id_token を取得（内部で settings.jquants_refresh_token を参照）
id_token = jq.get_id_token()

# 株価取得（ページネーション対応）
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,20))

# DuckDB 接続と save を使って保存
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)
```

7) RSS フィードの取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, preprocess_text

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], preprocess_text(a["content"]))
```

注意点:
- OpenAI 呼び出し (score_news / score_regime) は API のネットワーク障害やレート制限を想定したリトライロジックを備えていますが、APIキーの設定が必要です。
- ETL / データ保存は DuckDB を想定しています。初回はスキーマが必要（プロジェクト内の schema 初期化処理を実行してください）。

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env 自動ロードと Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（OpenAI）と score_news
  - regime_detector.py — マクロ + MA で市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集・前処理
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログスキーマ初期化と専用 DB 作成
- research/
  - __init__.py
  - factor_research.py — momentum / value / volatility 等
  - feature_exploration.py — 将来リターン / IC / 統計サマリー等

ドキュメント・設計上の注意は各モジュールの docstring に詳細が記載されています。

## 運用上の注意 / ベストプラクティス

- 環境変数はプロジェクトルートの .env / .env.local を利用することが想定されています（自動読み込み）。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして手動で値を注入してください。
- LLM / OpenAI を用いる処理は API コストが発生します。必要な場合は api_key を引数で注入して呼び出し元で管理してください。
- ETL は差分更新・バックフィルの仕組みがありますが、初回ロード時には十分な過去日付（J-Quants 提供範囲）を指定してください。
- DuckDB ファイルやローカル DB の配置・バックアップは運用ポリシーに合わせて行ってください（デフォルトは data/ 以下）。
- 監査ログは削除しない前提です。ディスク容量に注意してください。

---

README に記載の使い方は、ライブラリの公開 API（各モジュールの関数）を直接利用する例です。より詳しいパラメータや戻り値の仕様は各モジュールの docstring を参照してください。追加で README に載せたい具体例（CLI、Docker、CI の設定など）があれば教えてください。
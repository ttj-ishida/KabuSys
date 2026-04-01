# KabuSys

KabuSys は日本株の自動売買およびデータプラットフォームのためのライブラリ群です。  
DuckDB をデータレイクとして用い、J-Quants API からのデータ取得、ニュース収集・NLP によるセンチメント解析、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを備えています。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants からの日次株価（OHLCV）・財務データ・市場カレンダーの差分取得と DuckDB への冪等保存（ETL パイプライン）。
  - 品質チェック（欠損、スパイク、重複、日付不整合）の自動検出。
- ニュース収集・NLP
  - RSS フィードからのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事IDの正規化）。
  - OpenAI を用いた銘柄別ニュースセンチメント（ai.score_news）とマクロセンチメントを組み合わせた市場レジーム判定（ai.score_regime）。
- リサーチ（ファクター算出）
  - Momentum / Volatility / Value 等のファクター計算と特徴量解析（forward returns、IC、統計サマリー）。
  - Zスコア正規化ユーティリティ。
- 監査・実行ログ
  - signal → order_request → executions の階層で完全にトレース可能な監査テーブル群と初期化ユーティリティ。
  - 監査用 DuckDB 初期化 helper（init_audit_db / init_audit_schema）。
- インフラ関連
  - 環境設定一元管理（.env の自動ロード、Settings クラス）。
  - kabu ステーション API / Slack など接続先の設定を環境変数で管理。
  - カレンダー管理・営業日判定ユーティリティ。

---

## 必要条件（依存関係）

最低限の依存例（実際の pyproject.toml / requirements.txt を参照してください）：
- Python 3.10+
- duckdb
- openai
- defusedxml

その他、標準ライブラリ（urllib, json, logging 等）を使用します。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージのインストール
   - pyproject.toml / requirements.txt がある想定で：
     ```
     pip install -e .
     ```
     または最小依存を直接：
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml 配下）に `.env` / `.env.local` を置くと、自動的にロードされます（起動時に自動ロードされる。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須の主要環境変数（一部）：
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuAPI パスワード
     - SLACK_BOT_TOKEN — Slack Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API Key（ai モジュールで使用）
   - 任意の設定：
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development/paper_trading/live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

   例 `.env`（参考）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 初期化（監査 DB 例）

監査ログ用の DuckDB を作成してスキーマを初期化する例:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" でメモリ DB も可
# conn は duckdb.DuckDBPyConnection
```

または既存接続に対してスキーマを追加する場合:

```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 使い方（主な API 例）

以下は代表的なモジュールの利用例です。すべて DuckDB の接続（duckdb.connect(...)）を渡して使います。

- 日次 ETL を実行（prices / financials / calendar を差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成（OpenAI API が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"written {n_written} scores")
```

- 市場レジーム判定（MA とマクロニュースの LLM スコアを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- リサーチ（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- カレンダーユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- RSS フィードの取得（news_collector）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- J-Quants クライアント（トークン取得 / データ取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()
records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
```

---

## 環境設定の自動ロードについて

- config.py はプロジェクトルート（.git または pyproject.toml）を基準に `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する場合は環境変数を設定:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```
- Settings クラスからアプリ内で設定を参照できます:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

---

## ディレクトリ構成（抜粋）

以下はパッケージ内部の主要ファイル・モジュールです（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（銘柄別スコアリング）
    - regime_detector.py     — マクロ＋MA による市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py            — ETL パイプライン（run_daily_etl など）
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS 収集
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - audit.py               — 監査（signal/order_request/executions）スキーマ
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - etl.py                 — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — forward returns, IC, factor summary
  - research/*, data/*, ai/* など多くの補助関数とユーティリティが含まれます。

---

## 開発上の注意事項 / 設計上のポイント

- ルックアヘッドバイアス防止のため、各モジュールは内部で datetime.today() や date.today() を不用意に参照しない設計です。関数は target_date を明示的に受け取ることが推奨されます。
- OpenAI 呼び出しは JSON Mode（厳密な JSON を期待）とし、API エラーや不正レスポンス時はフェイルセーフとしてゼロやスキップで継続する実装です（例: macro_sentiment = 0.0）。
- DuckDB への書き込みは可能な限り冪等（ON CONFLICT DO UPDATE）を採用しています。
- news_collector は SSRF 対策（ホスト検査、リダイレクト検査）やレスポンスサイズ上限等の防御を組み込んでいます。

---

## ライセンス / コントリビューション

本リポジトリ内に LICENSE ファイルがある場合はそちらを参照してください。コントリビューション方針や issue / PR の運用はリポジトリの CONTRIBUTING.md を参照してください（存在する場合）。

---

README に含めるべき追加情報（例: CI / テスト実行方法、詳細な設定例、デプロイ手順等）があれば指示をください。必要に応じてサンプル .env.example やユニットテストの実行方法も追記します。
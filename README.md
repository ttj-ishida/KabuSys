# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤のコアライブラリです。  
DuckDB を用いたデータ ETL、ニュース収集・NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）などを提供します。研究（Research）用途と本番運用の両方を想定した設計で、Look‑ahead バイアス対策・冪等性・堅牢なリトライ制御を重視しています。

バージョン: 0.1.0

---

## 主な機能

- 環境設定管理（.env の自動読み込み、必須環境変数検証）
- J‑Quants API クライアント（株価・財務データ・マーケットカレンダー取得、DuckDB への冪等保存）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS -> 前処理 -> raw_news に保存する設計）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコアリング）
- 市場レジーム判定（ETF（1321）MA とマクロニュースセンチメントの合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）
- 研究支援ユーティリティ（将来リターン計算、IC、統計サマリー、Zscore 正規化）
- カレンダー管理（JPX カレンダー取得 / 営業日判定 / next/prev_trading_day）
- データ品質チェック（欠損／スパイク／重複／日付整合性）
- 監査ログ（signal → order_request → executions のトレーサビリティを担保する監査スキーマ）

---

## 必要条件 / 依存ライブラリ（代表例）

- Python 3.9+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, logging など）

（実際の requirements.txt がある場合はそちらを使ってください。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。以下は代表的な例）
   ```
   pip install duckdb openai defusedxml
   ```

4. パッケージをインストール（開発モード）
   ```
   pip install -e .
   ```

---

## 環境変数 / .env

kabusys は .env（プロジェクトルート）および .env.local を自動で読み込みます（優先度: OS 環境変数 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）、デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト `INFO`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト `data/monitoring.db`）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 呼び出し時に使用）

設定はコード上で以下のように参照できます:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

環境変数のパースはシェル形式（export KEY=val、コメント、クォート、エスケープ）に対応しています。

---

## 使い方（代表例）

以下は主要な関数の利用例です。すべて Python スクリプトや REPL から呼び出せます。

- DuckDB 接続を開く
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ったニューススコアリング（ai/news_nlp.score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

- 市場レジーム（ai/regime_detector.score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db はテーブルとインデックスを作成します
```

- RSS フィードのフェッチ（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意:
- OpenAI 呼び出しはモデル `gpt-4o-mini` を前提とした JSON Mode を使用します。API キーは `OPENAI_API_KEY` で設定するか、関数引数に渡してください。
- ETL / 保存処理は DuckDB のスキーマが事前に用意されていることが前提です。schema 初期化関数が別途ある場合はそれを使用してください（本リポジトリの該当部分を参照ください）。

---

## 代表的なモジュールと責務

- kabusys.config
  - 環境変数・.env 読み込み、settings オブジェクトの提供
- kabusys.data
  - jquants_client: J‑Quants API からの取得・DuckDB への保存
  - pipeline: ETL の統合実行（run_daily_etl, run_prices_etl 等）
  - news_collector: RSS 取得・前処理（SSRF 対策、gzip 対応）
  - calendar_management: 市場カレンダー管理 / 営業日ロジック
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - stats: Zスコア正規化などの統計ユーティリティ
  - audit: 監査ログスキーマの初期化 / audit DB ユーティリティ
- kabusys.ai
  - news_nlp: ニュースを銘柄ごとに集約して LLM でスコアリング
  - regime_detector: ETF の MA とマクロニュースを重み付けして市場レジームを判定
- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー等の定量ファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー

（上記は主要なファイルに対応する一覧です。実際のディレクトリ構成は下記参照）

---

## ディレクトリ構成（抜粋）

プロジェクトのルートに `src/kabusys` があり、主なファイルは以下の通りです:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__pycache__...（省略）

（上記に加えて strategy, execution, monitoring といった名前空間が __init__ で公開されていますが、本 README のコード抜粋では一部のみ示されています。）

---

## 開発 / テスト時のヒント

- 自動で .env をロードしますが、ユニットテストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを抑止できます。
- OpenAI や J‑Quants への外部 API 呼び出しは、各モジュールで内部呼び出し関数が分離されており、unittest.mock.patch による差し替えが想定されています（テスト容易性のため）。
- DuckDB を使ったユニットテストでは `":memory:"` を使ってインメモリ DB を生成できます（data.audit.init_audit_db 等は対応しています）。

---

## 参考 / 注意事項

- Look‑ahead バイアス防止のため、target_date の計算は外部から与えられ内部で date.today() を直接参照しない実装方針が採られています。
- OpenAI のレスポンスは JSON Mode を期待しており、レスポンスパースに失敗した場合はフェイルセーフで中立値（0.0 など）にフォールバックする設計です。
- J‑Quants の API 制限やネットワークエラーに対してはリトライ・レート制限（固定スロットリング）を実装しています。

---

必要であれば、README に CI / デプロイ手順、実運用の監視・アラート設定例、Docker 化手順、サンプル .env.example のテンプレートも追加で作成できます。どの情報をさらに強化したいか教えてください。
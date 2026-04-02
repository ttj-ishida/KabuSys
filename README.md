# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、市場レジーム判定、研究用ファクター計算、監査ログ（発注〜約定トレーサビリティ）などを含むモジュール群を提供します。

主な設計方針：
- DuckDB を中心としたローカルデータプラットフォーム（ETL → 品質チェック → 研究/戦略）
- 外部 API 呼び出しはレート制御・リトライ・フェイルセーフを備える
- バックテストでのルックアヘッドバイアスを排除する実装
- DB 書き込みは冪等（idempotent）を重視

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数、認証・レート制御・リトライ）
  - 市場カレンダー管理（営業日判定、次/前営業日取得、カレンダー更新ジョブ）
  - ニュース収集（RSS → raw_news、SSRF 対策、URL 正規化）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化（監査テーブル / インデックスの作成、init_audit_db）
  - 統計ユーティリティ（zscore 正規化など）
- ai/
  - ニュースセンチメント解析（score_news：OpenAI を使った銘柄別スコア）
  - 市場レジーム判定（score_regime：ETF の MA とマクロニュースの組合せ）
  - OpenAI 呼び出しは JSON Mode を使用、失敗時はフェイルセーフで継続
- research/
  - ファクター計算（momentum / volatility / value）
  - 特徴量解析ユーティリティ（forward returns, IC, summary, ranking）
- config.py
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定のラッパー（settings オブジェクト）
  - KABUSYS_ENV (development / paper_trading / live) や LOG_LEVEL 等の検証

---

## 要件（推奨）

- Python 3.10+
- 必須パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

（プロジェクトの pyproject.toml / requirements.txt がある前提でそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージをインストール
   - pip install -e .        # pyproject.toml がある場合（開発インストール）
   - または requirements.txt があれば: pip install -r requirements.txt
   - 直接依存を入れるなら例: pip install duckdb openai defusedxml
4. 環境変数／.env を用意
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可）。
   - 必須キー（config.Settings で必須となるもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 推奨／任意
     - OPENAI_API_KEY（score_news / score_regime 実行時に引数でも渡せます）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視データ等、デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/...）
5. データディレクトリの作成（必要なら）
   - mkdir -p data

.env の例（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXX
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

セキュリティ注意：API トークンはリポジトリにコミットしないでください。

---

## 使い方（簡易ガイド）

以下は Python スクリプト内から利用する例です。適宜ロギング設定や例外処理を追加してください。

- DuckDB 接続を作り ETL を実行する（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースをスコア化して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> env OPENAI_API_KEY を使用
print("written:", n_written)
```

- 市場レジーム判定（market_regime テーブルへ書込）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# テーブルが作成され、UTC タイムゾーンに設定されます
```

- ニュース RSS を取得（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

主な API の挙動（重要ポイント）
- OpenAI 呼び出しに失敗した場合、スコア処理は基本的に例外を投げずフェイルセーフ（0.0）で継続する設計箇所が多いです（score_news / score_regime など）。
- ETL、保存処理は冪等設計（INSERT ... ON CONFLICT DO UPDATE）です。
- 時刻・日付の扱いは Look-ahead バイアスを避けるために外部引数（target_date）に依存し、内部で date.today() を直接参照しない設計が基本です。

---

## 主要モジュールと代表 API

- kabusys.config
  - settings: 環境変数をラップする単一インスタンス
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.news_collector
  - fetch_rss, preprocess_text
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, ...
- kabusys.data.audit
  - init_audit_schema, init_audit_db
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

---

## ディレクトリ構成

（src 配下を想定）

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
    - (その他監査/ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/, strategy/, execution/ など（パッケージ __all__ に含まれる想定）

各モジュールは README や docstring に処理フロー・設計方針が詳細に記載されています。実装上の注意点（トークンリフレッシュ、リトライ、レート制御、フェイルセーフ、ルックアヘッドバイアス対策、冪等性など）は各モジュールの docstring を参照してください。

---

## 運用上の注意

- API キー・トークンは秘匿してください（.env を gitignore に追加）。
- OpenAI / J-Quants の課金／レート制限に注意してください（jquants_client には 120 req/min の制御あり）。
- 本コードベースは本番発注（実際の売買）に使う場合、十分なレビューと安全対策（リスク管理、二重発注防止、テスト）が必要です。KABUSYS_ENV を適切に設定してください（live は実売買用）。
- DuckDB の schema 初期化・マイグレーションは運用手順を別途作成してください（audit.init_audit_db や各 ETL は既存テーブルを前提とします）。

---

必要であれば、README に CI / テストの実行方法、より詳細な設定例、運用手順（cron/ジョブスケジューリング、監視 Slack 連携例）を追加できます。どの情報を優先して追記するか教えてください。
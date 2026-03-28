# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）→ ETL → 品質チェック → ファクター算出 → AIによるニュース評価 → 監査ログ／発注フロー といった一連の機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群を含む Python パッケージです。

- J-Quants API からの株価・財務・カレンダー等の差分取得（レート制御・リトライ・トークンリフレッシュ対応）
- DuckDB を利用した ETL パイプライン（差分取得、冪等保存、品質チェック）
- ニュース収集（RSS）、前処理、記事と銘柄の紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / 市場レジーム判定
- 研究（リサーチ）用のファクター計算・特徴量解析ユーティリティ
- マーケットカレンダー管理（営業日判定等）
- 監査（audit）用スキーマの初期化・管理（シグナル→発注→約定のトレーサビリティ）
- 環境変数ベースの設定管理・自動 .env ロード

設計上の特徴：
- ルックアヘッドバイアスに配慮（内部で date.today()/datetime.today() を直接参照しない設計が多い）
- DuckDB を主要データストアとして利用
- 冪等性・フェイルセーフ・リトライ戦略を重視

---

## 主な機能一覧

- data/jquants_client: J-Quants API クライアント（fetch / save / id_token 管理）
- data/pipeline: ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- data/news_collector: RSS フィード取得・前処理・raw_news 保存ロジック
- data/quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- data/calendar_management: 市場カレンダー管理、営業日判定ユーティリティ
- data/audit: 監査ログ（signal_events / order_requests / executions）スキーマの初期化
- ai/news_nlp: ニュースを銘柄別にまとめて LLM でスコア化し ai_scores に保存
- ai/regime_detector: ETF（1321）MA200乖離とマクロニュースの LLM スコアを合成して市場レジーム判定
- research/*: ファクター計算（momentum / value / volatility 等）・特徴量解析・統計ユーティリティ
- config: .env / 環境変数の読み込み・settings オブジェクト（必要な環境変数の getter）

---

## 必要条件

- Python 3.10+
- 主な依存パッケージ（少なくとも以下）:
  - duckdb
  - openai
  - defusedxml

※ その他、標準ライブラリ以外の追加依存が必要になる可能性があります（運用環境に応じて追加）。

例（開発環境に最低限インストールする例）:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows

3. パッケージと依存関係をインストール
   pip install -e .    # setup.py/pyproject がある場合
   または必要パッケージを個別にインストール:
   pip install duckdb openai defusedxml

4. 環境変数設定 (.env)
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   必須環境変数の例:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb         # 任意（デフォルト）
   SQLITE_PATH=data/monitoring.db          # 任意（デフォルト）
   KABUSYS_ENV=development                 # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   注意:
   - config.Settings で必須とされている値は起動時に参照されるため、適切に設定してください。
   - テスト時に自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡易サンプル）

以下は主要な機能の利用例です。実際は logger の設定やエラーハンドリング等を組み合わせてください。

- DuckDB 接続を用意して ETL を実行する:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアの生成（ai/news_nlp.score_news）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（ai/regime_detector.score_regime）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

- 監査DBスキーマを初期化する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリ自動作成
```

- RSS を取得する（ニュースコレクタのユーティリティ）:

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム検出で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系で使用）
- KABU_API_BASE_URL: kabu ステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用
- DUCKDB_PATH / SQLITE_PATH: 各種 DB ファイルパス（デフォルト値あり）
- KABUSYS_ENV: 実行環境 ("development", "paper_trading", "live")
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

config.Settings によって getter が提供されています。未設定で必須な場合は起動時に ValueError を投げます。

---

## ディレクトリ構成（主要ファイル）

（パッケージは `src/kabusys` 配下）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント / ai_scores 書込
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + 保存ロジック
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult の再エクスポート
    - news_collector.py              — RSS 収集・前処理
    - quality.py                     — データ品質チェック
    - calendar_management.py         — 市場カレンダー管理・営業日判定
    - audit.py                       — 監査テーブル定義・初期化
    - stats.py                       — 統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py             — momentum, value, volatility 等
    - feature_exploration.py         — forward returns, IC, summary, rank 等

---

## 開発・テストについて

- モジュール内部にはテスト用に差し替えが可能な箇所（HTTP/LLM 呼び出しのラッパー）があります（例: news_nlp._call_openai_api / regime_detector._call_openai_api / news_collector._urlopen など）。ユニットテストでは unittest.mock.patch を使って差し替え、外部依存をモックできます。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 注意事項 / 運用上のヒント

- OpenAI 呼び出しや外部 API 呼び出しはレート制限・課金が発生します。開発時は少量でのテスト、またはモックを使用してください。
- ETL は差分取得・backfill を行いますが、初回ロードや大規模なバックフィルでは時間とストレージを消費します。DuckDB ファイルのバックアップや管理を考慮してください。
- KABUSYS_ENV を `live` に設定すると実際の発注や本番設定を示唆する処理が有効になる可能性があるため、設定は慎重に行ってください。

---

もし README に追記したい使用例（cron スケジュールでの ETL 実行、Slack 通知の例、Kabu ステーションとの発注連携など）があれば、利用シナリオに合わせてサンプルを追加します。
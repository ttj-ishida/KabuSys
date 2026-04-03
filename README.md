# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、リサーチ用ファクター計算、監査ログ（発注 → 約定のトレーサビリティ）、および運用用設定管理を提供します。

バージョン: 0.1.0

---

## 主な特徴（概要）

- J-Quants API 経由の差分 ETL（株価・財務・カレンダー）および品質チェック
- DuckDB をデータストアとして使用する idempotent な保存ロジック
- ニュース収集（RSS）＋記事前処理（SSRF 対策、URL 正規化）＋OpenAI を使った銘柄単位のセンチメントスコア化
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成）
- リサーチ向けファクター計算（モメンタム、バリュー、ボラティリティ等）と関連統計ユーティリティ
- 監査ログスキーマ（signal_events / order_requests / executions）の初期化ユーティリティ
- 実行環境設定の .env / 環境変数読み込み機能（プロジェクトルート自動検出）
- フェイルセーフ設計（API エラー時に処理継続、LLM 失敗時は 0.0 にフォールバック など）

---

## 機能一覧（モジュール別ハイレベル）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート基準）
  - 環境設定のプロパティアクセス（JQUANTS_REFRESH_TOKEN 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得＋DuckDB 保存）
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL ジョブ
  - news_collector: RSS 取得・前処理・保存補助（SSRF 対策）
  - calendar_management: 市場カレンダー操作（営業日判定等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等汎用統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを使った銘柄別センチメント生成（OpenAI）
  - regime_detector.score_regime: 市場レジーム判定（MA200 + マクロセンチメント）
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## 必須・推奨環境

- Python 3.10+（型注釈 Path | None 等を使用）
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS XML の安全なパース）
- その他標準ライブラリ（urllib, json, logging 等）

推奨パッケージ（最低限）
- duckdb
- openai
- defusedxml

requirements.txt を用意している場合はそちらを利用してください（本リポジトリではサンプルを示していません）。

---

## セットアップ手順

1. Python 環境を用意（venv 推奨）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール

   例（pip）:

   ```bash
   pip install duckdb openai defusedxml
   ```

   実行パッケージがある場合はプロジェクトルートで:

   ```bash
   pip install -e .
   ```

3. 環境変数の設定（.env / 環境変数いずれでも可）

   必要な主な環境変数（一部既定値あり）:

   - JQUANTS_REFRESH_TOKEN (必須)  
     → J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
   - OPENAI_API_KEY (必須: AI 機能を使う場合)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知等に使用)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

   サンプル .env.example（README 用例）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_pass
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. 自動 .env 読み込みの無効化（テスト時）
   - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

---

## 使い方（代表例）

以下は Python スクリプト / REPL からの利用例です。実際の運用ではこれらをスケジューラやサービスに組み込んでください。

1) DuckDB 接続を作成して日次 ETL を実行（run_daily_etl）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェックの順で実行し、ETLResult を返します。

2) ニュースに基づく銘柄別スコア生成（OpenAI 必須）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数で設定するか、api_key 引数に渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```

- LLM 呼び出しに失敗した場合は安全にフォールバックし、取得できた銘柄のみを ai_scores に書き込みます。

3) 市場レジーム判定

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で渡します。API エラー時は macro_sentiment=0.0 にフォールバックします。

4) 監査ログ（audit）スキーマの初期化

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済み DuckDB 接続。以降監査テーブルにレコードを書き込めます。
```

5) RSS の取得（news_collector）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- fetch_rss は SSRF 対策、サイズ制限、XML 安全処理を行います。

---

## 実装上の注意点 / 設計ポリシー（運用向け）

- Look-ahead bias の厳格排除: 日付計算は target_date を明示的に渡す方針。datetime.today() を不用意に参照しません。
- LLM 呼び出しのフェイルセーフ: API エラーやレスポンス不整合時は例外を投げずスコアを 0.0 にするか、そのチャンクをスキップして継続します。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装されています。
- J-Quants API クライアントにはレートリミッタと再試行（指数バックオフ）実装あり。401 は自動リフレッシュ対応。
- news_collector は SSRF 対策（リダイレクト検査 / プライベートアドレス拒否）や XML の安全パーサを採用しています。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を起点）を探して行います。不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要モジュールを抜粋）

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
    - audit.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールの役割はコード中の docstring に詳細な説明があります。実装と使い方は docstring を参照してください。

---

## ロギング / 環境

- LOG_LEVEL 環境変数でログレベルを制御（デフォルト INFO）。
- KABUSYS_ENV により環境判定（development / paper_trading / live）。settings.is_live 等で判定可能。

---

## テスト・開発時のヒント

- OpenAI / J-Quants の API 呼び出しはモック可能に設計されています（内部の _call_openai_api 等を unittest.mock.patch で差し替え）。
- ETL や保存処理は DuckDB のファイルを指定してローカルで繰り返し検証できます（":memory:" を使用してインメモリ DB も可）。
- 自動 .env 読み込みを無効化して、テスト用に環境変数を明示的にセットしてください。

---

必要に応じて README にサンプル .env.example、開発用の requirements.txt、簡単な CLI ラッパー（ETL やニューススコア処理を定期実行するスクリプト）を追加できます。README の補足やサンプル追加を希望される場合は、どの例を追加したいか教えてください。
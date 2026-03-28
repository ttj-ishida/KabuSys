# KabuSys

日本株向けの自動売買（リサーチ・データプラットフォーム）ライブラリ。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、特徴量（ファクター）計算、LLM を用いたニュースセンチメント / 市場レジーム判定、監査ログ等のユーティリティを含みます。

---
## 主要な特徴（機能一覧）
- 環境設定読み込み（.env / .env.local / OS 環境変数）
  - 自動ロード順序: OS > .env.local > .env
  - 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API クライアント
  - 株価日足、財務データ、上場銘柄情報、JPX カレンダー取得
  - レートリミット制御・リトライ・トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - run_daily_etl によるカレンダー / 株価 / 財務の差分取得 + 品質チェック
  - ETL 結果を ETLResult として取得
- ニュース収集
  - RSS フィード取得（SSRF / gzip / XML 諸対策）
  - raw_news / news_symbols への冪等保存（ID は正規化 URL の SHA-256）
- ニュース NLP（OpenAI）
  - 銘柄ごとニュースをまとめて LLM（gpt-4o-mini）に投げるバッチ処理
  - 出力バリデーション・スコアクリップ・リトライ
  - API キーは引数 or 環境変数 `OPENAI_API_KEY`
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成して日次判定
  - レジーム（bull / neutral / bear）を market_regime テーブルに冪等書き込み
- 研究用途ユーティリティ
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - zscore_normalize 等の統計ユーティリティ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue）
- 監査ログ（audit）
  - Signal → OrderRequest → Execution のトレース可能なスキーマ初期化ユーティリティ
  - init_audit_db で監査用 DuckDB を初期化

---
## 前提 / 依存
主に次のパッケージを利用します（プロジェクトの pyproject.toml / requirements を参照してください）:
- Python 3.9+（型注釈に union 型等を使用）
- duckdb
- openai（OpenAI の Python SDK）
- defusedxml
- （標準ライブラリ：urllib, json, logging 等）

---
## セットアップ手順（ローカル開発）
1. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール（プロジェクトルートに pyproject.toml または setup がある想定）
   - pip install -e .[dev]  または pip install -r requirements.txt
   ※ requirements は各自のプロジェクト構成に合わせて下さい。

3. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（読み込み順は OS > .env.local > .env）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベース用ディレクトリ作成（例）
   - mkdir -p data

---
## 使い方（例 / API）
以下は代表的なユースケースの例です。実際はログ出力や例外処理を追加してください。

- DuckDB へ接続して日次 ETL を走らせる
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ってニューススコアを計算（ai.news_nlp.score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は env にセット可
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定を行う（ai.regime_detector.score_regime）
```python
from kabusys.ai.regime_detector import score_regime
# conn は duckdb connect
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル群が作成されます
```

- RSS 取得（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意:
- OpenAI 呼び出しは API レートやコストがあります。api_key を引数で上書くことも可能です。
- run_daily_etl 等の関数は DuckDB 上のテーブルスキーマを前提とします（スキーマ初期化はプロジェクトの schema 初期化ツールを参照してください）。

---
## 環境変数 / .env の例（.env.example）
```text
# J-Quants
JQUANTS_REFRESH_TOKEN=YOUR_JQUANTS_REFRESH_TOKEN

# OpenAI
OPENAI_API_KEY=YOUR_OPENAI_API_KEY

# Kabu ステーション（オプション）
KABU_API_PASSWORD=...

# Slack 通知（オプション）
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...

# システム
KABUSYS_ENV=development
LOG_LEVEL=INFO

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---
## 実装上の注意点（設計方針の要約）
- Look-ahead bias 回避: 日付関連ロジックは内部で date.today() を不用意に参照せず、明示的な target_date を受け取る形で設計されています。
- 冪等性: ETL / 保存処理は可能な限り冪等（ON CONFLICT）で実装されています。
- フェイルセーフ: LLM 呼び出しや外部 API が失敗した場合、例外直帰ではなくフォールバック（例えばスコア 0.0）して処理継続する設計の箇所が多くあります。
- テスト容易性: OpenAI 等の外部呼び出しをラップしており unittest.mock で差し替え可能です。

---
## ディレクトリ構成（概要）
以下は主なモジュールとファイルの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      （環境変数・.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                   （ニュースセンチメント）
    - regime_detector.py            （市場レジーム判定）
  - data/
    - __init__.py
    - jquants_client.py             （J-Quants API クライアント）
    - pipeline.py                   （ETL パイプライン & run_daily_etl）
    - etl.py                        （ETLResult エクスポート）
    - news_collector.py             （RSS 収集）
    - calendar_management.py        （マーケットカレンダー管理）
    - stats.py                      （統計ユーティリティ）
    - quality.py                    （データ品質チェック）
    - audit.py                      （監査ログスキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py            （Momentum/Value/Volatility 等）
    - feature_exploration.py        （forward returns / IC / summary）
  - (strategy/, execution/, monitoring/ 等のトップレベルパッケージを公開可能)

プロジェクトルートには通常 pyproject.toml（または setup.py）、.env.example、README.md、tests/ 等が存在します。

---
## 貢献・開発
- バグ報告・機能提案は issue を作成してください。
- 開発ルールやテストの詳細は CONTRIBUTING.md（ある場合）を参照してください。
- 自動ロードされる .env のパースは config._parse_env_line に実装されています。CI/テストで自動ロードを抑制したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定してください。

---
以上が本リポジトリの README.md（日本語）です。必要であれば使用例のコードや初期スキーマ作成手順（DuckDB のテーブル DDL）を追記します。どの部分を詳しく書き加えるか教えてください。
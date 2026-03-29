# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター/リサーチ、監査ログ（発注→約定のトレーサビリティ）などのユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援する内部ライブラリ群です。主な目的は以下です。

- J-Quants API からのデータ取得（株価・財務・カレンダー）
- DuckDB を用いたローカルデータプラットフォーム（ETL パイプライン・品質チェック）
- ニュース収集（RSS）と OpenAI を用いた記事レベル / 銘柄レベルセンチメント評価
- 市場レジーム判定（ETF とマクロニュースを組み合わせた判定）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）テーブル初期化ユーティリティ

設計上の注意点として、バックテスト等でのルックアヘッドバイアスを避けるために、関数は日付を明示的に受け取り `date.today()` や `datetime.today()` に依存しないようにしています。

---

## 機能一覧

- データ (kabusys.data)
  - J-Quants クライアント（fetch / save）
  - ETL パイプライン（run_daily_etl / run_prices_etl / ...）
  - 市場カレンダー管理（is_trading_day, next_trading_day, calendar_update_job）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS -> raw_news）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- AI (kabusys.ai)
  - ニュース NLP（score_news：銘柄ごとのセンチメントを ai_scores に書き込む）
  - レジーム判定（score_regime：ETF MA とマクロニュースを合成して market_regime に書き込む）
- Research (kabusys.research)
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（forward returns, IC, 統計サマリー等）
- 環境管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ユーティリティ

---

## 前提 / 要件

- Python 3.10 以上（PEP604 の union 型 `X | Y` を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース、OpenAI API）およびローカルファイル書き込み権限

（プロジェクト用の requirements.txt がある場合はそちらを利用してください。上記はコードから推測される主要依存です）

---

## インストール（ローカルでの開発例）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. パッケージを開発インストール（任意）
   - pip install -e .

---

## 環境変数 / .env

kabusys.config.Settings によって以下の環境変数を読み込みます。`.env` / `.env.local` をプロジェクトルートに置くと自動で読み込まれます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化可能）。

必須（実行する機能に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（使用する場合）
- SLACK_BOT_TOKEN — Slack 通知を利用する場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意:
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- OPENAI_API_KEY — OpenAI を使用する場合（関数引数としても渡せます）

例（プロジェクトルートの .env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxx
SLACK_BOT_TOKEN=xoxb-yyy
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: `.env.local` が存在すると `.env` の設定を上書きします（OS 環境変数はさらに優先されます）。

---

## セットアップ手順（データベース初期化 など）

1. DuckDB コネクションを作成（デフォルトパスは settings.duckdb_path）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

2. 監査ログ専用 DB を初期化（監査テーブルの作成）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db(settings.duckdb_path)  # もしくは別ファイルパス
```

3. ETL の初回実行（J-Quants からデータを取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

---

## 使い方（代表的な API / 実行例）

- 日次 ETL（価格・財務・カレンダーの差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
res = run_daily_etl(conn, target_date=date(2026,3,20))
print(res.to_dict())
```

- ニューススコアリング（ai_scores に書き込む）
```python
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None -> env を参照
print(f"スコア付与件数: {count}")
```

- 市場レジーム判定（market_regime に書き込む）
```python
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- RSS 取得（ニュース収集のユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
print(len(records))
```

注意点:
- OpenAI の呼び出し関数は `api_key` 引数で明示的に渡すことも可能（テスト時の差し替えに便利）。
- 多くの関数は `conn: duckdb.DuckDBPyConnection` を受け取ります。DuckDB の接続を使いまわしてください。
- 一部の処理（ETL、news scoring、regime scoring）はネットワークアクセスや外部 API の呼び出しが必要です。

---

## 実行環境のヒント / 開発時の設定

- テストや静的解析で .env 自動ロードを無効にするには環境変数を設定:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しなどをユニットテストで差し替えるため、モジュール内の `_call_openai_api` や `_urlopen` を mock する設計になっています。
- DuckDB の executemany に空リストを渡すと例外になるバージョンがあるため、実装側で空チェックを行っています。

---

## ディレクトリ構成

主要なファイル / モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py              — 環境変数・設定の読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースのセンチメントスコアリング（OpenAI）
    - regime_detector.py   — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（fetch / save）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - news_collector.py    — RSS ニュース収集と前処理
    - quality.py           — データ品質チェック
    - stats.py             — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py             — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py   — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー

（上記は主要ファイルの抜粋です。詳しくは src/kabusys 以下を参照してください）

---

## 注意事項 / 設計方針の要約

- Look-ahead Bias に注意：関数は明示的な日付を要求し、未来データ参照を防ぐ実装になっています。
- フェイルセーフ：外部 API の失敗時はゼロフォールバックやスキップして継続する箇所が多く、運用途中の耐障害性を重視しています。
- 冪等性：DB への保存は可能な限り ON CONFLICT / UPDATE を使って冪等化しています。
- セキュリティ：RSS 収集では SSRF 対策や XML インジェクション対策（defusedxml）を実施しています。

---

## さらに進めるために

- CI／テスト: OpenAI / J-Quants 呼び出しは外部依存なのでユニットテストではモックしてください。
- 本番運用時は KABUSYS_ENV を `paper_trading` / `live` に切り替え、ログレベルや安全策を見直してください。
- 発注・実際のブローカー連携（kabuステーション等）を行う場合は、監査ログと冪等キー（order_request_id）を適切に生成・管理してください。

---

もし README に追記してほしい実行例（cron ジョブ例、Dockerfile、requirements.txt 形式など）があれば教えてください。必要に応じてサンプル .env.example も作成します。
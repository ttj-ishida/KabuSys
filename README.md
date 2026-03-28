# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤のライブラリ群です。  
ETL（J-Quants からの価格・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような要件を満たすことを目的としたモジュール群です。

- J-Quants API を用いた市場データ取得（株価/財務/カレンダー）
- DuckDB を利用したローカルデータストア（ETL → 保存 → 品質チェック）
- RSS を用いたニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価と市場レジーム判定
- 研究用途のファクター計算・特徴量解析ユーティリティ
- 売買フローの監査ログ（シグナル → 発注 → 約定のトレーサビリティ）

設計上、ルックアヘッドバイアス回避、冪等性、API レート制御、フェイルセーフ（API 失敗時にゼロスコア等）を重視しています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save）: rate limiting、トークン自動リフレッシュ、ページネーション対応
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - データ品質チェック（欠損、スパイク、重複、日付整合性）
  - ニュース収集（RSS → raw_news、SSRF 対策、テキスト前処理）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA200 とニュースセンチメントを合成して市場レジームを market_regime に保存
- research
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算、IC（Information Coefficient）、ファクターサマリ

---

## 必要条件（例）

- Python 3.9+
- pip
- ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml

インストール例（最低限）:
```bash
pip install duckdb openai defusedxml
# またはパッケージ化されている場合
pip install -e .
```

※実行環境によって追加パッケージ（requests 等）は不要です。上記はコード内で実際に import されている主要依存です。

---

## セットアップ手順

1. レポジトリをクローン / コピー
2. 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows
   ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # またはプロジェクトが pip パッケージ化されていれば
   pip install -e .
   ```
4. 環境変数を設定（.env または環境へ直接）
   - このリポジトリの config モジュールはプロジェクトルートの `.env` / `.env.local` を自動的に読み込みます（CWD に依存せずパッケージ位置からルートを探索）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: `.env` に設定する代表的なキー
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# kabuステーション（必要なら）
KABU_API_PASSWORD=...

# Slack（通知等で使用する場合）
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...

# データベースパス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須項目（実行する機能に応じて）:
- JQUANTS_REFRESH_TOKEN（J-Quants に対する ETL を行う場合）
- OPENAI_API_KEY（ニュースNLP / レジーム判定を行う場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知を行う場合）
- KABU_API_PASSWORD（kabuステーション連携がある場合）

---

## 使い方（基本例）

以下は Python REPL やスクリプトからライブラリ機能を利用する簡単な例です。DuckDB 接続は duckdb.connect(path) で行います。

1) ETL（デイリー ETL）を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントをスコアして ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

3) 市場レジーム判定（ETF 1321 の MA200 とニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
res = score_regime(conn, target_date=date(2026, 3, 20))
print("実行結果:", res)
```

4) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル群が作成されます
```

5) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

注意点:
- 各関数はルックアヘッドバイアス防止のため内部で date.today() 等に依存しない設計です。必ず target_date を指定するときはバックテストや実行設計に注意してください。
- OpenAI を使う関数には api_key 引数を渡すことも可能です（省略時は環境変数 OPENAI_API_KEY を参照）。

---

## 環境変数と設定（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行に必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector に必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等に必要）
- SLACK_BOT_TOKEN: Slack Bot トークン（通知）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV: 環境 ('development' / 'paper_trading' / 'live')
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化するには '1' を設定

config.Settings クラスからこれらを取得できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## ロギング設定（例）

標準ライブラリ logging を使ってレベルやハンドラを設定してください。たとえば簡易設定:
```python
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
```

---

## ディレクトリ構成

主要モジュールとファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                        # 環境変数・.env ロード設定
  - ai/
    - __init__.py
    - news_nlp.py                     # ニュース NLP（OpenAI） → ai_scores
    - regime_detector.py              # 市場レジーム判定（1321 MA200 + macro sentiment）
  - data/
    - __init__.py
    - jquants_client.py               # J-Quants API クライアント（fetch/save）
    - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
    - etl.py                          # ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py               # RSS 収集、前処理、raw_news 保存
    - calendar_management.py          # 市場カレンダー管理（is_trading_day 等）
    - quality.py                      # データ品質チェック
    - stats.py                        # zscore_normalize 等
    - audit.py                         # 監査テーブル DDL と初期化
  - research/
    - __init__.py
    - factor_research.py              # momentum/value/volatility
    - feature_exploration.py          # forward_returns / IC / summary
  - research/... (他ユーティリティ)

各モジュールは docstring に処理フロー・設計方針が詳述されており、関数レベルでの使用方法も記載されています。

---

## 注意事項 / 実運用でのチェックポイント

- API キーやトークンは漏洩しないよう運用してください。
- 本コードは ETL・研究・バックテスト用途に向けたユーティリティ群です。実際の発注ロジック（execution / broker 接続）の実装や運用ルールは別途慎重に作る必要があります。
- OpenAI へのリクエストはコストが発生します。バッチサイズやモデル選択は利用状況に合わせて調整してください。
- DuckDB のバージョンによっては executemany や型バインドの挙動が異なることがあるため、CI や稼働環境での検証を行ってください。
- 自動 .env 読み込みはプロジェクトルート（.git もしくは pyproject.toml が存在する場所）を基準に行います。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 参考

ソースコード内に詳細な docstring と設計方針が記載されています。各モジュールを参照してください:
- src/kabusys/data/pipeline.py
- src/kabusys/data/jquants_client.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/ai/regime_detector.py

---

必要であれば README にサンプル .env.example、より具体的な CLI スクリプト例、UnitTest/CI のセットアップやデプロイ手順も追加できます。どの情報を追記しましょうか？
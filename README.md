# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリです。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、特徴量計算、ニュースNLP（OpenAI）、市場レジーム判定、監査ログ（発注トレース）等の機能を提供します。

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API からの株価・財務・カレンダーの差分取得と DuckDB への保存（ETL）
- RSS ニュース収集と前処理（SSRF対策、トラッキング除去、冪等保存）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄単位、マクロ）
- 市場レジーム判定（ETF:1321 の MA200 とマクロセンチメントの合成）
- 監査ログ（シグナル → 発注 → 約定）を記録する監査DB初期化ユーティリティ
- リサーチ用ファクター計算・統計ユーティリティ（モメンタム、ボラティリティ、バリュー、IC 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

パッケージルートは `kabusys`、主要サブパッケージは `kabusys.data`, `kabusys.research`, `kabusys.ai` などです。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証、fetch / save 各種データ）
  - 市場カレンダー管理（営業日判定・次/前営業日の取得）
  - ニュース収集（RSS 取得・前処理・冪等保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（監査スキーマ初期化、専用 DB 初期化ユーティリティ）
  - 統計ユーティリティ（zscore 正規化など）
- ai
  - ニュース NLP（銘柄ごとのセンチメントスコア: score_news）
  - 市場レジーム判定（score_regime: MA200 とマクロセンチメント合成）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索 / IC / 統計サマリ（calc_forward_returns, calc_ic, factor_summary 等）
- config
  - 環境変数管理（.env 自動読み込み、必須設定の検証、 Settings オブジェクト）

---

## 前提 / 必要環境

- Python 3.10+
  - 型注釈で `X | None` を使用しているため 3.10 以上を推奨します。
- 主要依存ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml
- ネットワーク経由の API 呼び出しを行うため、適切な API キーやネットワーク設定が必要です。

例（簡易）:
pip install duckdb openai defusedxml

プロジェクトの実際の依存は pyproject.toml / requirements.txt を参照してください（存在する場合）。

---

## セットアップ手順

1. リポジトリをクローン / ダウンロードしてプロジェクトルートへ移動

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements ファイルがあればそれを利用）
   - pip install -r requirements.txt

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml の同階層）に `.env` を置くと、自動的に読み込まれます。
   - 読み込み順序: OS 環境 > .env.local > .env
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。

   必須の例（.env の最小例）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API (必要なら)
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack (通知等)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # OpenAI
   OPENAI_API_KEY=sk-...

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development   # (development | paper_trading | live)
   LOG_LEVEL=INFO
   ```

   - `Settings` クラスで必須項目のチェックがあり、未設定だと ValueError が発生します。
   - `KABUSYS_ENV` は `development` / `paper_trading` / `live` のいずれかでなければなりません。

5. データディレクトリの準備（必要に応じて）
   - デフォルトの DuckDB パスは `data/kabusys.duckdb` です。親ディレクトリを作成してください。多くの初期化関数は自動でディレクトリ作成を行いますが、念のため。

---

## 基本的な使い方（例）

以下は代表的な API の使い方例です。実行は Python REPL やスクリプトから行います。

- DuckDB 接続例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントを付与（OpenAI API キーは env か引数で渡す）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scored:", n_written)
```

- 市場レジーム判定（MA200 + マクロセンチメント）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB の初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema は内部で UTC タイムゾーンを設定します
```

- RSS フィード取得（ニュースコレクタ）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- J-Quants から株価を直接取得:
```python
from kabusys.data.jquants_client import fetch_daily_quotes

records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
print(len(records))
```

注意:
- OpenAI 呼び出しや J-Quants API 呼び出しはネットワーク・API キーを必要とします。
- AI 関連関数は失敗時にフェイルセーフで 0 を返すデザインの箇所が多いですが、API キー未設定時は ValueError を送出します。

---

## 環境変数 / 設定一覧

主に以下の環境変数を使用します（必須は README の .env 例を参照）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI APIキー（score_news / score_regime で参照）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視用途など）
- KABUSYS_ENV — execution environment: development / paper_trading / live
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動読み込みを無効化

.env のパースは quotes、コメント、export プレフィックス等に対応しています。

---

## ディレクトリ構成（主要ファイル）

（パッケージソースは `src/kabusys` を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定・Settings、.env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL インターフェース再エクスポート（ETLResult）
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - news_collector.py      — RSS ニュース収集・前処理
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン / IC / factor_summary
  - (その他: strategy / execution / monitoring パッケージが export の一部として想定)

---

## 設計上の留意点（重要事項）

- Look-ahead バイアス対策:
  - AI / リサーチ / ETL 内では `datetime.today()` / `date.today()` を直接参照しない設計の箇所が多く、引数で基準日を渡すことを推奨します。
  - データ取得・処理の SQL では target_date 未満・以下等の条件に注意してルックアヘッドを避けています。

- 冪等性:
  - DuckDB への保存は基本的に ON CONFLICT DO UPDATE / INSERT ... DO UPDATE を用いて冪等性を担保しています。
  - ETL は差分取得と再フェッチ（backfill）を組み合わせて API 側の後出し修正を吸収する設計です。

- フェイルセーフ:
  - AI 呼び出しや外部 API 呼び出しは失敗時にスコア 0.0 やスキップするなど、全体処理を止めない設計の箇所が多いです。ただし、キー未設定等の致命的な問題は例外を投げます。

- セキュリティ:
  - ニュース取得で SSRF 対策、XML パースに defusedxml を利用、RSS レスポンスサイズ制限などの安全対策を実装しています。
  - J-Quants クライアントはレートリミットとリトライ（指数バックオフ）を実装しています。

---

## 開発・テストのヒント

- .env の自動読み込みはプロジェクトルート判定（.git または pyproject.toml）に基づき実行されます。ユニットテストや CI で外部設定を避ける場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants 呼び出し箇所はモックしやすい設計になっています（内部の `_call_openai_api` を patch する等）。
- DuckDB コネクションはメモリモード `":memory:"` でも動作するユーティリティがいくつかあります（例: init_audit_db）。

---

## 参考・次のステップ

- 本 README はコードベースから読み取れる機能・設計に基づく概要です。実運用前に以下を確認してください:
  - pyproject.toml / requirements.txt に記載の依存をインストール
  - .env.example を整備して必要な API キー・パスをセット
  - 開発用と本番用の KABUSYS_ENV に応じた設定・ログ・リスク制御の検討
  - 実際の発注機能を接続する場合は sandbox / paper_trading 環境を先に十分テスト

ご要望があれば、README に含める例や .env.example の完全なテンプレート、コマンドラインツールの追加説明（もし CLI があれば）などを追記します。
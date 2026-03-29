# KabuSys

日本株向け自動売買／データプラットフォームライブラリ KabuSys のリポジトリ向け README（日本語）

概要、機能、セットアップ、使い方、ディレクトリ構成をまとめています。ライブラリはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、研究（ファクター計算）、
監査ログ（発注トレース）などの主要機能を提供します。

---

## プロジェクト概要

KabuSys は日本株に特化したデータパイプラインとリサーチ／自動売買のためのユーティリティ群をまとめた Python パッケージです。主な目的は以下です。

- J-Quants API からのデータ取得（株価日足、財務情報、JPX カレンダー）
- DuckDB を用いた ETL（差分取得・冪等保存）と品質チェック
- RSS ベースのニュース収集と記事前処理（SSRF対策・トラッキング除去）
- OpenAI を利用したニュースセンチメントのスコアリング（銘柄単位 / マクロ判定）
- リサーチ向けファクター計算（モメンタム／ボラティリティ／バリュー等）
- 監査ログ（signal → order_request → execution）のスキーマ定義と初期化
- マーケットカレンダー管理（営業日判定・前後営業日の取得）

設計上、ルックアヘッドバイアスに注意し、外部 API 呼び出しはリトライやレート制御、フォールバックを備えています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（取得 / 保存 / 認証 / レート制御）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得と raw_news への冪等保存（SSRF対策、圧縮対応）
  - calendar_management: 営業日判定 / next_trading_day / prev_trading_day / calendar_update_job
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブル作成と初期化ユーティリティ
  - etl: ETLResult 再エクスポート
  - stats: zscore 正規化など汎用統計ユーティリティ
- ai
  - news_nlp.score_news: ニュース記事を銘柄ごとにまとめて OpenAI でセンチメントを算出し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュース（LLM）を合成して market_regime を保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数の自動ロード（.env/.env.local）と settings オブジェクト

---

## セットアップ手順（開発環境向け）

以下は一般的なセットアップ例です。プロジェクトの依存パッケージは pyproject.toml / requirements.txt を参照してください（本 README では依存を仮定して説明します）。

1. Python を用意（推奨: 3.10+）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージをインストール
   - pip install -e .    （プロジェクトのルートに pyproject.toml / setup.cfg がある前提）
   - または必要なライブラリを個別にインストール（duckdb, openai, defusedxml など）
4. 環境変数の設定
   - プロジェクトルートの .env または .env.local に必要な値を記述できます。
   - 自動ロードはデフォルトで有効。テスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（発注周りで使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- OPENAI_API_KEY: OpenAI API キー（score_news や regime_detector 呼び出しに指定可能）

サンプル .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（コード例）

以下は主要機能の利用例です。DuckDB 接続には公式 duckdb パッケージを使用します。

- DuckDB 接続準備
```python
import duckdb
from kabusys.config import settings

db_path = str(settings.duckdb_path)  # defaults to data/kabusys.duckdb
conn = duckdb.connect(db_path)
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai.news_nlp）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを引数で与えるか、環境変数 OPENAI_API_KEY を設定する
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ai.regime_detector）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

t = date(2026, 3, 20)
mom = calc_momentum(conn, t)
val = calc_value(conn, t)
vol = calc_volatility(conn, t)
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して監査テーブルが作成される
```

- ニュース RSS を取得（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- カレンダー関係ユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

テスト時の補助:
- OpenAI 呼び出しは内部で _call_openai_api を呼んでいるため、ユニットテストではモック（patch）してレスポンスを差し替えられます。
  例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", new=mock_fn)

---

## 注意点 / 設計上の重要事項

- ルックアヘッドバイアス防止のため、モジュール内では datetime.today() / date.today() を直接参照しないよう設計されています（多くの関数は target_date を引数として受け取ります）。
- J-Quants API はレート制限があるため内部で固定間隔スロットリング／リトライを実装しています。
- OpenAI 呼び出しには JSON Mode（response_format={"type":"json_object"}）を使い、レスポンスの厳密な JSON パースとバリデーションを行います。
- DB 書き込みは可能な限り冪等（ON CONFLICT DO UPDATE / INSERT ... DO NOTHING）にしています。
- ニュース取得は SSRF 対策、gzip・サイズ上限、トラッキングパラメータ削除など安全性に配慮しています。

---

## ディレクトリ構成（主要ファイル）

パッケージルート: src/kabusys 以下

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
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

主なモジュール概要:
- kabusys.config: 環境変数管理・自動 .env ロードと settings オブジェクト
- kabusys.data.jquants_client: J-Quants との通信・DuckDB 保存ロジック
- kabusys.data.pipeline: 日次 ETL と ETLResult
- kabusys.data.news_collector: RSS 取得と前処理
- kabusys.ai.news_nlp: 銘柄別ニュースセンチメント付与（OpenAI）
- kabusys.ai.regime_detector: マクロ＋ETF 指標で市場レジーム判定
- kabusys.research.*: ファクター計算・特徴量解析ユーティリティ

---

## よくある質問（FAQ）

Q: 設定はどのようにロードされますか？
A: config.Settings は起動時に .env/.env.local を自動ロードします（OS 環境変数 > .env.local > .env の優先順位）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: OpenAI キーを関数で渡すことはできますか？
A: はい。score_news / score_regime など多くの AI 関数は api_key 引数を受け付け、明示的にキーを渡せます。渡さない場合は環境変数 OPENAI_API_KEY を参照します。

Q: DuckDB のパスを変更したい
A: 環境変数 DUCKDB_PATH を設定するか、settings.duckdb_path を参照してプログラム側で指定可能です。

Q: J-Quants の認証トークンはどう扱いますか？
A: JQUANTS_REFRESH_TOKEN を .env に配置してください。jquants_client はリフレッシュトークンを使って id_token を取得／キャッシュします。

---

README に含めるコードスニペットは代表例です。実運用ではエラーハンドリング、ログ設定（logging.basicConfig 等）、証券会社 API（kabuステーション）との発注統合、ポジション管理やリスク管理を適切に実装してください。

問題点や改善案があればお知らせください。ドキュメントを拡張したい箇所（API リファレンス、運用手順、CI/CD、テスト戦略など）があれば追記します。
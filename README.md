# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と LLM を使ったニュースセンチメント評価、研究用ファクター計算、監査ログ（オーダー/約定トレーサビリティ）などを含んだモジュール群を提供します。

---

## プロジェクト概要

KabuSys は、日本株のデータ収集・品質チェック・ファクター生成・AI によるニューススコアリング・市場レジーム判定・監査ログなど、自動売買システムやリサーチ基盤に必要な主要機能を集めた Python パッケージです。設計方針として「ルックアヘッドバイアスを防ぐ」「冪等処理」「堅牢なエラーハンドリング」「DuckDB を用いた軽量なオンディスク DB」を重視しています。

主な特徴（抜粋）:
- J-Quants API からの日次株価・財務・カレンダーの差分 ETL（ページネーション・レート制御・リトライ・トークン自動更新）
- RSS ベースのニュース収集（SSRF/サイズ/トラッキングパラメータ等の保護）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（JSON mode、リトライロジック）
- マクロ + テクニカルを合成した市場レジーム判定
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）と初期化ユーティリティ

---

## 機能一覧

- data（ETL / calendar / jquants_client / news_collector / quality / stats / audit）
  - ETL: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - Calendar 管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - J-Quants クライアント: fetch/save daily quotes, financials, market calendar, listed info
  - News collector: RSS 取得・前処理・raw_news 登録（SSRF や Gzip/サイズ対策）
  - Quality: check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - Audit: init_audit_schema / init_audit_db（監査ログテーブルの初期化）
  - Stats: zscore_normalize
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) の MA とニュースセンチメントを合成して market_regime を生成
- research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 前提条件 / 依存ライブラリ

主に次のようなライブラリが想定されます（プロジェクトの pyproject / requirements に従ってください）:

- Python 3.10+
- duckdb
- openai
- defusedxml

例（最低限）:
pip install duckdb openai defusedxml

※ 実運用では Slack 通知・kabu API 等の連携用ライブラリも必要になる場合があります。

---

## 環境変数（必須／主要）

以下の環境変数は本パッケージの各機能で使用されます。必須のものは明示します。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。
- KABU_API_PASSWORD (必須 for kabu API を使う場合)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須 for Slack 通知)
- SLACK_CHANNEL_ID (必須 for Slack 通知)
- OPENAI_API_KEY (必須 for AI 機能を使う場合: score_news / score_regime)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, 有効値: development, paper_trading, live) デフォルト: development
- LOG_LEVEL (任意, 有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL) デフォルト: INFO

自動 .env 読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env を自動で読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で使用）。

---

## セットアップ手順（ローカル開発用）

1. Python 環境の準備（推奨: venv / pyenv）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存ライブラリをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトがパッケージ化されている場合）
   - pip install -e .

3. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数としてエクスポートしてください。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

4. データ用ディレクトリ作成（必要なら）
   - mkdir -p data

---

## 使い方（簡易サンプル）

以下は Python REPL やスクリプトからの利用例です。各例は接続に DuckDB を用いています。

- ETL（日次パイプライン）を実行する:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算（score_news）:

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定済みであれば api_key=None でよい
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）:

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: でインメモリ可
```

- RSS を取得（ニュース収集ヘルパー）:

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url, source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用ファクター計算:

```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
```

注意:
- AI（OpenAI）呼び出しは API キーと課金が発生します。ローカルテスト時はモックして使うことを推奨します。
- 多くの関数は「ルックアヘッドバイアス」を避けるために内部で date.today() を直接参照しない実装になっています。target_date を明示して使うことを推奨します。

---

## 設計上の挙動・注意点

- 冪等性: jquants_client の save_* 関数や ETL は ON CONFLICT DO UPDATE を使い冪等に保存します。
- エラーハンドリング: API 呼び出しはリトライ／バックオフ戦略を持ち、致命的な例外は上位で処理されます。AI 関連はフェイルセーフ（失敗時は中立スコア等）を採っています。
- 時刻管理: 監査ログは UTC 固定。news のウィンドウ計算等は JST と UTC の換算を明示的に行います。
- テスト: AI / ネットワーク呼び出しはモックしやすいよう内部 _call_openai_api / _urlopen 等を差し替え可能な設計です。

---

## ディレクトリ構成（抜粋）

以下はコードベースの主要ファイル・モジュール構成の簡易ツリーです。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (その他 ETL 補助モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (README に明示的なファイルはありませんがモジュール一覧に含めています)
  - (strategy/, execution/ 等のトップレベルパッケージは __all__ に含まれますが実装は別途)

---

## 開発・テストのヒント

- 自動 .env 読み込みを無効にしてユニットテストを制御するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出し部分は内部関数（例: kabusys.ai.news_nlp._call_openai_api）をモックしてテストできます。
- news_collector.fetch_rss はネットワークの代わりにモック可能な _urlopen を内部で利用しています。
- DuckDB を使ったテストでは ":memory:" でインメモリ DB を使うと高速です。

---

以上が KabuSys の概要・導入手順・主要機能の説明です。実際の運用にあたっては各環境変数の管理、API キーの扱い（秘密情報管理）、および OpenAI / 証券会社 API の利用制約に留意してください。必要であれば利用シナリオ別の詳細な例（ETL ジョブの cron 設定、Slack 通知の組み込み、kabu API とブローカー連携の実装例）を追記できます。必要なら教えてください。
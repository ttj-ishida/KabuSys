# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群。  
DuckDB をデータ層に用い、J-Quants からのデータ取得、ニュース収集・NLP によるセンチメント算出、市場レジーム判定、研究用ファクター計算、監査ログなどのユーティリティを提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足 / 財務データ / JPX カレンダーを差分取得（ページネーション・レート制御・リトライ対応）
  - ETL パイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを実行
- データ品質チェック（quality モジュール）
  - 欠損・重複・スパイク・日付不整合チェック
- ニュース収集（news_collector）
  - RSS フィードの取得、前処理、SSRF 対策、サイズ制限等の安全対策
- ニュース NLP（ai.news_nlp）
  - OpenAI を使った銘柄毎のニュースセンチメント算出（JSON Mode, バッチ処理・リトライ）
- 市場レジーム判定（ai.regime_detector）
  - ETF(1321) の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成して日次で 'bull'/'neutral'/'bear' を判定
- 研究用ユーティリティ（research）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化
- 監査ログ（data.audit）
  - シグナル → 発注 → 約定までのトレーサビリティ用テーブル定義・初期化ユーティリティ
- カレンダー管理（data.calendar_management）
  - market_calendar を元に営業日判定・前後営業日取得・カレンダー更新ジョブ

---

## 必要条件（依存）

主なランタイム依存（pyproject/setup で管理を想定）:

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

その他標準ライブラリ（urllib, datetime, logging 等）を利用。実行環境により追加パッケージが必要な場合があります。

---

## 環境変数 / .env

自動的にプロジェクトルートの `.env` と `.env.local` を読み込みます（CWD には依存しません）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（本番的に実行する場合）:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注機能がある場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot Token
- SLACK_CHANNEL_ID — Slack チャネル ID

推奨/任意:

- OPENAI_API_KEY — OpenAI 呼び出し時の API キー（ai モジュールに必要）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / ...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等（デフォルト: data/monitoring.db）

サンプル `.env.example`（README 用）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# OpenAI
OPENAI_API_KEY=sk-...

# cabu station (発注時)
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化（例: venv / pyenv）
3. 依存をインストール
   - 例:
     pip install duckdb openai defusedxml
   - またはプロジェクトが pyproject を持つ場合:
     pip install -e .

4. `.env` を作成して必要な環境変数を設定（上記参照）
5. DuckDB ファイルや監査 DB のディレクトリがなければ作成されます（init 関数が自動生成）

---

## 使い方（例）

以下は主要なユースケースの簡単なコード例です。実行前に環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定してください。

- DuckDB 接続例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント (ai.news_nlp.score_news):
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されている前提
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {written} codes")
```

- 市場レジーム判定 (ai.regime_detector.score_regime):
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成されれば OK
```

- 研究用ファクター計算:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- カレンダー関連ユーティリティ:
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

- RSS フェッチ（news_collector.fetch_rss）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

for source, url in DEFAULT_RSS_SOURCES.items():
    articles = fetch_rss(url, source)
    # articles: list of NewsArticle (dict with id, datetime, source, title, content, url)
    # DB 保存は ETL パイプライン内等で行う（このモジュールは記事の取得・正規化を担当）
```

注意:
- ai モジュールは OpenAI API を呼び出します。API キーを設定し、料金やレートに注意してください。
- ETL / jquants_client は J-Quants の利用規約・レート制限を順守する前提です。

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント算出（OpenAI）
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py         — 市場カレンダー管理・判定
    - etl.py                         — ETL 公開インターフェース（ETLResult）
    - pipeline.py                    — ETL 実処理（run_daily_etl 等）
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログスキーマ初期化
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - news_collector.py              — RSS 取得・前処理
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Value / Volatility 計算
    - feature_exploration.py         — 将来リターン・IC・統計解析
  - research/*（その他ファイル群）
  - ...（将来的に strategy, execution, monitoring 等が追加予定）

---

## 設計上の注意（抜粋）

- ルックアヘッドバイアス回避が多くの関数で意識されています（date 引数で明示的に基準日を与え、内部で date.today() を直接参照しない）。
- AI 系処理はフェイルセーフ設計：API 失敗時は 0.0 にフォールバックし、例外を投げず処理継続する箇所があるので監査やログを確認してください。
- DuckDB に対しては冪等な保存（ON CONFLICT / DELETE → INSERT 等）を行い、部分失敗時に既存データを必要以上に上書きしない工夫があります。
- news_collector は SSRF / XML Bomb / 大容量レスポンス対策を実装しています。

---

## よくある質問

Q. 開発中に .env の自動読み込みを無効にできますか？  
A. はい。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q. OpenAI を使いたくないテスト環境はどうしますか？  
A. ai モジュールの内部 API 呼び出し関数（_call_openai_api 等）を unittest.mock.patch でモックできます。regime_detector / news_nlp の実装はモックを想定した構成です。

---

必要であれば、README に含めるサンプル .env ファイルのテンプレートや、より詳細な API 使用例（J-Quants トークン取得フロー、Slack 通知の実装例、発注フロー実行例）も作成します。どの項目を拡張しますか？
# KabuSys

日本株向けのデータパイプライン・研究・自動売買の基盤ライブラリです。  
ETL（J-Quants 経由）、ニュース収集と NLP による銘柄センチメント評価、ファクター計算、監査ログなどのユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための内部ライブラリ群です。主に以下の機能を提供します。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL（保存は DuckDB）
- ニュース収集（RSS）と前処理、OpenAI を用いたニュースセンチメントのスコアリング
- 市場レジーム判定（ETF とマクロニュースの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー、Zスコア正規化）
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）
- 監査ログ（signal / order_request / executions テーブル）と初期化ユーティリティ
- J-Quants クライアント（レート制御・リトライ・トークン自動リフレッシュ）

設計上の注意点として、Look-ahead バイアス防止のため内部で datetime.today()/date.today() を不用意に参照しない実装が多く採用されています。また、DB 書き込みは冪等になるよう配慮されています。

---

## 主な機能一覧

- data:
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系関数、get_id_token）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS 取得・前処理、SSRF 対策、サイズ制限）
  - データ品質チェック（missing, duplicates, spike, date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai:
  - ニュース NLP（score_news: 銘柄ごとのニュースセンチメントを ai_scores に書込）
  - レジーム判定（score_regime: ETF + マクロニュースで daily regime を算出）
- research:
  - ファクター計算（momentum / volatility / value）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- config:
  - 環境変数読み込みと settings オブジェクト（.env 自動読み込み・保護・バリデーション）

---

## 前提条件 / 必要パッケージ

- Python 3.10+
- 必須ライブラリ（一例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib, json, logging 等を使用

（プロジェクトの pyproject.toml / requirements.txt に正式な依存がある想定です。ローカルで使う場合は上記をインストールしてください）

例:
```bash
python -m pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. レポジトリをクローン／配置
2. 仮想環境を作成・有効化（任意）
3. 依存パッケージをインストール（上記参照）
4. 環境変数を設定（.env をプロジェクトルートに配置することで自動読み込みされます）

.env の自動読み込み:
- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を探索）で `.env` / `.env.local` を自動で読み込みします。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

### 推奨環境変数（.env 例）

以下は主要な環境変数の例です（実運用では安全に保管してください）。

```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=xxxx
KABU_API_PASSWORD=xxxx
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xxxx
SLACK_CHANNEL_ID=xxxx
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid
CPU_THRESHOLD_PCT=90.0
MEMORY_THRESHOLD_PCT=85.0
DISK_THRESHOLD_PCT=90.0
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

settings による取得例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## 使い方（簡単なサンプル）

以下は主要な操作例です。実行は Python スクリプト・REPL で行ってください。

- DuckDB 接続と ETL 日次実行

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- 監査 DB 初期化（監査用の DuckDB を初期化する）

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# この conn_audit に対して監査ログを書き込める
```

- ニュースのセンチメントスコア生成（AI）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026,3,20), api_key="sk-xxxx")
print(f"written: {written} codes")
```

- 市場レジーム判定（AI）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-xxxx")
```

- RSS の単体取得（ニュース収集の一部機能）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意:
- OpenAI の呼び出し部分はモジュール内で _call_openai_api を分離しているため、ユニットテスト時はパッチしてモック可能です。
- J-Quants API 呼び出しは jquants_client 内で RateLimiter（固定間隔）とリトライロジックを備えています。

---

## データベース初期化（監査テーブル等）

監査テーブルを既存の DuckDB に追加するには:

```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

監査専用 DB を作るには init_audit_db を使用します（親ディレクトリ自動作成）。

---

## 開発メモ / 実装上のポイント

- Look-ahead バイアス対策:
  - 多くの関数は target_date を引数に取り、内部で現在時刻を参照しないように設計されています。
  - ETL / AI 処理をバックテストパイプラインに組み込む際はこの点を尊重してください。
- 冪等性:
  - jquants_client の save_*、news_collector の保存等は ON CONFLICT を用いて冪等に保存します。
- リトライとフォールバック:
  - ネットワーク／API エラーに対してリトライ（指数バックオフ）し、AI API の失敗はフェイルセーフ（スコア 0.0 等）で継続する設計です。
- セキュリティ:
  - news_collector は SSRF 対策、リダイレクト検査、受信サイズ制限、defusedxml による XML パース保護を施しています。
- テスト向け:
  - OpenAI 呼び出しや URL オープンなどは内部関数をモックしやすい形に分離しています。

---

## ディレクトリ構成

（主要ファイル・モジュール一覧: src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                         - 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                      - ニュース NLP スコアリング（score_news）
    - regime_detector.py               - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                - J-Quants API クライアント（fetch / save）
    - pipeline.py                      - ETL パイプライン / run_daily_etl 等
    - etl.py                           - ETL 結果の公開（ETLResult）
    - calendar_management.py           - 市場カレンダー管理 / is_trading_day 等
    - news_collector.py                - RSS ニュース収集・前処理
    - quality.py                       - データ品質チェック
    - stats.py                         - zscore_normalize 等
    - audit.py                         - 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py               - Momentum/Volatility/Value の計算
    - feature_exploration.py           - 将来リターン / IC / summary / rank
  - (その他) strategy, execution, monitoring などのトップレベル参照は __init__ で公開される想定

---

## よくある質問（FAQ）

Q: .env の自動ロードを無効にしたい  
A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます。

Q: OpenAI のテストを行いたい（API を叩きたくない）  
A: ai モジュール内の _call_openai_api を unittest.mock.patch で置き換えてモックレスポンスを返すことでテスト可能です。

Q: J-Quants のトークンが切れたら自動で更新されますか？  
A: はい。jquants_client._request は 401 を検知すると get_id_token を呼んで一度だけトークンをリフレッシュしてリトライします。

---

## 貢献・拡張

- 新しいデータソースや研究用ファクターを追加する場合は、data/ または research/ に新しいモジュールを追加し、既存の ETL / 正規化パターンに合わせてください。
- OpenAI モデルやプロンプトを調整する際は ai/news_nlp.py 及び ai/regime_detector.py の SYSTEM_PROMPT と _MODEL 定数を確認してください。

---

README はコードベースの注釈に基づいて作成しています。実際の動作には pyproject.toml / requirements.txt に記載された依存関係やプロジェクト固有の設定（.env 等）が必要です。必要であれば README の英語版やインストール用スクリプト・例の拡張を作成します。
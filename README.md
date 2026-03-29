# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集と NLP（OpenAI でのセンチメント評価）、ファクター計算、監査ログ（注文→約定のトレーサビリティ）、マーケットカレンダー管理などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 環境変数（.env）例
- 基本的な使い方（コード例）
- ディレクトリ構成（概要）

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ基盤向けに設計された Python モジュール群です。  
主な目的は以下です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（差分 ETL、冪等保存）
- RSS によるニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄ごと・マクロ判定）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）のためのスキーマ初期化とユーティリティ
- 市場カレンダー管理（営業日の判定、next/prev_trading_day 等）

設計方針として、バックテストでのルックアヘッドバイアスを防ぐこと、冪等処理・フェイルセーフを重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制限・リトライ）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL ジョブ（prices/financials/calendar）
  - news_collector: RSS 取得・前処理・raw_news への保存補助
  - calendar_management: market_calendar 管理、営業日判定、calendar_update_job
  - quality: データ品質チェック（missing, spike, duplicates, date consistency）
  - audit: 監査ログ用の DDL/初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄別にニュースを集約して OpenAI に投げ、ai_scores を更新
  - regime_detector.score_regime: ETF（1321）MA200 乖離 + マクロニュースで市場レジーム判定
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

前提: Python 3.9+（コードは型注釈で Path | None 等を使用）、pip または Poetry 等。

1. リポジトリをクローン／配置
   - src レイアウトになっているため、ローカル開発時は editable install を推奨します。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   必要な主な外部依存例:
   - duckdb
   - openai
   - defusedxml
   - （必要に応じて）requests 等

   例（最低限）:
   - pip install duckdb openai defusedxml

   補足: 実運用では requirements.txt や pyproject.toml を用意して管理してください。

4. 開発インストール（src 配下をパッケージとして扱う）
   - pip install -e .

5. .env 作成（下記参照）

注意:
- パッケージは src/kabusys 以下のモジュール群をインポートして利用します。
- 自動で .env をロードする仕組みが組み込まれており、プロジェクトルートの .env/.env.local を読み込みます。自動ロードを抑制したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（.env）例

必須の主要環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token のため）
- KABU_API_PASSWORD: kabuステーション等の API パスワード（利用する場合）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot Token（利用する場合）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで未指定時に参照）

その他（任意／デフォルト有り）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化

例 (.env):
    JQUANTS_REFRESH_TOKEN=あなたの_refresh_token
    OPENAI_API_KEY=sk-xxxxx
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-xxxx
    SLACK_CHANNEL_ID=C01234567
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

注意: .env のパースはシェル風の形式に対応しており、export プレフィックス／引用符／行末コメント等を解釈します。

---

## 基本的な使い方（コード例）

以下は一例です。実行前に .env を準備しておくか、明示的に api_key 等を渡してください。

- DuckDB に接続して日次 ETL を実行する（pipeline）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores を書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
print("scored:", n_written)
```

- 市場レジームを判定して market_regime に書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_duckdb.db")
# conn を使って order_requests / signal_events / executions テーブルが作成される
```

- RSS フィードをフェッチ（news_collector）:

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["title"], a["datetime"])
```

- J-Quants の ID トークンを取得:

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # JQUANTS_REFRESH_TOKEN を使用
print(token)
```

- ファクター計算（research）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
print(len(momentum), momentum[:3])
```

注意点:
- 多くの関数は DuckDB 接続と target_date を受け取り、内部で look-ahead バイアスを避ける実装になっています。
- OpenAI 呼び出しを行う関数は api_key を引数で明示的に渡すこともできます（テスト用にパッチ可能）。

---

## よく使うエントリポイント（サマリ）

- ETL / データ:
  - kabusys.data.pipeline.run_daily_etl(...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- ニュース・NLP:
  - kabusys.data.news_collector.fetch_rss(...)
  - kabusys.ai.news_nlp.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
- 監査ログ:
  - kabusys.data.audit.init_audit_schema(conn) / init_audit_db(path)
- 研究用:
  - kabusys.research.factor_research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.feature_exploration.calc_forward_returns / calc_ic / factor_summary
- ユーティリティ:
  - kabusys.data.stats.zscore_normalize
  - calendar 管理: kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days

---

## ディレクトリ構成（src/kabusys の主なファイル）

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
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research パッケージは factor / feature の計算ロジックを提供
  - data パッケージは ETL / 保存 / 品質チェック / カレンダー / RSS などデータ基盤関連を提供
  - ai は OpenAI を使った NLP 系のロジック（ニュースセンチメント、レジーム判定）

（README では省略されていますが、各モジュール中に詳細な docstring があり、関数の入出力や設計意図が明記されています）

---

## 運用上の注意・推奨

- 本ライブラリは実運用（特に実口座での発注）用途に用いる場合、十分なテスト・監査を行ってください。発注や資金管理は重大なリスクを伴います。
- OpenAI 呼び出しや外部 API 呼び出しはコスト・レート制限があるため、バッチ単位での実行やロギング・リトライ設定に注意してください。
- DuckDB ファイルのバックアップ、監査ログの保護、環境変数（秘密情報）の適切な管理を行ってください。
- ETL 実行時は run_daily_etl の戻り値 ETLResult を監視し、quality_issues や errors を監査してアラートやオペレーション判断に活用してください。

---

必要であれば README に追加したい内容（例: 詳細な .env.example、CI 用コマンド、運用チェックリスト、具体的な SQL スキーマ）を教えてください。各モジュールの利用例や API 仕様をより詳しく展開できます。
# KabuSys

日本株向け自動売買・データプラットフォームライブラリ

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、品質チェック、特徴量（ファクター）計算、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注→約定トレーサビリティ）などを含む、自動売買基盤向けのユーティリティ群です。DuckDB をデータレイヤに用い、ETL パイプライン・データ品質チェック・研究用のファクター解析機能を提供します。

主な設計方針:
- ルックアヘッドバイアス（未来情報参照）を防ぐ設計
- J-Quants / OpenAI API 呼び出しに対する堅牢なリトライ・レート制御
- DuckDB への冪等保存（ON CONFLICT）と監査ログの充実
- テストしやすいように内部 API の差し替えを想定

---

## 機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
- データ ETL（kabusys.data.pipeline）
  - 株価（日足）、財務データ、マーケットカレンダーの差分取得・保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制御、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、SSRF 対策、トラッキングパラメータ除去、冪等保存
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア取得、ai_scores へ書込
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して daily レジーム判定
- 研究用関数（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン、IC 計算、サマリー
- 監査ログ管理（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル定義・初期化ユーティリティ
- 汎用統計ユーティリティ（kabusys.data.stats）
  - Z スコア正規化など

---

## 要件（主な依存）

- Python 3.10+
- duckdb
- openai (OpenAI SDK)
- defusedxml
- そのほか標準ライブラリ

（実プロジェクトでは pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順（ローカル開発向け - 例）

1. リポジトリをクローンしてパッケージをインストール
   - pip install -e .（開発用インストール）

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

3. 環境変数を設定
   - プロジェクトルートに `.env` を配置するか、OS 環境変数を設定します。
   - 自動ロードはデフォルトで有効（.env / .env.local）。自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API 用パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出し時に省略可能）
   - DB パス（任意、デフォルト）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 SQLite、デフォルト: data/monitoring.db)
   - KABUSYS_ENV: one of "development", "paper_trading", "live"（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

5. .env のサンプルを用意（.env.example を参照して作成してください）

---

## 初期化・基本的な使い方（Python 例）

以下はライブラリ API の代表的な使い方例です。DuckDB 接続には duckdb.connect を使用します。

- DuckDB 接続を作成して監査用スキーマを初期化する:
```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# または既存接続に対して
# conn = duckdb.connect("data/kabusys.duckdb")
# init_audit_schema(conn)
```

- 日次 ETL を実行する（市場カレンダー・株価・財務の差分取得 + 品質チェック）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（指定日分）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written:", n_written)
```

- 市場レジームスコア計算:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
res = score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- カレンダー周りユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_td = is_trading_day(conn, date(2026, 3, 20))
next_td = next_trading_day(conn, date(2026, 3, 20))
```

- RSS フィード取得（ニュース収集）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
```

---

## よく使うエントリポイント（要約）

- ETL / データ
  - kabusys.data.pipeline.run_daily_etl
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
  - kabusys.data.quality.run_all_checks
- ニュース / AI
  - kabusys.ai.news_nlp.score_news
  - kabusys.ai.regime_detector.score_regime
- 監査ログ
  - kabusys.data.audit.init_audit_db / init_audit_schema
- 設定
  - from kabusys.config import settings

---

## 環境変数の自動ロード挙動

- プロジェクトルートは __file__ を基準に上位ディレクトリから `.git` または `pyproject.toml` を探索して決定します。見つからない場合は自動ロードをスキップします。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースはシェル風（export KEY=値、コメント行、クオート対応）に対応しています。

---

## ログ・実行モード

- KABUSYS_ENV 値: "development", "paper_trading", "live"
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- settings.is_live / is_paper / is_dev で判定可能

---

## ディレクトリ構成（主なファイル）

src/kabusys/
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
  - etl.py (ETL エクスポート)
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: 例えば jquants_client のユーティリティ)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring / execution / strategy / (パッケージ化されている想定のトップモジュール)

（上記は本リポジトリに含まれる主要モジュールの抜粋です）

---

## 開発・テストのヒント

- OpenAI 呼び出しや外部 HTTP をテストで差し替えるため、内部の _call_openai_api / _urlopen 等の関数を unittest.mock.patch でモックする設計になっています。
- 自動環境読み込みを無効化してテスト用環境を明示的に注入する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB の接続文字列に ":memory:" を渡せばインメモリ DB を使用できます（audit.init_audit_db も対応）。

---

## 免責と注意事項

- 本プロジェクトは取引システムの一部要素を提供しますが、実際の売買に使用する際は十分な検証・バックテスト・リスク管理を行ってください。
- 実際の取引 API（kabu ステーション等）との接続・発注処理は別モジュール／運用ルールを整備する必要があります。
- API キー・トークンは秘匿管理し、ログやリポジトリに含めないでください。

---

必要があれば README にサンプル .env.example、より詳しいクイックスタート（Docker / CI / systemd ジョブ定義）、あるいは API リファレンス（関数一覧と引数説明）を追加できます。どの情報を優先して拡充しますか？
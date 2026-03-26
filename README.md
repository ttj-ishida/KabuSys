# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants / RSS / OpenAI 等を組み合わせてデータ収集（ETL）・品質チェック・ニュースの NLP スコアリング・市場レジーム判定・監査ログ機能などを提供します。

---

## プロジェクト概要

- ETL：J-Quants API から株価・財務・マーケットカレンダー等を差分取得して DuckDB に格納するパイプラインを提供します（差分取得・バックフィル・品質チェック含む）。
- ニュース NLP：RSS から収集したニュースに対して OpenAI（gpt-4o-mini）を使い銘柄別センチメントを算出し `ai_scores` に保存する処理を提供します。
- レジーム判定：ETF（1321）200 日移動平均乖離とマクロニュースセンチメントを合成して日次の市場レジームを判定・保存します。
- 監査ログ：シグナル → 発注 → 約定までをトレースする監査用スキーマ（DuckDB）を生成・初期化する機能を提供します。
- データ品質チェック：欠損・重複・スパイク・日付不整合などを検出するチェック群を実装しています。
- 研究ユーティリティ：ファクター計算（momentum/value/volatility）・将来リターン・IC / 統計サマリ等の研究用ツールを提供します。

---

## 主な機能一覧

- kabusys.config
  - .env / 環境変数の自動読み込み（.env, .env.local）と設定オブジェクト `settings`
- kabusys.data
  - jquants_client：J-Quants API クライアント（取得・保存・レートリミット・リトライ等）
  - pipeline：日次 ETL（run_daily_etl）および個別 ETL ジョブ（run_prices_etl 等）
  - calendar_management：市場カレンダー管理・営業日判定ユーティリティ
  - news_collector：RSS の安全な取得と前処理ユーティリティ
  - quality：データ品質チェック群（欠損・重複・スパイク・日付不整合）
  - audit：監査ログスキーマの初期化・監査 DB 作成（init_audit_schema / init_audit_db）
  - stats：汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news：ニュースを LLM で評価し `ai_scores` に書き込む
  - regime_detector.score_regime：市場レジーム判定（ma200 + マクロセンチメント）
- kabusys.research
  - ファクター計算・特徴量探索・IC 計算などの研究用ユーティリティ

---

## 必要条件

- Python 3.10 以上（構文で | 型注釈等を利用）
- 主要依存（抜粋）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード）

pip インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発環境ではさらに linters / test libs 等を追加
```

パッケージをプロジェクトとして使う場合:
```bash
pip install -e .   # setup.cfg/pyproject がある場合
```

---

## 環境変数（代表）

必須（実運用で必要）:
- JQUANTS_REFRESH_TOKEN = J-Quants リフレッシュトークン
- OPENAI_API_KEY = OpenAI API キー（score_news/score_regime で使用）
- KABU_API_PASSWORD = kabu API 用パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID = Slack 通知設定（監視等で使用）

任意:
- KABUSYS_ENV = development | paper_trading | live（デフォルト: development）
- LOG_LEVEL = DEBUG|INFO|...（デフォルト: INFO）
- DUCKDB_PATH = data/kabusys.duckdb（デフォルト）
- SQLITE_PATH = data/monitoring.db（監視 DB 用など）
- KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 を設定すると自動 .env ロードを無効化

.config モジュールの挙動:
- プロジェクトルート（.git または pyproject.toml を検索）を起点に `.env` と `.env.local` を自動読み込みします。
  - 読み込み優先度: OS 環境 > .env.local（強制上書き）> .env（未定義のみ）
- テストや意図的に自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=./data/kabusys.duckdb
```

---

## セットアップ手順（開発者向け / ローカル実行）

1. リポジトリをチェックアウト
2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存ライブラリをインストール
   ```bash
   pip install duckdb openai defusedxml
   # 必要に応じて他のライブラリを追加
   ```
4. 必要な環境変数を用意（.env をプロジェクトルートに配置）
5. DuckDB ファイルの親ディレクトリを作成（settings.duckdb_path を利用）
   ```bash
   mkdir -p data
   ```
6. 監査ログ DB の初期化（任意）
   ```python
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db(settings.duckdb_path)  # 必要なら別パスを指定
   conn.close()
   ```
7. （重要）データテーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, prices_daily, etc.）のスキーマを用意してください。
   - 本コードベースは保存（INSERT）を行いますが、テーブル DDL（全体スキーマ定義）は別に用意することが前提です（プロジェクト内の schema 初期化スクリプト等を利用してください）。

---

## 使い方（主要例）

以下はライブラリを直接呼び出すシンプルな使用例です。必ず事前に環境変数と DB スキーマを整えてください。

- DuckDB 接続を作成:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュース NLP（銘柄別センチメント付与）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY を使用するか、api_key 引数で直接渡す
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
# market_regime テーブルに日次のレジーム結果が保存されます
```

- 監査スキーマ初期化（監査用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # または別パス
```

- RSS 取得（ニュース収集の一部）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# 取得した article は raw_news に格納するロジックへ渡して永続化してください
```

注意:
- score_news / score_regime は OpenAI API を呼び出すため API キーを必ず設定してください。
- ETL / 保存処理は DuckDB に対して INSERT を実行します。対象テーブルが存在することを確認してください。
- ネットワーク障害や API の一時エラーはリトライ・フォールバックの実装がありますが、API のレートやコストには留意してください。

---

## 開発者向けポイント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を検出）を起点に行われます。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用すると便利です。
- OpenAI 呼び出しは各モジュール内で明示的に行われ、モック差し替えを想定した設計になっています（テスト時は `unittest.mock.patch` で `_call_openai_api` を差し替えてください）。
- J-Quants クライアントは内部で固定間隔の RateLimiter を実装しています（120 req/min）。
- DuckDB に対する書込みは基本的に冪等操作（ON CONFLICT DO UPDATE / DO NOTHING）を用いる設計です。
- ルックアヘッドバイアス回避のため、各モジュールは `date.today()` を直接参照しない設計方針を取っています（target_date を明示的に渡す）。

---

## ディレクトリ構成（抜粋）

```
src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py
      calendar_management.py
      news_collector.py
      quality.py
      stats.py
      audit.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/
    # 他に strategy, execution, monitoring 等のサブパッケージが想定される
```

主なファイルと責務:
- config.py: 環境変数・設定読み込み
- data/jquants_client.py: J-Quants API 呼び出しと DuckDB 保存ロジック
- data/pipeline.py: 日次 ETL パイプライン（run_daily_etl 等）
- data/news_collector.py: RSS 取得・前処理・安全対策
- ai/news_nlp.py: ニュースの LLM スコアリング
- ai/regime_detector.py: 市場レジーム判定（MA + LLM）
- data/audit.py: 監査ログスキーマの初期化ユーティリティ
- research/*: ファクター計算・特徴量解析ユーティリティ

---

## よくある質問 / 注意点

- Q: テーブルスキーマはどこにある？
  - A: このコードベースはテーブルに対する操作（INSERT/DELETE）を行いますが、すべての DDL（raw_prices などの作成）は別途用意する想定です。監査スキーマは `kabusys.data.audit.init_audit_schema / init_audit_db` で自動生成できます。その他のテーブルはプロジェクト内の schema/migrations を利用するか、DataPlatform.md を参照して初期化してください。

- Q: テスト時に外部 API を叩きたくない
  - A: OpenAI 呼び出し等はモジュール内の `_call_openai_api` を patch することでモック化できます。また、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えば .env の自動ロードを抑制できます。

- Q: 実運用での注意
  - A: OpenAI / J-Quants の API 料金・レート制限に注意してください。 `KABUSYS_ENV` を `live` にすることで本番判定が可能になりますが、本番環境では発注周りの安全チェック（リスク・ポジション制限等）を十分に実装してください。

---

## 参考（ドキュメント）

- 各モジュールの docstring に設計方針・処理フローが詳述されています。実装を拡張する場合はそちらを参照してください。
- DataPlatform.md / StrategyModel.md 等がプロジェクト全体の仕様として存在する想定です（本リポジトリ外に配置されている場合があります）。

---

この README はコードベース提供の主要な使い方と注意点をまとめたものです。実際の運用・デプロイにあたっては、環境固有の設定・スキーマ定義・運用手順（監視/アラート/ロールバック）を別途整備してください。
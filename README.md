# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）・ニュース収集・LLM を用いたニュース/レジーム評価・ファクター計算・監査ログ管理など、バックテスト／運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API 経由で株価・財務・マーケットカレンダーを差分取得して DuckDB に格納する ETL パイプライン
- RSS からのニュース収集と銘柄紐付け（raw_news / news_symbols）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）およびマクロレジーム判定（market_regime）
- 研究用ファクター計算（Momentum / Value / Volatility 等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定まで追跡可能な監査ログスキーマ（DuckDB）と初期化ユーティリティ

設計上の特徴:
- Look-ahead バイアス回避（datetime.now / date.today を直接使わない箇所が多い）
- 冪等な DB 書き込み（ON CONFLICT 等）
- API 呼び出しはリトライ・バックオフ・レート制限を組み込み
- テストしやすい実装（API 呼び出しの差し替えが容易）

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（kabusys.data.jquants_client）
  - save_* 系の DuckDB 保存関数
- ニュース収集
  - RSS 取得・前処理・raw_news への保存（kabusys.data.news_collector）
- ニュース NLP / レジーム判定（OpenAI）
  - score_news（kabusys.ai.news_nlp）
  - score_regime（kabusys.ai.regime_detector）
- 研究 (research)
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ（audit）
  - init_audit_schema / init_audit_db（kabusys.data.audit）
- 設定管理
  - 環境変数/.env 自動読み込み（kabusys.config）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（typing の | 表記を使用）
- DuckDB, OpenAI SDK, defusedxml などが必要

1. リポジトリをクローンしてパッケージをインストール（開発モード）
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```
   必要な依存が package metadata に書かれていない場合は、最低限以下をインストールしてください:
   ```
   pip install duckdb openai defusedxml
   ```

2. 環境変数を設定
   環境変数を直接設定するかプロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config）。
   自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=your_openai_api_key
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (デフォルト)
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

   .env の書式例:
   ```
   JQUANTS_REFRESH_TOKEN=abcd...
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

3. データベースディレクトリ作成
   - DuckDB ファイルの親ディレクトリは自動作成されますが、必要に応じて `data/` を作成してください。
   ```
   mkdir -p data
   ```

---

## 使い方（主要ユースケース）

ここでは簡単な Python スニペットと動作イメージを示します。

1) 日次 ETL を実行する（例: スクリプトから）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリングを実行する（OpenAI API が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 環境変数 OPENAI_API_KEY が設定されていれば api_key 引数は不要
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定を実行する（1321 の MA200 とマクロニュースを統合）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

4) 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル(signal_events, order_requests, executions) が作られます
```

5) 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{date, code, mom_1m, mom_3m, mom_6m, ma200_dev}, ...]
```

注意:
- OpenAI との接続は `OPENAI_API_KEY` を環境変数で設定するか、関数引数に `api_key` を渡してください。
- ETL / 保存処理は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar 等）が存在することを前提としています。適宜スキーマ初期化が必要です（本リポジトリに schema 初期化機能があるならそちらを利用してください）。

---

## 主要ファイル・ディレクトリ構成

以下はソースツリーの主なファイルと簡単な説明です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env 自動読み込み、settings オブジェクトを提供
  - ai/
    - __init__.py
    - news_nlp.py        : ニュースセンチメント（score_news）
    - regime_detector.py : マクロ+MA200 を合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント（取得 + 保存）
    - pipeline.py           : ETL パイプライン（run_daily_etl 等）
    - etl.py                : ETLResult 再エクスポート
    - news_collector.py     : RSS 取得・記事前処理・保存
    - calendar_management.py: 市場カレンダー関連ユーティリティ（is_trading_day 等）
    - stats.py              : zscore_normalize 等の統計ユーティリティ
    - quality.py            : データ品質チェック（各種チェック）
    - audit.py              : 監査ログスキーマの作成・初期化
  - research/
    - __init__.py
    - factor_research.py    : Momentum/Value/Volatility の計算
    - feature_exploration.py: forward returns / IC / factor summary / rank

各モジュールはドキュメンテーション文字列で設計方針・警告（例: Look-ahead 防止）や返り値の形を詳述しています。実装を追うことで使い方の詳細が確認できます。

---

## 設定（settings）と自動 .env 読み込み

- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基に `.env` / `.env.local` を自動読み込みします（kabusys.config）。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数を設定:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

settings オブジェクト（kabusys.config.settings）から設定値を取得できます。必須変数が見つからない場合は ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。

---

## 注意点 / 運用上のヒント

- OpenAI 呼び出しはエラー時にフェイルセーフでフォールバック（通常 0.0 スコア）する設計ですが、APIキー・レート制限には注意してください。
- DuckDB の `executemany` は空リストを許容しないバージョンがあるため本コードでは空チェックを行っています。
- research パッケージの計算関数は発注や外部 API を呼ばないように設計されており、バックテスト用途で安全に使えます。
- 本パッケージはデータ収集・分析を行うライブラリ群であり、実際の発注を行うモジュール（execution 等）が別にある場合は、そちらとの接続設計に注意してください。

---

README に記載の手順で足りない点や、実際に CLI / systemd / Airflow 等で運用するためのデプロイ手順（サービス化、監視、リトライポリシー）について詳細が必要であれば、用途に合わせた運用ドキュメントを作成します。必要ならどの環境（ローカル / Docker / クラウド）で動かす予定か教えてください。
# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL・ニュース収集・LLMベースのニュース解析・市場レジーム判定・リサーチ（ファクター計算）・監査ログなど、取引システムとバックテスト基盤に必要な機能群を含みます。

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集・保存し、銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で評価する NLP モジュール
- ETF（1321）の長期移動平均乖離とマクロニュースセンチメントを組み合わせた市場レジーム判定
- 研究用途のファクター計算、IC・将来リターンの算出ユーティリティ
- データ品質チェック、監査（signal → order → execution のトレース用テーブル初期化）
- 設定・環境変数の扱いや .env 自動読み込み（プロジェクトルート検出付き）

設計上の重要ポイント：
- ルックアヘッドバイアス防止（内部で datetime.today() 等を直接参照しない設計が多い）
- 冪等性（DB 保存は ON CONFLICT / 単一冪等キーなどで安全化）
- API 呼び出しはリトライ・バックオフやレート制御を備える
- 外部呼び出しに対するセキュリティ対策（RSS の SSRF 防止等）

---

## 主な機能一覧

- 環境設定: kabusys.config.Settings（.env 自動読み込み・優先順位制御）
- Data / ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（J-Quants からの差分取得と保存）
  - jquants_client: API 呼び出し、ページネーション、トークンリフレッシュ、保存関数（raw_prices, raw_financials, market_calendar 等）
  - calendar_management: 営業日判定 / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査テーブル（signal_events / order_requests / executions）の初期化ユーティリティ
  - news_collector: RSS 収集・正規化・SSRF対策・raw_news 保存
  - stats: zscore_normalize（クロスセクション正規化）
- AI:
  - news_nlp.score_news: ニュースを集計して OpenAI に投げ、ai_scores に書込む
  - regime_detector.score_regime: ETF 200日MA乖離とマクロニュースセンチメントを合成して market_regime に書込む
- Research:
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得

2. Python 仮想環境を作成（推奨）

   - macOS / Linux
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール

   本コードベースは以下の主要依存を想定しています（例）:
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

4. 環境変数を設定（.env ファイル推奨）
   - 必須:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API パスワード（発注等を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack チャネル ID
   - 任意 / 推奨:
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
     - DUCKDB_PATH: DuckDB のパス（既定: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite のパス（既定: data/monitoring.db）
     - KABUSYS_ENV: environment ("development" | "paper_trading" | "live")
     - LOG_LEVEL: ログレベル ("DEBUG","INFO",...)

   .env の自動読み込み:
   - プロジェクトルートの検出：.git または pyproject.toml を基準に __file__ の親を探索します。
   - 読み込み優先順位: OS環境変数 > .env.local > .env
   - 自動読み込みを無効化するには環境変数を設定:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（簡単な例）

まず DuckDB 接続を作成してから各処理関数を呼び出します。以下は基本的な利用例です。

- 日次 ETL を実行（J-Quants から差分取得・保存・品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY か引数で指定）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査専用 DB を別に作る場合）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn に対して order/signals/executions を挿入できるようになります
```

- 研究用ファクター計算例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄のモメンタム指標を含む dict のリスト
```

---

## 主要 API（抜粋）

- kabusys.config.settings: 環境設定取得（settings.jquants_refresh_token, settings.duckdb_path 等）
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
- kabusys.data.jquants_client:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.news_collector.fetch_rss(url, source)
- kabusys.data.calendar_management:
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.audit.init_audit_schema / init_audit_db

各関数は README の例のように DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

---

## ディレクトリ構成

（ソースは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント集約 & OpenAI 呼び出し（ai_scores 書込）
    - regime_detector.py     — ETF MA + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント・保存ロジック
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再公開
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - news_collector.py      — RSS 取得・前処理・保存
    - quality.py             — データ品質チェック
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - audit.py               — 監査テーブル初期化（signal / order / execution）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py — 将来リターン, IC, サマリー, rank
  - research/__init__.py

---

## 実装上の注意点

- Look-ahead バイアス防止:
  多くの関数は内部で現在時刻を直接参照せず、target_date を明示的に受け取る設計です。バックテスト等では必ず過去データのみを参照するよう注意してください。

- 冪等性:
  DB への保存は原則 ON CONFLICT / 重複キーで上書きする実装です。パイプラインの再実行に耐えるようになっています。

- API 呼び出し:
  J-Quants, OpenAI 呼び出しはリトライ・バックオフ・レート制御を実装しています。429 / ネットワーク断 / タイムアウトなどを考慮しているため、本番での一時エラーに耐性があります。

- セキュリティ:
  RSS 収集では URL 正規化・トラッキングパラメータ除去・SSRF 対策（内部ホスト拒否）・受信サイズ制限などを実装しています。

---

## 開発 / テスト

- 環境変数の自動ロードはプロジェクトルートを検出して .env/.env.local を読み込みます。テストで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し等はモジュール内部のラッパー関数をモックしてユニットテスト可能なように設計されています（例: kabusys.ai.news_nlp._call_openai_api を patch）。

---

必要に応じて README を拡張します（例: 具体的な DB スキーマ、運用例、CI / デプロイ手順、Slack 通知連携方法、kabu API 発注フローなど）。どの項目を詳しく追加したいか教えてください。
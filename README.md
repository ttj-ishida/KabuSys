# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群（KabuSys）。  
ETL、ニュース収集・NLP、リサーチ（ファクター計算）、監査ログ（監査テーブル）など、アルゴリズムトレーディング基盤に必要な主要機能を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0 (src/kabusys/__init__.py)

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質チェック・特徴量計算・ニュースNLP・市場レジーム判定・監査ログなどを一貫して扱えるライブラリです。J-Quants API からのデータ取得（株価、財務、カレンダー）、RSS ニュース収集、OpenAI を使ったニュースセンチメント評価、DuckDB への永続化・ETL パイプライン、監査テーブルの初期化などをサポートします。

設計方針の要点：
- ルックアヘッドバイアス（future leakage）を避ける実装（内部で date.today() を直接参照しない等）。
- DuckDB をデータストアとして使用、SQL と Python を組み合わせて効率的に処理。
- API 呼び出しに対するリトライやバックオフ、レート制御を内蔵。
- 冪等性を重視した保存処理（ON CONFLICT / upsert）。
- 外部サービス（OpenAI / J-Quants / RSS）とのインタフェースを抽象化。

---

## 主な機能一覧

- 環境設定管理
  - settings オブジェクトで環境変数を簡単取得（J-Quants トークン、kabu API パスワード、Slack トークン等）。
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。

- Data / ETL
  - J-Quants クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 市場カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - DuckDB への保存ユーティリティ（raw_prices, raw_financials, market_calendar 等）

- ニュース収集・NLP
  - RSS 収集（fetch_rss）: SSRF 対策・gzip 対応・追跡パラメータ除去等を実装
  - ニュースセンチメント（score_news）: OpenAI（gpt-4o-mini）を用いたバッチセンチメント & ai_scores への書込

- 市場レジーム判定
  - score_regime: ETF（1321）の200日MA乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ書き込む

- 監査ログ（Audit）
  - init_audit_schema / init_audit_db: signal_events, order_requests, executions 等の監査テーブルを初期化
  - 発注 → 約定までのトレーサビリティを UUID 連鎖で保持

- 研究用ユーティリティ（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（ソース内での型注釈 `Path | None` 等を使用）。
- DuckDB を利用（ローカルファイルまたは :memory:）。

1. リポジトリをクローン／プロジェクトルートへ移動

2. 依存パッケージをインストール（例: pip）
   ```
   pip install duckdb openai defusedxml
   ```
   - 必要に応じて pyproject.toml / requirements.txt を参照してインストールしてください。

3. パッケージを開発モードでインストール（オプション）
   ```
   pip install -e .
   ```

4. 環境変数 / .env の設定
   プロジェクトルートに .env を置くと自動で読み込まれます（読み込み順: OS環境変数 > .env.local > .env）。
   自動ロードを無効化したい場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

   最低限設定が必要な環境変数（コード参照）:
   - JQUANTS_REFRESH_TOKEN  （J-Quants リフレッシュトークン）
   - KABU_API_PASSWORD      （kabuステーション API 用パスワード）
   - SLACK_BOT_TOKEN        （Slack 通知用ボットトークン）
   - SLACK_CHANNEL_ID       （Slack 通知先チャンネルID）
   - OPENAI_API_KEY         （OpenAI 呼び出し時に環境変数で指定する場合）

   任意／デフォルト:
   - KABUSYS_ENV (development | paper_trading | live) — default: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
   - DUCKDB_PATH — default: data/kabusys.duckdb
   - SQLITE_PATH — default: data/monitoring.db
   - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡単なサンプル）

以下は主要ユースケースの最小例。DuckDB 接続は duckdb.connect() を使います。

- ETL（日次 ETL の実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントの評価（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数か api_key 引数で渡す
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以後 conn に対して監査テーブルが利用可能
```

- RSS フィード取得（ニュース収集ヘルパ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
# raw_news テーブル等への保存はプロジェクト内の別ロジックで行います
```

- 設定値の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- OpenAI 呼び出しはコスト・レート制限があるため、production では API キー管理・課金に注意してください。
- ETL や API 呼び出しはネットワーク依存のため、ログ・例外処理を適切に行ってください。

---

## ディレクトリ構成

リポジトリの主要なファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP / score_news
    - regime_detector.py            — 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント & 保存処理
    - pipeline.py                   — ETL パイプライン (run_daily_etl 等)
    - etl.py                        — ETL の公開型 (ETLResult)
    - calendar_management.py        — 市場カレンダー管理
    - news_collector.py             — RSS/ニュース収集
    - quality.py                    — データ品質チェック
    - stats.py                      — 汎用統計ユーティリティ
    - audit.py                      — 監査テーブル初期化
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility 計算
    - feature_exploration.py        — 将来リターン、IC、統計サマリー

その他:
- pyproject.toml / setup.py 等（プロジェクトルートに存在することを想定）
- .env / .env.local（任意）: 環境変数をプロジェクトルートに置くと自動読み込みされます

---

## 注意事項・運用上のヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。テスト時などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し（news_nlp, regime_detector）は外部 API に依存します。API 失敗時はフォールバックロジック（スコア 0.0 等）を持ちますが、rate limit、コスト、レスポンス検証に注意してください。
- J-Quants API はレート制限があります（モジュール内で制御あり） — id token は自動更新されます。
- DuckDB への executemany に空リストを渡すとエラーになるバージョン制約があるため、呼び出し側は空チェックが入っています。
- 監査ログテーブルは一度作成すると削除しない前提で設計されています。テーブル設計（DDL）を変更する場合は移行手順を検討してください。

---

もし README に追記したい「運用手順（cron / Airflow の例）」「CI / テストの実行方法」「pyproject.toml によるパッケージ化手順」などがあれば、環境や運用方針を教えてください。それに合わせて具体的な手順を追加します。
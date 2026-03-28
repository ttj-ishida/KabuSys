# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（データパイプライン、リサーチ、AI ニューススコアリング、監査ログ等）。  
設計上の主な方針は「ルックアヘッドバイアスの排除」「冪等性」「堅牢なエラーハンドリング／リトライ」「セキュリティ対策（SSRF 等）」です。

---

## 概要

KabuSys は以下の機能群を備えた内部ライブラリ群です。

- J-Quants API を使った株価/財務/カレンダーの差分 ETL（ページネーション・レート制御・リトライ対応）
- RSS ベースのニュース収集（SSRF 防御・トラッキングパラメータ除去・前処理）
- OpenAI を用いたニュースセンチメント / マクロセンチメント評価（JSON mode、バッチ処理・リトライ）
- リサーチ用ファクター計算（モメンタム／ボラティリティ／バリュー等）、特徴量探索ユーティリティ（将来リターン・IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 市場カレンダー管理（営業日判定・前後営業日の検索・夜間バッチ）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）と初期化ユーティリティ
- 設定管理（.env 自動ロード、環境変数取得のラッパー）

設計上、バックテスト等に使う場合は「Look-ahead bias（未来情報参照）」を生まないよう注意されています（多くの処理で datetime.today()/date.today() を直接参照しない実装）。

---

## 主な機能（抜粋）

- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - 差分取得・バックフィル・品質チェック
- データ取得・保存:
  - jquants_client: fetch_* / save_*（raw_prices, raw_financials, market_calendar など）
- ニュース:
  - news_collector.fetch_rss、記事前処理、raw_news / news_symbols への保存（冪等）
- AI:
  - ai.news_nlp.score_news（ニュースを銘柄毎にスコアリング）
  - ai.regime_detector.score_regime（ETF 1321 の MA200 とマクロセンチメント合成で市場レジーム判定）
- リサーチ:
  - research.factor_research: calc_momentum, calc_value, calc_volatility
  - research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize
- カレンダー:
  - data.calendar_management: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- 品質チェック:
  - data.quality: check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- 監査ログ:
  - data.audit.init_audit_schema / init_audit_db（DuckDB で監査用 DB を初期化）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型表記などを使用）
- システムに duckdb、openai、defusedxml 等をインストール可能であること

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   必要に応じて logging 等の追加パッケージを導入してください。

3. ソースを配置（ソースがリポジトリにある前提）
   - pip install -e .   （パッケージ化されている場合）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動的に読み込まれます（読み込み順: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須となる主な環境変数（.env の例）:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン

   # OpenAI
   OPENAI_API_KEY=sk-...

   # kabuステーション API（運用時）
   KABU_API_PASSWORD=...

   # Slack 通知（任意だが設定を想定）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXX

   # DB パス（オプション）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データディレクトリ作成
   - mkdir -p data

---

## 使い方（代表的な利用例）

ここでは DuckDB を用いた簡単な実行例を示します。適宜パスやキーを環境に合わせてください。

- DuckDB 接続を作り ETL を実行する例

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # ファイルがなければ作成
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニューススコアリング（OpenAI を使う）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> env OPENAI_API_KEY を参照
print("書き込み銘柄数:", n_written)
conn.close()
```

- 市場レジーム判定（MA200 とマクロセンチメント）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
conn.close()
```

- 監査ログ DB の初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って監査ログを記録
conn.close()
```

- リサーチ関数の例（モメンタム計算）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の辞書リスト
conn.close()
```

- RSS フィード取得（ニュースコレクタの単発利用）

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- OpenAI 呼び出しは retries を行いますが、API キーが未設定だと例外が発生します。api_key を直接引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- ETL / AI 処理は network IO を伴い、時間がかかる場合があります。ログレベルを調整して実行してください。

---

## 設定管理

- settings = kabusys.config.settings で各種設定（JQUANTS_REFRESH_TOKEN、KABU_API_BASE_URL、SLACK_BOT_TOKEN、DUCKDB_PATH など）にアクセスできます。
- KABUSYS_ENV は次のどれか: development / paper_trading / live。無効な値を与えると ValueError が発生します。
- LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか。

---

## ディレクトリ構成（主要ファイル）

（リポジトリが src レイアウトの場合）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存関数
    - pipeline.py                   — ETL パイプライン / run_daily_etl 等
    - etl.py                        — ETLResult の再エクスポート
    - news_collector.py             — RSS 取得・前処理
    - calendar_management.py        — 市場カレンダー管理
    - stats.py                      — zscore_normalize 等共通統計関数
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py        — calc_forward_returns / calc_ic / factor_summary / rank

---

## 実運用上の注意 / 備考

- DuckDB をメインのデータ格納に利用します（デフォルトパス: data/kabusys.duckdb）。バックアップや運用上の権限管理に注意してください。
- J-Quants API はレート制限があるため、jquants_client は内部でスロットリングとリトライを実装しています。ID トークンの自動リフレッシュも行います。
- news_collector は SSRF 対策（リダイレクト検査・プライベートホスト排除）や XML の安全な解析を行うよう実装されています。
- AI 呼び出しは JSON mode を期待したパース処理を行いますが、LLM の出力変化に対してはログでフォールバック（0.0 やスキップ）する設計です。
- production 環境（KABUSYS_ENV=live）では実際の発注ロジックと接続情報（kabu API password など）の取り扱いに十分注意してください。ここに含まれるコードは発注層そのものではなく、監査用スキーマや ETL / リサーチロジックが中心です。

---

もし README に追加したい実行スクリプト例（cron ジョブ例、Dockerfile、CI 設定など）があれば、その要件を教えてください。必要に応じて .env.example ファイルや簡易の systemd / cron 実行例も作成できます。
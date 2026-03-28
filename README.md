# KabuSys README

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ集です。ETL、ニュース収集、LLM を使ったニュースセンチメント、ファクタ計算、マーケットカレンダー管理、監査ログスキーマなどを含みます。

## プロジェクト概要
KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・カレンダーの差分取得（ETL）
- DuckDB を用いたデータ保存・品質チェック
- RSS ニュース収集と前処理
- OpenAI（gpt-4o-mini 相当）を使ったニュースセンチメント / 市場レジーム判定
- ファクター計算・特徴量探索（研究用）
- 発注・約定まで追跡可能な監査ログスキーマ（audit）
- 運用向けに環境変数管理・ロギング・フォールバック処理を実装

設計上の重点は「ルックアヘッドバイアス回避」「冪等性」「堅牢なリトライとフェイルセーフ」「DuckDB を前提とした効率的な SQL 処理」にあります。

---

## 主な機能一覧
- データ取得・保存
  - J-Quants から株価（daily_quotes）・財務データ・マーケットカレンダーの差分取得と DuckDB への冪等保存（jquants_client）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質管理
  - 欠損・重複・スパイク・日付不整合の検出（data.quality）
- ニュース
  - RSS 収集（news_collector）・前処理・raw_news 保存
  - OpenAI を用いた銘柄別ニュースセンチメント（ai.news_nlp.score_news）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定（ai.regime_detector.score_regime）
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等（research.feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）
- 運用ユーティリティ
  - 市場カレンダー判定・探索（data.calendar_management）
  - 監査ログスキーマの初期化と専用 DB 起動（data.audit.init_audit_db / init_audit_schema）

---

## 必須環境変数（最低限）
（.env または環境に設定してください）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（※発注周りを実装する際に使用）
- SLACK_BOT_TOKEN: Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / ai.score_regime を使う場合）

設定が足りない場合は Settings クラス（kabusys.config.settings）が ValueError を投げます。

.env 自動ロード:
- パッケージのルート（.git または pyproject.toml の階層）にある `.env` と `.env.local` を自動読み込みします（OS 環境変数が優先）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（開発環境向け）
1. Python バージョン
   - Python 3.10 以上を推奨（typing, match などの言語機能と互換性を前提）

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージ（最小）
   - duckdb
   - openai
   - defusedxml

   インストール例:
   ```
   pip install duckdb openai defusedxml
   ```

   ※ 実運用では requirements.txt を用意して pip install -r requirements.txt を推奨します。

4. (任意) パッケージの開発インストール（リポジトリルートに pyproject.toml / setup.cfg がある想定）
   ```
   pip install -e .
   ```

5. .env の準備
   - リポジトリの root に `.env` を作成し、上記必須変数を設定します。
   - 機密情報は `.env.local` に置き、`.gitignore` に入れる運用が推奨されます。

---

## 使い方（代表的な例）

以下は最低限の利用例です。実際はアプリケーションからこれら関数を呼び出して運用します。

1) DuckDB 接続を作って ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')  # settings.duckdb_path を使っても良い
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（OpenAI 必須）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None => OPENAI_API_KEY を参照
print(f"written scores: {n_written}")
```

3) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/monitoring.duckdb")
# init_audit_schema は内部で transactional=True を使ってテーブルを作成します
```

5) リサーチ関数（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
mom = calc_momentum(conn, target_date=date(2026,3,20))
# 結果は list[dict] 形式
```

6) jquants_client を直接使う（例: 上場銘柄取得）
```python
from kabusys.data.jquants_client import fetch_listed_info
records = fetch_listed_info(date_=date(2026,3,20))
```

---

## 主要 API の説明（抜粋）
- kabusys.config.settings
  - 環境変数をラップした Settings オブジェクト。例: settings.jquants_refresh_token, settings.duckdb_path
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...): 一連の ETL を実行して ETLResult を返す
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL ジョブ
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: API からのデータ取得
  - save_daily_quotes / save_financial_statements / save_market_calendar: DuckDB への保存（冪等）
  - get_id_token(refresh_token=None): トークン取得
- kabusys.data.news_collector
  - fetch_rss(url, source): RSS 取得とパース（SSRF 対策・サイズ制限・トラッキング除去あり）
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュースを銘柄ごとにまとめて OpenAI に投げ、ai_scores テーブルに書き込む
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF（1321）の MA200 乖離とマクロニュース（LLM）を合成して market_regime に書き込む
- kabusys.data.audit.init_audit_db(path)
  - 監査ログ用の DuckDB を作成しスキーマを初期化する

---

## 設計上の注意・運用メモ
- ルックアヘッドバイアス防止
  - 多くの関数は内部で date.today() を使わない、または target_date 未満のみ参照することでバックテストでのルックアヘッドを防止しています。
- 冪等性
  - J-Quants から得たデータは ON CONFLICT DO UPDATE により冪等的に保存されます。
- リトライ & Rate limit
  - J-Quants および OpenAI 呼び出しには適切なリトライ（指数バックオフ）とレート制御が組み込まれています。
- タイムゾーン
  - 監査ログでは TIMESTAMP を UTC で保存することを前提としています（init_audit_schema は SET TimeZone='UTC' を実行）。
- OpenAI 呼び出しのテスト
  - ai モジュールでは _call_openai_api を patch してユニットテストしやすい設計になっています。
- セキュリティ
  - news_collector は SSRF・XML Bomb 対策（defusedxml、ホスト検査、レスポンス上限）を実施しています。

---

## ディレクトリ構成
（主要ファイル・モジュールの一覧）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得/保存）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETLResult 再エクスポート
    - news_collector.py  — RSS 収集・正規化
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - stats.py           — zscore_normalize 等統計ユーティリティ
    - quality.py         — データ品質チェック
    - audit.py           — 監査ログスキーマ初期化・管理
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

---

## 開発・テストのヒント
- 自動環境変数読み込みを無効化する:
  - テスト時に .env の自動ロードを抑えたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しのモック:
  - ai.news_nlp._call_openai_api や ai.regime_detector._call_openai_api を unittest.mock.patch して擬似レスポンスでテストできます。
- DuckDB のインメモリ DB:
  - テスト時は `duckdb.connect(":memory:")` を使うことでファイル I/O を避けられます。
- ロギング:
  - settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。

---

以上が KabuSys の主要な README 内容です。追加で「運用手順」「Dockerfile」「CI/CD 設定」などのドキュメントが必要であれば、用途（ETL の定期実行、監査 DB のローテーション、Slack 通知フローなど）を教えてください。さらに詳しいサンプルやテンプレート（.env.example、docker-compose、systemd ユニット等）も作成できます。
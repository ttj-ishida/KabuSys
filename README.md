# KabuSys

日本株向け自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants / kabuステーション 等のデータ取得・ETL、ニュース収集とLLMによるニュースセンチメント、ファクター計算、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API からの株価・財務・カレンダー等データの差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集（SSRF対策・トラッキング除去等）と raw_news への保存
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score / マクロセンチメント）
- ETF（1321）の MA 乖離＋マクロセンチメント合成による市場レジーム判定
- 研究用のファクター計算（モメンタム／ボラティリティ／バリュー等）と前方リターン／IC 計算
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）のスキーマ初期化・管理
- 設定管理（環境変数／.env 自動読み込み）

設計方針として、ルックアヘッドバイアスを避けるために日付参照は明示的（date 引数）で行い、外部 API 呼び出しは必要な場所に限定、フェイルセーフ（API失敗時はゼロ扱いなど）を採用しています。

---

## 主な機能一覧

- データ取得・ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: レートリミット、リトライ、トークン自動リフレッシュ、ページネーション対応
- ニュース処理
  - RSS 収集（kabusys.data.news_collector）：トラッキング除去、SSRF対策、XML脆弱性対策、前処理
  - ニュース NLP（kabusys.ai.news_nlp）：銘柄ごとのセンチメントスコア算出、バッチ処理、レスポンスバリデーション
  - 市場レジーム判定（kabusys.ai.regime_detector）：ETF MA 乖離とマクロセンチメントの合成
- 研究用ユーティリティ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）
- データ品質（kabusys.data.quality）
  - missing_data / duplicates / spike / date_consistency / run_all_checks
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ（kabusys.data.audit）
  - init_audit_schema / init_audit_db（監査テーブル・インデックス作成）
- 設定管理（kabusys.config）
  - 環境変数・.env 自動ロード、settings オブジェクト経由で設定を取得

---

## セットアップ手順

想定 Python バージョン: 3.9+（型注釈や一部の構文を使用）

1. リポジトリをクローン／チェックアウト
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて）pip install -e . などプロジェクト化
   - ※ requirements.txt があればそちらを利用してください
4. 環境変数／.env の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知に使う場合
     - SLACK_CHANNEL_ID — Slack 通知チャンネル ID
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - OPENAI_API_KEY — OpenAI 呼び出しに利用する場合（関数引数で上書き可能）
   - 任意／デフォルト
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で自動 .env ロードを無効化
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトでの利用例です。必要に応じて API キーを関数に直接渡せます。

- 基本的な DB 接続（DuckDB）と設定取得
```
from kabusys.config import settings
import duckdb

conn = duckdb.connect(settings.duckdb_path)
```

- 日次 ETL を実行
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026,3,20))
print(res.to_dict())
```

- 個別 ETL（株価／財務／カレンダー）
```
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

- ニュースセンチメント（銘柄別 ai_scores へ書き込み）
```
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は env または api_key 引数
```

- 市場レジーム判定
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- ファクター計算（研究用）
```
from kabusys.research import calc_momentum, calc_volatility, calc_value
from datetime import date

moms = calc_momentum(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
```

- 前方リターン・IC・サマリー
```
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
fwd = calc_forward_returns(conn, date(2026,3,20), horizons=[1,5,21])
ic = calc_ic(moms, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(moms, columns=["mom_1m","mom_3m","ma200_dev"])
```

- 監査ログスキーマ初期化（監査専用DBを作る）
```
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

- データ品質チェック
```
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意点：
- 多くの API 呼び出し（OpenAI, J-Quants）は API キーを必要とします。関数の `api_key` / `id_token` 引数で注入可能で、引数が None の場合は環境変数から取得します。
- DuckDB の executemany に関する制約や欠損レコードハンドリングなど、ETL 実装は実運用を想定した安全策が組み込まれています。

---

## 設定（環境変数）

kabusys.config.Settings からアクセスします（settings オブジェクト）。

主な設定項目（環境変数名）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等）のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（LLM 呼び出しに使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化

.env ファイルの読み込み優先順位:
- OS 環境変数 > .env.local > .env

---

## ディレクトリ構成

パッケージの主要ファイルと概略は以下の通りです。

- src/kabusys/
  - __init__.py — パッケージ情報（version, __all__）
  - config.py — 環境変数 / .env 管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄別 ai_scores）
    - regime_detector.py — 市場レジーム判定（1321 MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 収集・前処理・保存
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - quality.py — データ品質チェック
    - stats.py — zscore_normalize 等統計ユーティリティ
    - audit.py — 監査ログテーブル初期化・audit DB ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility の計算
    - feature_exploration.py — forward returns / IC / summary / rank

この README は主要 API と設計意図のみをまとめたものです。各モジュールの詳細（引数仕様・戻り値・エラー挙動）はソース内の docstring を参照してください。

---

## 運用上の注意

- Look-ahead バイアスに注意：関数は多数が target_date 引数ベースで実装されており、内部で datetime.today()/date.today() を直接参照しない設計ですが、呼び出し側が日付を誤るとバイアスが発生します。バックテスト用途では日付管理を厳密に行ってください。
- API キー漏洩対策：.env をコミットしないでください（.gitignore を利用）。
- OpenAI 呼び出しはコストとレート制限に注意してください（バッチ化とリトライロジックあり）。
- J-Quants はレート制限対応（120 req/min）を行っていますが、運用環境でも追加のスロットリングが必要な場合があります。

---

必要であれば、具体的なワークフロー（例：日次バッチ cron スクリプト、Slack 通知フロー、監査ログの読み出しクエリなど）のサンプルや、各モジュールの詳細な API リファレンスを作成します。どの部分を優先して追加ドキュメント化するか教えてください。
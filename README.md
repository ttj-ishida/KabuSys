# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI を利用したセンチメントスコアリング）、市場レジーム判定、監査ログなどのユーティリティを提供します。

-----

## 目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（.env）
- 使い方（簡易例）
- よく使う API / モジュール
- ディレクトリ構成

-----

## プロジェクト概要
KabuSys は日本株のデータプラットフォーム／リサーチ／自動売買を支援する内部ライブラリ群です。  
主に以下を目的としています。

- J-Quants API からの株価・財務・市場カレンダーの差分取得と DuckDB への保存（ETL）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）とニュースに基づく銘柄別 AI スコアリング（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化／管理

設計上の特徴として、ルックアヘッドバイアスを避ける設計、DuckDB による効率的な SQL ベース処理、外部 API 呼び出しのリトライ・フェイルセーフが組み込まれています。

-----

## 機能一覧
- data.jquants_client: J-Quants API クライアント（ページネーション／レート制限／トークン刷新）
- data.pipeline: 日次 ETL（市場カレンダー・日足・財務）と ETL 結果表現（ETLResult）
- data.quality: データ品質チェック（missing / spike / duplicates / date consistency）
- data.calendar_management: 営業日判定・next/prev_trading_day などのカレンダー機能
- data.news_collector: RSS 取得／前処理／保存（SSRF 等対策あり）
- data.audit: 監査ログスキーマの初期化（audit tables / indexes）
- research.factor_research, research.feature_exploration: ファクター計算・IC/統計分析
- ai.news_nlp: ニュース記事を LLM で銘柄ごとに採点（score_news）
- ai.regime_detector: ETF の MA とマクロニュースで日次の市場レジームを判定（score_regime）
- data.stats: zscore 正規化などの統計ユーティリティ

-----

## 必要条件
- Python 3.10 以上（型アノテーションに | 演算子を利用）
- 以下の主な依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, datetime, json, logging 等）

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

-----

## セットアップ手順（ローカル開発向け、例）
1. リポジトリをクローンしてプロジェクトルートへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - あるいはプロジェクトに requirements.txt があれば:
     - pip install -r requirements.txt
4. パッケージを開発モードでインストール（任意）
   - pip install -e .
5. .env を作成（下の「環境変数」参照）
6. データベースフォルダ作成（必要に応じて）
   - mkdir -p data

注意: パッケージは src/ 配下に実装されています（典型的な src layout）。

-----

## 環境変数（.env）
パッケージ起動時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします（CWD ではなくファイル位置からプロジェクトルートを検索）。テスト用に自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須は明示）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード（本プロジェクト中の API 呼び出しに使用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI を利用する際に使う API キー（ai モジュール使用時）
- KABUSYS_ENV — 実行環境: one of "development", "paper_trading", "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

-----

## 使い方（簡易例）

共通: settings を使って設定を参照できます
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

DuckDB 接続を作成する
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースの AI スコアを算出して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数で設定していること
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
```

市場レジーム判定（market_regime テーブルに書き込み）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログスキーマ初期化（DuckDB を監査 DB として初期化）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# init_audit_db は初期化済みの接続を返します
```

品質チェックを手動で走らせる
```python
from kabusys.data import quality
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

ニュース RSS 取得（保存フローはプロジェクト内の仕組みに従って実装）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a['datetime'], a['title'])
```

注意:
- ai モジュール（news_nlp / regime_detector）は OpenAI API を使用します。API キーは OPENAI_API_KEY に設定するか、各関数の api_key 引数で渡してください。
- jquants_client は J-Quants のリフレッシュトークンを必要とします（JQUANTS_REFRESH_TOKEN）。

-----

## よく使う API / モジュール（サマリ）
- kabusys.config.settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live など
- kabusys.data.jquants_client
  - fetch_daily_quotes, save_daily_quotes
  - fetch_financial_statements, save_financial_statements
  - fetch_market_calendar, save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(path)

-----

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下。抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数／設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）で ai_scores を作成
    - regime_detector.py      — 市場レジーム判定（1321 MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存ロジック
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult 再エクスポート
    - quality.py              — データ品質チェック
    - calendar_management.py  — 市場カレンダー管理 / 営業日判定
    - news_collector.py       — RSS 収集・正規化・保存ユーティリティ
    - stats.py                — zscore などの統計ユーティリティ
    - audit.py                — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Value/Volatility 等の計算
    - feature_exploration.py  — 将来リターン、IC、統計サマリー等

-----

## 運用上の注意 / ヒント
- OpenAI API 呼び出しにはレート制限／費用が伴うため、バッチ頻度やバッチサイズを運用に合わせて調整してください。
- jquants_client にはレートリミッターとリトライが組み込まれていますが、大量のデータ取得時は API 制限に注意してください。
- ETL は部分的に失敗しても他のステップを続行する設計です。ETLResult のエラー／quality_issues を監視してください。
- データベースのパス（DUCKDB_PATH 等）は .env で管理すると便利です。
- テスト中に自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

-----

この README はコードベースの要点と利用方法をまとめたものです。詳細な関数引数や返り値、動作上の制約（例: ルックアヘッドバイアス対策）は各モジュールのドキュメンテーション文字列（docstring）を参照してください。ご要望があれば、導入手順の自動化スクリプト例や具体的な ETL 運用例（cron / Airflow）も追加で作成します。
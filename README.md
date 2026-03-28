# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants 経由の株価・財務・カレンダ取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（発注/約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株を対象としたデータ基盤および研究・自動売買支援モジュール群を含む Python パッケージです。主に以下を目的としています。

- J-Quants API を用いた市場データ（株価、財務、上場情報、JPX カレンダー）の差分 ETL
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント（銘柄別 / マクロ）評価
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- 監査（audit）テーブルの初期化とトレーサビリティ（signal → order_request → executions）
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上の特徴：
- ルックアヘッドバイアス対策（target_date に基づく処理、現在時刻の直接参照を最小化）
- 冪等性（DB 保存は ON CONFLICT / DELETE→INSERT 等で安全に上書き）
- フェイルセーフ（外部 API 失敗時はスキップ/デフォルト値にフォールバック）

---

## 機能一覧

主要なモジュールと代表的な機能：

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）
  - 環境変数ラッパー（settings）
- kabusys.data
  - jquants_client: J-Quants API 呼び出し / ページネーション / DuckDB 保存関数
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - news_collector: RSS 取得・前処理・保存
  - calendar_management: 営業日判定 / calendar_update_job
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査テーブル初期化・専用 DB の作成（init_audit_schema / init_audit_db）
  - stats: zscore_normalize
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）MA200 乖離とマクロ記事の LLM 結果から市場レジームを判定し market_regime に書き込む
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件（依存ライブラリ）

本 README はリポジトリ内のコードから推測した依存項目です。実際の setup.py / pyproject.toml を確認してください。

- Python 3.10+
- duckdb
- openai
- defusedxml
- その他標準ライブラリ（urllib, json, logging など）

---

## 環境変数（主なもの）

プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（環境依存で上書き可）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（Settings._require により参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション等のパスワード（使用する場合）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

オプション:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または pyproject.toml に従い pip install -e .

   必須パッケージ例:
   - pip install duckdb openai defusedxml

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数として設定してください。

5. DuckDB 用ディレクトリを作る（必要に応じて）
   - mkdir -p data

---

## 使い方（代表例）

下記は Python スクリプト / REPL からの呼び出し例です。エラー処理やログ設定は用途に合わせて追加してください。

- ETL（日次差分 ETL 実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（ai_scores テーブルへ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {n_written}")
```

- 市場レジーム判定（market_regime へ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監査テーブル初期化（専用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_kabusys.duckdb")
# conn を使って監査ログを書き始められます
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

注意:
- OpenAI API を用いる関数は `OPENAI_API_KEY` 環境変数か api_key 引数が必要です。
- ETL 周りは J-Quants の認証トークンを内部で取得するため `JQUANTS_REFRESH_TOKEN` が必要です。

---

## ディレクトリ構成（主なファイル・モジュール）

リポジトリ内の主要なソースは `src/kabusys` 配下に配置されています。抜粋：

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py (ETLResult エイリアス)
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記は主要モジュールの一覧です。詳しくは各ファイルの docstring を参照してください。）

---

## 開発・運用上の注意

- ルックアヘッドバイアス防止のため、関数は target_date ベースで設計されています。バックテストや研究用途ではこれを順守してください。
- DuckDB に対する executemany などの制約（バージョン依存）に注意して実装されていますが、運用環境の DuckDB バージョンでの動作確認を推奨します。
- ニュース収集・RSS パーシングには SSRF 対策や XML の安全パーサ（defusedxml）などセキュリティ対策を実装しています。外部フィードを追加する際も同様の注意を継続してください。
- OpenAI / J-Quants 等の外部 API はレート制限や課金が発生します。API キーの管理、呼び出し頻度の制御を行ってください。

---

もし README に加えたい実行例・設定例・運用手順（CI や cron ジョブ、Docker 化等）があれば教えてください。詳細を追加して README を拡張します。
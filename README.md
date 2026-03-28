# KabuSys

日本株向けのデータ基盤・自動売買補助ライブラリです。  
ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（監査用 DuckDB スキーマ）などのユーティリティを提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）
- 使い方（基本例）
- 主要 API の説明
- ディレクトリ構成
- 注意事項 / 設計ポリシー

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量生成・ニュース NLP・レジーム判定・監査トレースを行うための内部ライブラリ群です。  
J-Quants API を用いた日次 ETL、RSS ニュース収集と OpenAI を用いたセンチメント解析、DuckDB を中心とした永続化・品質チェック、取引監査テーブル初期化などを含みます。

設計上の特徴：
- DuckDB を中心とした軽量な組み込み DB
- Look-ahead バイアス回避に配慮した日付処理
- API 呼び出しに対するリトライ / レート制御・フェイルセーフ
- 各処理は冪等（idempotent）に設計

---

## 主な機能一覧

- データ ETL（J-Quants からの株価・財務・カレンダー取得）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック（欠損・重複・スパイク・日付不整合）
  - quality.run_all_checks / check_missing_data / check_spike / ...
- ニュース収集（RSS）と前処理
  - news_collector.fetch_rss / preprocess_text
- ニュース NLP（OpenAI を用いた銘柄別センチメント）
  - ai.news_nlp.score_news
- 市場レジーム判定（ETF 1321 の MA とマクロ記事の LLM スコアの合成）
  - ai.regime_detector.score_regime
- リサーチ用ファクター計算
  - research.calc_momentum / calc_volatility / calc_value / feature_exploration.*
- 統計ユーティリティ
  - data.stats.zscore_normalize
- 監査ログ（order/signal/execution）スキーマ初期化
  - data.audit.init_audit_db / init_audit_schema
- J-Quants クライアント（rate limiting / token refresh / save_* helpers）
  - data.jquants_client.*

---

## セットアップ手順

前提：
- Python 3.9+（typing|annotations の利用を考慮）
- ネットワーク接続（J-Quants / OpenAI / RSS 取得）

インストール（ローカル開発）例：
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※プロジェクトに requirements ファイルがある場合はそれを使ってください。  
   ※パッケージ名は実際の依存に応じて調整してください。

3. 開発中はソースツリーで editable インストール可能:
   - pip install -e .

ファイル配置：
- 環境変数はプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化可）。

---

## 環境変数（必須 / 主要）

自動ロードの挙動：
- プロジェクトルートはこのパッケージの位置から `.git` または `pyproject.toml` に基づいて検出します。
- ルート検出に成功した場合、`.env`（上書きしない）→ `.env.local`（上書き）を順に読み込みます。
- また OS 環境変数は優先されます。
- 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（コード内で参照されるもの）：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API を使用する場合（AI モジュール）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 動作環境（development / paper_trading / live、default: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例（.env）:
KABUSYS_ENV=development
LOG_LEVEL=INFO
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...

---

## 使い方（基本例）

以下は Python REPL / スクリプトからの簡単な利用例です。

1) DuckDB 接続を作る（デフォルトファイル path を使う場合）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行する（J-Quants からデータ取得→保存→品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI APIキーを api_key 引数で直接渡すことも可能
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

4) 市場レジーム判定（ETF 1321 とマクロ記事の合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ専用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 必要に応じて audit_conn を使って監査テーブルへ書き込みを行う
```

6) ファクター計算（研究用）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "ma200_dev"])
```

---

## 主要 API（簡易説明）

- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
  - 市場カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック を実行して ETLResult を返します。

- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - J-Quants API からのデータ取得（ページネーション対応）。低レベル API。

- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - DuckDB への永続化（ON CONFLICT DO UPDATE により冪等）。

- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news + news_symbols を集約し、OpenAI（gpt-4o-mini 想定）で銘柄ごとのスコアを ai_scores に書き込みます。

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の 200 日 MA 乖離とマクロニュース LLM スコアを合成して market_regime テーブルに書き込みます。

- kabusys.data.quality.run_all_checks(conn, target_date, ...)
  - データ品質チェックを全て実行し QualityIssue のリストを返します。

- kabusys.data.audit.init_audit_db(path)
  - 監査ログ用 DuckDB を作成し監査スキーマを初期化します。

---

## ディレクトリ構成

（src/kabusys を起点とした主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数/設定の読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py                  - ニュース NPL（銘柄ごとスコア）および OpenAI 呼び出しラッパー
    - regime_detector.py           - 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py            - J-Quants API クライアント + Save helpers
    - pipeline.py                  - ETL パイプライン（run_daily_etl など）
    - etl.py                       - ETLResult の再エクスポート
    - news_collector.py            - RSS フィード収集 / 前処理
    - calendar_management.py       - マーケットカレンダー管理（営業日判定など）
    - quality.py                   - データ品質チェック
    - stats.py                     - 統計ユーティリティ（zscore 等）
    - audit.py                     - 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           - モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py       - 将来リターン / IC / サマリー等
  - research/*（その他の研究用ユーティリティ群）...
  - その他（strategy / execution / monitoring 用の名前空間は __all__ に含むが省略）

---

## 注意事項 / 設計ポリシー

- Look-ahead バイアス対策：多くの関数は date.today() や datetime.now() に依存しない設計（呼び出し側で target_date を指定）。
- API フォールトトレランス：OpenAI や J-Quants の呼び出しはリトライやバックオフ、タイムアウトを備えています。失敗時のフェイルセーフ（スコア 0.0 など）を取り入れている箇所があります。
- 冪等性：DB への保存は基本的に ON CONFLICT（UPSERT）で行い、再実行可能な ETL を意図しています。
- セキュリティ：
  - news_collector は SSRF 対策（リダイレクト検査・プライベートホスト検出）や XML の安全パース（defusedxml）を採用しています。
  - J-Quants クライアントは rate limiting を行います（120 req/min）。
- テスト：OpenAI 呼び出し等は内部関数（_call_openai_api など）を unittest.mock.patch で差し替え可能にしてあります。

---

何か追加してほしいセクション（例: CLI 実行例、詳細な .env.example、ユニットテストの実行方法）があれば教えてください。README を用途に合わせて拡張します。
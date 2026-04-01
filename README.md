# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群（KabuSys）。  
J-Quants / JPX のデータを取得して DuckDB に蓄積し、ニュースNLP・市場レジーム判定・ファクター計算などを行うためのユーティリティと ETL/監査機能を提供します。

主な用途
- データプラットフォーム（株価・財務・市場カレンダー）の差分 ETL
- ニュース収集・NLP による銘柄センチメント算出
- 市場レジーム判定（ETF + マクロニュースの合成）
- ファクター計算・特徴量解析（リサーチ用途）
- データ品質チェック（欠損・スパイク・重複・日付整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- J-Quants API クライアント（レート制御・リトライ・トークン更新）

---

## 機能一覧（抜粋）

- data/
  - jquants_client: J-Quants API 呼び出し（ページング、リトライ、レート制御）
  - pipeline: 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - news_collector: RSS 取得・前処理（SSRF 対策・トラッキング除去）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブル初期化 / 専用 DB 初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）
- ai/
  - news_nlp.score_news: ニュースを LLM（OpenAI）でセンチメント評価し ai_scores に書込
  - regime_detector.score_regime: ETF の MA やマクロニュース LLM を合成して market_regime に書込
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算・IC（スピアマン）・要約等
- config: 環境変数管理（.env 自動ロード、必須キーチェック）
- jquants_client や news_collector は冪等／フェイルセーフ設計（部分失敗でも継続）

---

## セットアップ

前提
- Python 3.10 以上を推奨（typing の縦棒合併型などを使用）
- DuckDB, OpenAI Python SDK, defusedxml などを利用

例: 仮想環境を作って必要パッケージをインストールする一例

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発インストール（パッケージ化している場合）
# pip install -e .
```

requirements の例（プロジェクトに requirements.txt が無い場合の参考）
- duckdb
- openai>=1.0
- defusedxml

環境変数 / .env
- パッケージはプロジェクトルートにある `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須の環境変数（Settings が参照するもの）:
  - JQUANTS_REFRESH_TOKEN (J-Quants リフレッシュトークン)
  - SLACK_BOT_TOKEN (Slack 通知に使う場合)
  - SLACK_CHANNEL_ID (Slack 通知に使う場合)
  - KABU_API_PASSWORD (kabu ステーション API を使う場合)
- OpenAI API キーは関数引数で上書き可能ですが、未指定時は環境変数 `OPENAI_API_KEY` を参照します。

例 .env (参考)

```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は Python 側から `from kabusys.config import settings` でアクセスできます（例: settings.duckdb_path）。

---

## 使い方（基本例）

以下はライブラリを使って日次 ETL を実行したり、AI スコアを計算する最小例です。

1) DuckDB 接続を作る（設定からパスを取得）

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する（パイプライン）

```python
from kabusys.data.pipeline import run_daily_etl

# target_date を指定するか省略して今日を使う
result = run_daily_etl(conn, target_date=None, id_token=None)
print(result.to_dict())
```

3) ニュースセンチメントを計算して ai_scores テーブルへ書き込む

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーを環境変数に設定しておくか、api_key 引数で渡す
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written codes: {n}")
```

4) 市場レジーム判定（market_regime へ書き込み）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログスキーマ初期化（監査用 DuckDB を作成して初期化）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または :memory:
# audit_conn = init_audit_db(":memory:")
```

6) RSS を取得して記事を調べる（保存処理は別関数で行う想定）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点
- OpenAI 呼び出しを行う機能は API 呼び出し回数・料金が発生します。テスト時は api_key を差し替えるか、該当関数の内部呼び出しをモックしてください（モジュール内で差し替え可能な設計になっています）。
- run_daily_etl 等は内部で market_calendar を参照して営業日を調整します。バックテスト環境で使用する際は Look-ahead バイアスに注意してください（関数設計はバイアス抑制を意識しています）。

---

## よく使う API / 関数（まとめ）

- ETL
  - kabusys.data.pipeline.run_daily_etl(conn, target_date, id_token, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- データ取得 / 保存
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
- ニュース / AI
  - kabusys.data.news_collector.fetch_rss(url, source)
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 監査
  - kabusys.data.audit.init_audit_schema(conn, transactional=False)
  - kabusys.data.audit.init_audit_db(db_path)
- リサーチ
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.research.calc_volatility(conn, target_date)
  - kabusys.research.calc_value(conn, target_date)
  - kabusys.research.calc_forward_returns(conn, target_date)

---

## 設定/運用上のポイント

- 環境の切り替え: settings.env で development / paper_trading / live を指定できます（環境変数 KABUSYS_ENV）。
- ログレベル: settings.log_level で制御（ENV LOG_LEVEL、デフォルト INFO）。
- .env の優先順:
  - OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化（テスト用）
- OpenAI / J-Quants のリトライ・バックオフ・レート制御は実装済み（ライブラリ側で取り扱い）。
- ニュース収集は SSRF 対策（リダイレクト検査・プライベートホストブロック）やレスポンスサイズ上限を実装。

---

## ディレクトリ構成

（主要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py      — RSS 取得・前処理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化 / init_audit_db
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility 等
    - feature_exploration.py — forward returns / IC / summary

---

## 開発・テストについて

- モジュール内で外部 API 呼び出し箇所（OpenAI, J-Quants, urllib 等）はモック可能なように設計されています。ユニットテストでは該当関数を patch して副作用を抑えてください。
- DuckDB を使う関数は接続オブジェクトを受け取るため、":memory:" 接続で一時 DB を作ってテスト可能です。
- LLM を使う部分はレスポンス検証を厳密に行い、エラー時はフォールバック（スコア 0.0 など）する実装になっています。

---

## ライセンス / 責任範囲

本 README はコードベースの説明を目的としています。実運用に当たっては API キー・資金管理・発注ロジック等の安全性・法規制を十分に確認してください。実際の売買・本番運用は細心の注意を払って行ってください。

---

質問や README に追記したい情報（CI/デプロイ手順、具体的な .env.example など）があれば教えてください。README を元に短い .env.example や起動スクリプト例も作成できます。
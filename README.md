# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants / RSS / OpenAI を用いたデータ収集・ETL・NLP・リサーチ・監査ログ機能を提供します。  
設計上の主な方針は次の通りです：ルックアヘッドバイアスを避ける、ETL/DB操作は冪等性を保つ、外部API呼び出しはリトライ/フォールバックを備える。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単なコード例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームおよび自動売買システムのためのモジュール群です。主に以下を目的とします。

- J-Quants API からの株価・財務・マーケットカレンダー等の差分 ETL（DuckDB へ保存）
- RSS ニュース収集と記事の前処理（raw_news 保存）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロセンチメント評価（AI スコアの生成）
- 市場レジーム判定（ETF とマクロセンチメントの合成）
- ファクター計算・特徴量探索（研究用途）
- 監査ログ（signal → order_request → execution までのトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計の特徴：
- バックテストでのルックアヘッドを避ける（date 引数ベース、datetime.now を直接参照しない関数が多い）
- DuckDB を中心としたローカルデータ管理（ファイル or :memory:）
- 冪等な DB 保存（ON CONFLICT / INSERT…DO UPDATE）
- 外部 API のリトライ・レート制御・フォールバック実装

---

## 機能一覧

主なモジュールと機能（抜粋）

- kabusys.config
  - .env 自動読み込み（プロジェクトルートの .git または pyproject.toml を検出）
  - 環境変数ラッパー（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API の取得・保存（fetch_* / save_*）
  - pipeline: 日次 ETL ランナー（run_daily_etl）
  - news_collector: RSS 収集・前処理（fetch_rss）, raw_news 保存ロジック
  - calendar_management: JPX カレンダー管理・営業日判定
  - quality: 品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - audit: 監査ログテーブルの初期化・監査用 DB ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）MA200 乖離とマクロセンチメントの合成による市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提
- Python 3.10+（typing の | や型アノテーションを使用）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（OpenAI API を使用する機能のみ）
- defusedxml（RSS パースの安全性のため）

例：仮想環境を作成して依存をインストールする

```bash
git clone <このリポジトリ>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 必要に応じて追加: (例) pip install slack-sdk
```

環境変数（.env）の準備
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動でロードされます（優先順：OS環境 > .env.local > .env）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用など）。

主要な環境変数（必須/任意）
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants の refresh token（jquants_client が使用）
- OPENAI_API_KEY（AI 機能を使う場合、score_news/score_regime で利用可能）
- KABU_API_PASSWORD（kabuステーション API 用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知用。プロジェクト内で参照）
- DUCKDB_PATH（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH（監視 DB 用、デフォルト "data/monitoring.db"）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/...）

例 .env（プロジェクトルート）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

DB 初期化（監査用 DB など）
- 監査ログ専用の DB を初期化する例：

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

---

## 使い方（簡単なコード例）

以下はよく使うユースケースの例です。各関数は詳細な引数・挙動をドキュメント（関数 docstring）で確認してください。

1) DuckDB 接続を作成して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントをスコアして ai_scores に書き込む

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

score_news / score_regime はデフォルトで環境変数 `OPENAI_API_KEY` を参照します。引数 `api_key` で上書きできます。

3) 市場レジーム判定

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 研究用ファクター計算（例：モメンタム）

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

5) RSS 取得（ニュース収集）

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

---

## 注意点 / 実運用上のヒント

- OpenAI / J-Quants API はレート制限や課金に注意してください。ローカルでは環境変数で API キーを管理します。
- ETL は冪等になるように設計されていますが、初回ロードやスキーマ変更時はバックアップをとってから実行してください。
- DuckDB の executemany はバージョン依存の挙動があるため、各関数は空リストの executemany を避ける工夫をしています。
- テスト時には `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境依存を切ると安定します。
- news_collector は SSRF 対策・レスポンスサイズ制限・XML パースの安全化（defusedxml）を行っています。

---

## ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメントスコアリング（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API client（fetch/save_*）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - news_collector.py             — RSS 収集・前処理（fetch_rss）
    - calendar_management.py        — マーケットカレンダー管理
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログスキーマ・初期化
    - etl.py                        — ETL インターフェース再エクスポート
    - stats.py                      — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py            — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py        — 将来リターン, IC, 統計サマリー, rank
  - research/feature_exploration.py
  - その他モジュール（strategy、execution、monitoring 等は __all__ に含まれる想定）

（上記は現行コードベースの主要モジュールの抜粋です）

---

## 最後に

詳細な関数仕様や設計方針は各ソースコードの docstring に記載されています。実運用・バックテストでの利用時は docstring の注記（特にルックアヘッド防止に関する注意）を必ず確認してください。質問やドキュメント追記の要望があれば教えてください。
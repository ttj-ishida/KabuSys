# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
データETL、ニュース収集とLLMベースのニュース分析、市場レジーム判定、ファクター計算、監査ログ（トレーサビリティ）など、取引システムを構築するためのユーティリティを提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含みます。

- J-Quants API を用いた市場データ（株価・財務・カレンダー）の差分取得・保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF/サイズ制限等の安全対策内蔵）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント解析（銘柄別 / マクロ）
- マクロ＋テクニカル（ETF MA200乖離）を組み合わせた市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）および探索用統計関数
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 取引フロー向けの監査ログ（signal / order_request / executions）用DDLと初期化関数
- DuckDB を想定したデータ永続化（冪等保存ロジック）

設計上の特徴：
- Look-ahead バイアス対策（date の扱いに注意）
- ETL/保存は冪等（ON CONFLICT / UPSERT）で実装
- API 呼び出しに対するリトライ・レート制御・フォールバックを実装
- テストしやすいように API 呼び出しポイントの差し替えを想定

---

## 主な機能一覧

- 環境設定読み込み / settings（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数のラッピングプロパティ
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_* / save_*（ページネーション・トークン更新・レート制御）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、ID 生成、SSRF 対策、raw_news 保存
- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合検出
- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize
- Research ツール（kabusys.research）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
- AI モジュール（kabusys.ai）
  - score_news: 銘柄別ニュースセンチメントを ai_scores へ書込
  - score_regime: ETF(1321) MA200 とマクロ記事の LLM センチメントを合成して market_regime へ書込
- 監査ログ初期化（kabusys.data.audit）
  - init_audit_schema / init_audit_db

---

## セットアップ手順

前提
- Python 3.10+（型注釈に Union 表記等を使用）
- DuckDB（Python パッケージ）、openai（OpenAI SDK）、defusedxml などが必要

推奨インストール（例）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# その他プロジェクトで必要なライブラリをインストールしてください
```

環境変数
- このライブラリは複数の環境変数を参照します。主なものは以下です。

必須（実行する機能に依存）:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN        — Slack 通知を使う場合
- SLACK_CHANNEL_ID       — Slack チャンネルID
- KABU_API_PASSWORD      — kabuステーション API パスワード（発注機能を使う場合）
- OPENAI_API_KEY         — OpenAI API キー（AI スコアリングを利用する場合）

任意 / デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — 実行環境。デフォルト: development
- LOG_LEVEL (DEBUG | INFO | ...) — ログレベル。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（テスト時に有用）

.env / 自動読み込み
- パッケージ import 時（kabusys.config）が、プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を検出すると、
  .env を読み込み、続いて .env.local を上書きします（OS 環境変数は保護されます）。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（基本例）

以下は最小限の使用例。DuckDB 接続を作成して ETL 実行、AI スコアリング、レジーム判定などを呼び出します。

1) DuckDB 接続を作る（デフォルトの DUCKDB_PATH を使う）

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# 明示的に target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントを計算して ai_scores テーブルに書く

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数か api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

4) 市場レジームをスコアリングして market_regime テーブルへ書く

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ用の DB 初期化

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# もしくは既存接続にスキーマを追加
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

注意点:
- OpenAI 呼び出しはネットワークおよび課金が発生します。テスト時はモックしてください。
- API キーが未設定の場合、score_news/score_regime は ValueError を投げます。
- ETL / 保存は冪等設計ですが、接続・テーブルが事前に正しく用意されていることを確認してください。

---

## 主要な API / エントリポイント（まとめ）

- kabusys.config.settings — 環境設定アクセサ
- kabusys.data.pipeline.run_daily_etl(...) — 日次ETLパイプライン
- kabusys.data.jquants_client.fetch_* / save_* — J-Quants 取得/保存
- kabusys.data.news_collector.fetch_rss(...) — RSS 取得ユーティリティ
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) — 銘柄別ニューススコア
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定
- kabusys.research.* — ファクター計算 / 特徴量探索ユーティリティ
- kabusys.data.audit.init_audit_schema / init_audit_db — 監査ログ初期化

---

## ディレクトリ構成

（リポジトリの主要ファイル/モジュール。実際のプロジェクトでは tests や docs などが追加される想定）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境設定・.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                    — 銘柄ニュース NLP スコアリング（OpenAI）
    - regime_detector.py             — 市場レジーム判定（MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL 結果データクラス再エクスポート
    - news_collector.py              — RSS 収集 / 前処理 / 保存
    - calendar_management.py         — マーケットカレンダー管理・営業日ロジック
    - stats.py                       — 共通統計ユーティリティ（zscore）
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログDDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py             — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py         — 将来リターン・IC・統計サマリー等

---

## 注意事項・設計上の留意点

- Look-ahead バイアス防止：内部関数は datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を与える設計です（バックテスト用に重要）。
- 冪等性：DB 保存関数は可能な限り ON CONFLICT DO UPDATE（UPSERT）や INSERT ... ON CONFLICT を使用して冪等にしています。
- エラーハンドリング：API 呼び出しはリトライ（指数バックオフ）・タイムアウトを考慮。LLM 呼び出しや外部 API の失敗は安全側のデフォルト（例: macro_sentiment=0）にフォールバックしサービス全体の停止を避けます。
- セキュリティ：news_collector には SSRF 対策、XML パースの安全化（defusedxml）、レスポンスサイズ制限などの防御ロジックがあります。
- テスト：OpenAI / HTTP 呼び出しポイントはモック差し替えが想定されています（関数単位で差し替え可能）。

---

必要に応じて README に追記します（例：開発環境構築、詳細なスキーマ、SQL スニペット、運用手順、CI 設定など）。どの項目を詳しく追加しますか？
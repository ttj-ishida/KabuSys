# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ、J-Quants クライアントなど、トレーディングシステム構築に必要な基盤機能を提供します。

---

## 概要

KabuSys は以下の主要機能を持つ Python パッケージです。

- J-Quants API からの株価・財務・カレンダーの差分取得（Rate limit / retry 対応）
- DuckDB を用いた ETL パイプライン（差分取得・冪等保存・品質チェック）
- RSS ニュース収集（SSRF 対策・前処理）と銘柄紐付け
- OpenAI を用いたニュースセンチメント / 市場レジーム判定（gpt-4o-mini / JSON mode 想定）
- ファクター計算（Momentum / Value / Volatility 等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）用のスキーマ初期化ユーティリティ
- カレンダー管理（営業日判定 / next/prev_trading_day 等）
- 環境変数ベースの設定管理（.env の自動読み込みをサポート）

設計上、ルックアヘッドバイアス回避（バックテスト安全）やフェイルセーフ（API故障時のフォールバック）を意識しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数）
  - market calendar 管理（is_trading_day、next_trading_day、calendar_update_job）
  - news_collector（RSS 取得、前処理、安全対策）
  - quality（データ品質チェック：欠損・重複・スパイク・日付不整合）
  - audit（監査テーブルのDDL と初期化関数）
  - stats（zscore 正規化等）
- ai/
  - news_nlp.score_news（記事群を LLM でスコアリングして ai_scores に保存）
  - regime_detector.score_regime（ETF MA200 とマクロニュース LLM を合成して market_regime に保存）
- research/
  - factor_research（モメンタム・ボラティリティ・バリュー計算）
  - feature_exploration（将来リターン計算、IC、統計サマリー）
- config.py
  - Settings クラスで環境変数を集中管理。自動でプロジェクトルートの `.env` / `.env.local` を読み込み。

---

## セットアップ手順

前提
- Python 3.10+ を推奨（型注釈 Union | を使用）
- DuckDB、openai SDK 等が必要（プロジェクトの packaging に依存します）

1. リポジトリをクローン（例）
   - git clone <repo_url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （本プロジェクトに packaging があれば）pip install -e .

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を参照してください。

4. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

サンプル .env:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabu API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack (通知用途)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development   # or paper_trading / live
LOG_LEVEL=INFO
```

必須環境変数（Settings により require される）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

OpenAI の API キーは各 ai 関数に `api_key` 引数として渡すか、環境変数 `OPENAI_API_KEY` をセットします。

---

## 使い方（主要な例）

- DuckDB 接続の作成（例）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL の実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを生成（ai.news_nlp.score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None の場合 OPENAI_API_KEY を参照
print("書き込み件数:", n_written)
```

- 市場レジーム判定（ai.regime_detector.score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査DB 初期化（audit schema）
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査ログテーブルが作成される
```

- カレンダー関数例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- ai モジュールは OpenAI API を呼び出します。API 呼び出し回数やコストに注意してください。
- ETL・news_collector は DuckDB スキーマ（raw_prices / raw_news 等）が前提です。初期スキーマの作成手順は別途スキーマ初期化機能を用意してください（本コードベースでは audit 用 init_audit_schema が提供されています）。
- 自動 .env 読み込みはパッケージ import 時に行われます（プロジェクトルート判定は .git または pyproject.toml）。テスト時に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースの LLM スコアリング
    - regime_detector.py          — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント / save_* / fetch_*
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - etl.py                      — ETLResult の再公開
    - calendar_management.py      — 市場カレンダー管理
    - news_collector.py           — RSS 収集 / 前処理 / SSRF 対策
    - quality.py                  — データ品質チェック
    - stats.py                    — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                    — 監査ログ DDL / init_audit_schema / init_audit_db
  - research/
    - __init__.py
    - factor_research.py          — ファクター計算（momentum/value/volatility）
    - feature_exploration.py      — forward returns / IC / summary / rank

---

## 実運用上の注意・設計方針（抜粋）

- ルックアヘッドバイアス防止
  - 日付判定やニュースウィンドウ等は内部で datetime.today()/date.today() を不用意に参照せず、引数の target_date を基に処理します。
- フェイルセーフ
  - LLM / API エラー時は例外を直接投げずにフォールバック（ゼロスコア等）して処理を継続する箇所が多くあります（ログは出力）。
- 冪等性
  - J-Quants データ保存やニュースの保存は冪等操作（ON CONFLICT / ハッシュID）で行います。
- セキュリティ
  - news_collector は SSRF 対策、XML パースの defusedxml 使用、レスポンス最大バイト制限などを実施しています。
- レート制御
  - J-Quants クライアントは API レート制限（120 req/min）に対応する RateLimiter を実装しています。

---

## 貢献 / テスト

- テストを書く際は環境変数自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants の外部呼び出しをテストする場合は、モジュール内で提供されている `_call_openai_api` 等をモックすると容易です。
- news_collector や jquants_client の HTTP 周りはリプレイ/モックでのテストが推奨されます。

---

もし README に追加してほしい点（依存関係の正確な列挙、CI/テスト手順、スキーマ定義の詳細、実行スクリプト例など）があれば教えてください。必要に応じて追記します。
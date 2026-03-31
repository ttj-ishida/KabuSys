# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（ライブラリ）。  
データ収集（J-Quants）、ニュースセンチメント（OpenAI）、ファクター計算、ETL、監査ログなどを含むモジュール群を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数 (.env) 例
- ディレクトリ構成
- 注意事項 / 設計上のポイント

---

## プロジェクト概要

KabuSys は日本株の自動売買パイプラインを構築するための内部ライブラリです。主に以下を目的としています。

- J-Quants API を用いた市場データ（株価・財務・カレンダー）の差分取得と DuckDB への蓄積（ETL）
- RSS ニュース収集とニュース → 銘柄紐付け
- OpenAI を使ったニュースセンチメント（銘柄別 / マクロ）評価（gpt-4o-mini）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）とリサーチ用ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマ初期化と運用サポート
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、バックテスト等における Look-ahead Bias を避ける実装方針が随所に反映されています（日時の取り扱い、DB クエリ条件等）。

---

## 機能一覧

- 環境変数管理（src/kabusys/config.py）
  - プロジェクトルートの .env/.env.local を自動読み込み（無効化可能）
  - 必須環境変数チェックを提供

- データ（src/kabusys/data）
  - J-Quants クライアント（fetch / save）: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - カレンダー管理（営業日判定、next/prev/get_trading_days 等）
  - ニュース収集 (RSS) と前処理（SSRF対策・gzip上限・トラッキングパラメータ除去）
  - データ品質チェック（missing, spike, duplicates, date consistency）
  - 監査ログスキーマ初期化 / 専用 DB 初期化（init_audit_schema, init_audit_db）

- AI（src/kabusys/ai）
  - 銘柄別ニュースセンチメント: score_news (gpt-4o-mini, JSON モード)
  - マクロ＋ETF MA を合成した市場レジーム判定: score_regime

- 研究（src/kabusys/research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
  - 統計ユーティリティ: zscore_normalize

- 共通ユーティリティ
  - DuckDB を利用した SQL 実行
  - OpenAI 呼び出しのリトライ・バックオフ方針（AI モジュール）
  - J-Quants API の RateLimiter（120 req/min）とトークン自動リフレッシュ

---

## セットアップ手順

1. Python (推奨: 3.10+) 仮想環境を作成・有効化:
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 必要パッケージをインストール（最低限）:
   - pip install duckdb openai defusedxml

   実運用ではログ出力・Slack 通知等の追加依存がある可能性があります。requirements.txt がある場合はそちらを使用してください。

3. プロジェクトルートに .env を配置（下記テンプレート参照）。環境変数は OS 環境変数でも可。

4. データベース用ディレクトリ（デフォルト: data/）を作成:
   - mkdir -p data

5. DuckDB / 監査 DB の初期化はコード内 API を利用する（例を参照）。

---

## 使い方（簡単な例）

以下は最小限の Python スニペット例です。実行には上で設定した環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）が必要です。

- DuckDB 接続を作って日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を実行:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written", n_written)
  ```

- 市場レジーム判定（ETF 1321 + マクロニュース）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB を初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/monitoring_audit.duckdb")
  # conn を使って order_events 等の操作を行う
  ```

- ファクター計算 / 研究ユーティリティ:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  momentum = calc_momentum(conn, date0)
  value = calc_value(conn, date0)
  vol = calc_volatility(conn, date0)
  ```

注意: OpenAI 呼び出しは gpt-4o-mini（JSON mode）を想定しており、API キーは `OPENAI_API_KEY` 環境変数で参照されます。テスト時は内部の _call_openai_api をモックして呼び出しを置き換えられます。

---

## 環境変数 (.env) 例

プロジェクトルートに .env または .env.local を置くと自動読み込みされます（読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

例 (.env):
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# OpenAI (optional: 直接 score_news 等に api_key を渡すことも可能)
OPENAI_API_KEY=sk-...

# kabuステーション API (注文連携など)
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

必須となる環境変数は実行する機能により異なります。`kabusys.config.settings` のプロパティ参照で必須チェックが行われます。

---

## ディレクトリ構成（抜粋）

ソースは `src/kabusys` 以下に配置されています。主要なモジュール:

- src/kabusys/
  - __init__.py
  - config.py               # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py           # ニュースセンチメント（銘柄別）
    - regime_detector.py    # マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント（fetch/save）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - news_collector.py     # RSS 収集・前処理
    - quality.py            # データ品質チェック
    - calendar_management.py# 市場カレンダー管理 / 営業日判定
    - audit.py              # 監査ログ（テーブルDDL / 初期化）
    - stats.py              # 統計ユーティリティ（zscore）
    - etl.py                # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py    # ファクター計算
    - feature_exploration.py# IC / forward returns / rank / summary

---

## 注意事項 / 設計上のポイント

- Look-ahead Bias 防止:
  - 各モジュールは内部で date / datetime の「今日参照」を避け、引数で対象日を与える設計です。
  - ETL や AI スコアリングも target_date 引数を受け取ります。

- エラー処理:
  - J-Quants クライアント・OpenAI 呼び出しともにリトライやフォールバック（例: マクロセンチメント失敗時は 0.0）を備え、処理を継続する設計です。
  - ETL パイプラインは各ステップが独立してエラーハンドリングされ、可能な限り他ステップを止めない挙動を取ります。

- セキュリティ:
  - RSS 収集で SSRF 対策、defusedxml による XML パース防御、レスポンスサイズ制限を実施しています。
  - J-Quants のトークンはリフレッシュ可能、モジュールでキャッシュ・自動リフレッシュを実装しています。

- レート制限:
  - J-Quants API は 120 req/min を想定し RateLimiter を実装しています。過度な同時呼び出しに注意してください。

---

もし README に追記したい操作（例: CI 設定、具体的な SQL スキーマ、Slack 通知の使い方、kabuステーション連携のサンプル等）があれば教えてください。それに合わせてサンプルコードや手順を追加します。
# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの市場データ取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ管理、マーケットカレンダー管理、レジーム判定などを提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（.env）
- 使い方（主な API と実行例）
- ディレクトリ構成
- 備考 / 運用上の注意

---

## プロジェクト概要

KabuSys は日本株の自動売買・データ基盤向けに設計された Python モジュール群です。J-Quants API を用いた株価・財務データの差分 ETL、RSS ベースのニュース収集と OpenAI によるニュースセンチメント評価、研究用途のファクター計算、マーケットカレンダー管理、監査ログ（シグナル→発注→約定のトレーサビリティ）などを提供します。Look-ahead バイアスに配慮した実装や、API 呼び出しのリトライ／レート制御、冪等保存（DuckDB 側での ON CONFLICT）などの運用上重要な設計指針が採用されています。

---

## 機能一覧

- データ ETL
  - J-Quants からの日次株価（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得・保存
  - 差分・バックフィル対応、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS 取得（SSRF 対策、サイズチェック、URL 正規化）
  - OpenAI（gpt-4o-mini 等）を用いた銘柄別センチメントスコア生成（ai_scores）
  - マクロニュースを用いた市場レジーム判定（market_regime）
- 研究用ユーティリティ
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Zスコア正規化
- カレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日列挙
  - 夜間バッチ更新 job（J-Quants から差分取得）
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等のテーブル定義・初期化
  - 監査用 DuckDB 初期化ユーティリティ（UTC タイムスタンプ等）
- 設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検知）
  - 必須環境変数のラップ（kabusys.config.settings）

---

## 必要条件

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース、OpenAI）

プロジェクトの pyproject.toml / requirements.txt があればそちらに従ってください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があれば pip install -e . または pip install -r requirements.txt）

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を配置すると自動で読み込まれます（`.env.local` は上書き）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須変数や例は次節を参照。

5. DuckDB ファイル等の初期化
   - 監査ログ用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 実行のために DuckDB 接続を用意してください:
     ```python
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     ```

---

## 環境変数（.env）例 / 説明

主に以下の環境変数が使用されます。README 用のサンプル `.env`:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi  # オプション

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Slack 通知
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789

# データベースパス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

必須（実行パスに依存）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合
- KABU_API_PASSWORD: kabuステーション API を使う場合

kabusys.config.Settings は必須環境変数が未セットだと ValueError を投げます。

---

## 使い方（主な API と実行例）

以下は代表的な利用例です。実運用ではログ設定や例外処理、ID トークン注入等を組み合わせてください。

- 日次 ETL を実行する（DuckDB 接続が必要）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを生成する（OpenAI API キーが必要）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", n_written)
  ```

- 市場レジームを判定する（ETF 1321 + マクロニュース）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログのスキーマ初期化:
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- 研究系 API（ファクター計算など）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- カレンダー・ユーティリティ:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  is_trading = is_trading_day(conn, date(2026, 3, 20))
  nxt = next_trading_day(conn, date(2026, 3, 20))
  ```

注意:
- OpenAI の呼び出しは gpt-4o-mini 等を想定しており、レスポンスは JSON mode により JSON のみ返すよう期待しています。API 失敗時にはフェイルセーフとしてゼロにフォールバックする実装の箇所があります。
- ETL / API 呼び出しはリトライ・レート制御が組み込まれていますが、運用監視は必須です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント（OpenAI）
  - regime_detector.py     — マーケットレジーム判定
- data/
  - __init__.py
  - calendar_management.py — マーケットカレンダー管理
  - etl.py                 — ETL 型（ETLResult 再エクスポート）
  - pipeline.py            — 日次 ETL パイプライン実装（run_daily_etl 等）
  - stats.py               — 統計ユーティリティ（zscore 正規化）
  - quality.py             — 品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py               — 監査ログ（テーブル定義・初期化）
  - jquants_client.py      — J-Quants API クライアント（取得・保存）
  - news_collector.py      — RSS 取得・前処理・保存ユーティリティ
- research/
  - __init__.py
  - factor_research.py     — Momentum / Volatility / Value 等
  - feature_exploration.py — 将来リターン・IC・統計サマリー

その他:
- データベースファイル (デフォルト): data/kabusys.duckdb, data/monitoring.db
- `.env` / `.env.local`（プロジェクトルートに置くことで自動ロード）

---

## 備考 / 運用上の注意

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を起点に行われます。テスト環境などで自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- settings で取得する環境変数が不足していると ValueError を発生させます（必須項目の保護）。
- OpenAI / J-Quants API 呼び出しはレート制限・リトライロジックが組み込まれていますが、API キーの使用量やコスト管理は別途行ってください。
- DuckDB に対する executemany の取扱いや一部バージョン特有の挙動（空リストの executemany 不可等）を考慮した実装になっています。DuckDB のバージョン依存性に注意してください。
- 監査ログは削除しない（削除前提の設計でない）ため、保守運用（ディスク容量管理など）を行ってください。
- 外部ネットワークからの RSS 取得時は SSRF 対策・レスポンスサイズ上限・gzip 解凍上限などの安全策を実装していますが、運用時のソースホワイトリスト管理等を行ってください。

---

もし README に追加したい実行スクリプト例（cron / Airflow ジョブの例）や CI 設定、.env.example テンプレートなどが必要であれば、用途に合わせて具体例を作成します。
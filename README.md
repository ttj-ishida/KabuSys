# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（README 日本語版）

このリポジトリは、J-Quants 等の外部データソースからデータを収集し、DuckDB に保存・品質チェックを行い、シグナル→発注→約定の監査トレースを備えた自動売買基盤の核となるモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたライブラリです。

- J-Quants API から株価（OHLCV）・財務・マーケットカレンダーを取得して保存
- RSS ベースのニュース収集と銘柄抽出（トラッキングパラメータ削除、SSRF対策、XML 攻撃対策）
- DuckDB ベースの 3 層データレイヤ（Raw / Processed / Feature）と Execution / Audit テーブルの提供
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 設計上の考慮点：API レート制限・リトライ・トークン自動更新・冪等保存・Look-ahead bias 回避

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- data/news_collector.py
  - RSS から記事を収集・前処理・正規化して raw_news に保存
  - URL 正規化（utm_* 等除去）→ SHA-256（先頭32文字）で記事IDを生成
  - defusedxml を使った XML パース・SSRF / private-host 検出・gzip 対応・サイズ上限

- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) によるテーブル作成（冪等）

- data/pipeline.py
  - 日次 ETL（run_daily_etl）：calendar → prices → financials → 品質チェック
  - 差分更新・backfill・品質チェック（quality モジュール）を実装

- data/calendar_management.py
  - market_calendar を元に営業日判定・次営業日/前営業日検索・夜間カレンダー更新ジョブ

- data/quality.py
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue オブジェクトで詳細を返す

- data/audit.py
  - 監査ログ（signal_events / order_requests / executions）テーブル定義と初期化
  - init_audit_schema / init_audit_db を提供

- config.py
  - 環境変数読み込み（.env/.env.local の自動ロード、プロジェクトルート探索）
  - Settings オブジェクトからアプリ設定を取得（必須パラメータのバリデーション含む）

---

## セットアップ手順

前提
- Python 3.9+（type hints や一部構文を使用）
- ネットワークアクセス（J-Quants / RSS）

1. レポジトリをクローン（あるいはパッケージを取得）:

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows (PowerShell)
   ```

3. 依存パッケージをインストール

   必須ライブラリの一例（プロジェクトに requirements.txt があればそちらを使用してください）:

   ```bash
   pip install duckdb defusedxml
   ```

   必要に応じて logger 等を追加でインストールしてください。

4. 環境変数を用意

   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（config.py がプロジェクトルートを探します）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（必須・任意）:

   - JQUANTS_REFRESH_TOKEN (必須)  
   - KABU_API_PASSWORD (必須)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
   - KABUSYS_ENV (optional; development | paper_trading | live; default: development)
   - LOG_LEVEL (optional; DEBUG/INFO/WARNING/ERROR/CRITICAL; default: INFO)

   例 (.env):

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡単なコード例）

以下は基本的な初期化と日次 ETL 実行の例です。

1. DuckDB スキーマ初期化

```python
from kabusys.data import schema

# ファイル DB の初期化（親ディレクトリを自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
```

2. 日次 ETL を実行する（J-Quants の ID トークンは Settings から自動取得）

```python
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
result = pipeline.run_daily_etl(conn)  # target_date を省略すると今日を使用
print(result.to_dict())
```

3. RSS ニュース収集ジョブ例

```python
from kabusys.data import news_collector
from kabusys.data import schema
import duckdb

conn = schema.get_connection("data/kabusys.duckdb")
# 既知の銘柄コードセットを用意（抽出フィルタ用）
known_codes = {"7203", "6758", "9984"}

# sources を指定して実行（省略時はデフォルトの Yahoo Finance）
news_collected = news_collector.run_news_collection(conn, known_codes=known_codes)
print(news_collected)
```

4. 監査ログ用スキーマ初期化

```python
from kabusys.data import schema, audit

conn = schema.get_connection("data/kabusys.duckdb")
# 監査テーブルを追加で作成
audit.init_audit_schema(conn)
```

---

## 設計上の注意点 / 運用ガイド

- J-Quants のレート制限（120 req/min）に従うよう RateLimiter を実装しています。大量データ取得時は注意してください。
- API 呼び出しは最大3回のリトライ、401 を受けた場合は自動でリフレッシュトークンから idToken を取得して再試行します。
- データベースへの保存は冪等（ON CONFLICT）を採用しているため、再実行での重複挿入を回避します。
- ETL は差分更新を行い、backfill_days を使って後出し修正を吸収する仕様です。
- news_collector は SSRF / XML bomb / gzip bomb 等の対策を施していますが、外部フィードの取り扱いには常に注意してください。
- 環境変数の読み込みはプロジェクトルート（.git または pyproject.toml の存在）から自動で行います。CI やテストで自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定します。
- DuckDB はファイルベースの軽量DBです。バックアップや排他（同時接続）ポリシーを運用で考慮してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュール構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                - 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      - RSS ニュース収集・正規化・保存
    - schema.py              - DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py            - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py - カレンダー管理（営業日判定・更新ジョブ）
    - quality.py             - データ品質チェック
    - audit.py               - 監査ログ（signal/order_request/executions）定義
    - pipeline.py
  - strategy/
    - __init__.py            - 戦略関連パッケージプレースホルダ
  - execution/
    - __init__.py            - 発注/実行関連プレースホルダ
  - monitoring/
    - __init__.py            - 監視用プレースホルダ

主要なテーブル（DuckDB スキーマ例）

- Raw layer
  - raw_prices, raw_financials, raw_news, raw_executions
- Processed layer
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature layer
  - features, ai_scores
- Execution / Audit layer
  - signals, signal_queue, orders, trades, positions, portfolio_targets, portfolio_performance
  - signal_events, order_requests, executions (監査専用)

---

## 追加情報 / 開発者向け

- 自動環境読み込みロジックはプロジェクトルートを .git または pyproject.toml で検出します。パッケージ化後でも動作するように __file__ を基準に探索します。
- news_collector の fetch_rss は内部で urllib を用いており、テスト目的で _urlopen をモックすることが想定されています。
- jquants_client はページネーションに対応し、ページネーション間で ID トークンを共有するためのモジュールレベルのキャッシュを持ちます（_ID_TOKEN_CACHE）。
- 品質チェックは fail-fast ではなく全チェックを実行し、呼び出し側が問題の重大度に応じて停止/警告を判断します。

---

必要であれば、README にサンプル .env.example、CI 実行例、より詳しい運用手順（スケジューリング、バックアップ、監視 Slack 通知例）を追加できます。どのトピックを優先して拡張しましょうか？
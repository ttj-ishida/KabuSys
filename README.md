# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants API や RSS からのデータ収集、DuckDB を用いたスキーマ/ETL、品質チェック、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。主な目的は以下です。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得する
- RSS フィードからニュースを収集して記事と銘柄を紐付ける
- DuckDB に対するスキーマ定義・初期化・ETL パイプラインを提供する
- データ品質チェック（欠損・スパイク・重複・日付不整合）を行う
- 発注〜約定までの監査ログ（audit）を保持しトレーサビリティを担保する

設計上のポイント：
- API レート制限とリトライ（指数バックオフ）に対応
- Look-ahead bias 回避のため取得時刻（UTC）を記録
- RSS 取得における SSRF 対策・サイズ制限・XML 攻撃対策
- DuckDB への保存は冪等（ON CONFLICT）で実装
- 品質チェックは Fail-Fast とせず問題を収集して報告

---

## 機能一覧

- データ取得（kabusys.data.jquants_client）
  - 日次株価（OHLCV）
  - 財務（四半期 BS/PL）
  - JPX マーケットカレンダー
  - レート制限、リトライ、トークン自動リフレッシュ、ページネーション対応

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（gzip対応）
  - URL 正規化、トラッキングパラメータ除去、記事ID生成（SHA-256）
  - SSRF / private IP ブロック、XML 安全パーシング
  - raw_news / news_symbols への冪等保存

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日からの差分）
  - backfill 対応（後出し修正の吸収）
  - 市場カレンダーの先読み
  - 品質チェックの統合実行

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチ）

- スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス定義、初期化ユーティリティ（init_schema / init_audit_schema）

- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク、重複、日付不整合の検出
  - QualityIssue を返し集約・報告可能

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions などの監査テーブル
  - 発注の冪等キー、トレース用インデックス

- 設定管理（kabusys.config）
  - .env / .env.local / OS 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検証と Settings API

---

## セットアップ手順

前提:
- Python 3.9+（typing | None 型や typing の機能を想定しています）
- Git リポジトリルート（.git）または pyproject.toml がルートとして存在すること（.env 自動読み込みに利用）

1. リポジトリをクローン／配置

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須: duckdb, defusedxml
   - 例:
     pip install duckdb defusedxml

   （本リポジトリに requirements.txt / pyproject.toml がある場合はそちらを使用）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先順: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須/任意）例:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
   - KABUSYS_ENV (任意, dev/paper_trading/live のいずれか; デフォルト: development)
   - LOG_LEVEL (任意, DEBUG/INFO/WARNING/ERROR/CRITICAL; デフォルト: INFO)

   .env のサンプル:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（DuckDB）
   - Python REPL やスクリプトからスキーマを作成します。例:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ（audit）を別 DB に初期化する場合:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（概要と例）

基本的な ETL 実行例（日次 ETL）:

```
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（存在しない場合は作成）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を指定しなければ今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

ニュース収集ジョブの実行例:

```
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes を与えると記事と銘柄を紐付ける（抜粋例）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

マーケットカレンダー夜間更新ジョブ:

```
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

J-Quants API の直接呼び出し（トークン取得やデータ取得）:

```
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()  # settings.jquants_refresh_token を使用
quotes = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
```

品質チェックの実行:

```
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

設定管理について:
- `from kabusys.config import settings` で Settings オブジェクトにアクセスできます（例: settings.jquants_refresh_token）。
- .env の自動ロードはプロジェクトルートを .git や pyproject.toml から検出して行われます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。

ログ:
- 各モジュールは標準ライブラリの logging を使用しているため、アプリケーション側で適切にロガーを設定してください（レベル、ハンドラ等）。

---

## ディレクトリ構成

主要なモジュールとファイル（src/kabusys 配下）:

- kabusys/
  - __init__.py
    - パッケージ公開。__version__ = "0.1.0"
  - config.py
    - 環境変数読み込み・Settings API、.env 自動ロードロジック
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存機能、レート制限・リトライ）
    - news_collector.py
      - RSS 収集、記事正規化、raw_news/news_symbols への保存
    - schema.py
      - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - calendar_management.py
      - カレンダー判定・夜間更新ジョブ（is_trading_day 等）
    - audit.py
      - 監査ログスキーマ（signal_events / order_requests / executions）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
    - （戦略実装用のプレースホルダ）
  - execution/
    - __init__.py
    - （発注・ブローカ連携用のプレースホルダ）
  - monitoring/
    - __init__.py
    - （監視・監督機能用プレースホルダ）

補足:
- schema.py は大量の DDL を定義しており、init_schema() でまとめてテーブル／インデックスを作成します。
- audit.py は監査用追加テーブルを提供し、init_audit_schema()/init_audit_db() を通じて初期化できます。

---

## 注意点 / 実運用に向けたメモ

- 環境変数の管理: 秘密情報（refresh token 等）は適切に保護してください（.env を git 管理しない等）。
- API レート制限: jquants_client は 120 req/min を想定した簡易レート制御をしていますが、運用時は追加のトラフィック管理が必要になるかもしれません。
- DB バックアップ: DuckDB ファイルの扱い（バックアップ・スナップショット）を運用ルールに定めてください。
- テスト: ネットワーク依存部分（RSS、API）はモック化してユニットテストを実装してください。news_collector._urlopen 等は差し替え可能に設計されています。
- ログの UTC ポリシー: 監査ログは UTC タイムスタンプで保存する仕様です（audit.init_audit_schema は TimeZone='UTC' を設定します）。

---

必要であれば、README に以下の追記を行えます:
- 依存関係（pyproject.toml / requirements.txt）の例
- CI / テスト実行手順
- Docker / コンテナ化の例
- よくあるトラブルシュート（認証エラー、DuckDB パス権限等）

ご希望があれば上記のいずれかを追加で作成します。
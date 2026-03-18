# KabuSys

日本株向けの自動売買/データ基盤ライブラリ。J-Quants API や RSS を用いたデータ収集、DuckDB によるデータ永続化、ETL（差分取得・バックフィル・品質チェック）、マーケットカレンダー管理、ニュース収集、監査ログ（発注〜約定トレース）などを提供します。

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを安全かつ冪等に取得して DuckDB に保存
- RSS からニュース記事を収集し、記事と銘柄コードの紐付けを行う
- ETL パイプライン（差分更新・バックフィル・品質チェック）を提供
- マーケットカレンダーの判定・更新ユーティリティを提供（営業日/半日/SQ判定など）
- 監査ログ（signal → order_request → execution）スキーマを提供し、トレース可能にする

設計上の注目点:
- API レート制御（120 req/min）とリトライ（指数バックオフ、401 時の自動トークンリフレッシュ）を実装
- DuckDB に対する挿入は冪等（ON CONFLICT）で安全
- ニュース収集は SSRF / XML-Bomb / 大容量レスポンス対策を含む堅牢な実装

---

## 主な機能一覧

- データ取得
  - 株価日足（OHLCV）, 財務（四半期 BS/PL）, JPX マーケットカレンダー（jquants_client）
- 保存 / スキーマ管理
  - DuckDB スキーマ定義・初期化（data.schema.init_schema）
  - 監査ログスキーマ（data.audit.init_audit_schema / init_audit_db）
- ETL
  - 差分更新（backfill を考慮）と総合 ETL（data.pipeline.run_daily_etl）
  - 品質チェック（欠損、スパイク、重複、日付不整合を検出）
- ニュース収集
  - RSS の取得／正規化／前処理／ID生成／DuckDB への冪等保存（data.news_collector）
  - 記事から銘柄コードを抽出して news_symbols に紐付け
- カレンダー管理
  - 営業日判定、next/prev_trading_day、期間内営業日取得、夜間更新ジョブ（data.calendar_management）
- 設定管理
  - .env および OS 環境変数の自動読み込み（config.Settings）
  - 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要要件 / 依存パッケージ

最低限の主な依存（例）:
- Python 3.10+
- duckdb
- defusedxml

プロジェクトの実際の requirements はこのリポジトリに含めるか、パッケージ化時に指定してください。

---

## セットアップ手順（開発環境向け）

1. レポジトリをクローン（省略）

2. 仮想環境の作成と有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```

   実際は requirements.txt / pyproject.toml を用意して `pip install -r requirements.txt` / `pip install .` することを推奨します。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（config モジュールが .git または pyproject.toml を探索してルートを特定します）。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時等）。

---

## 環境変数 (.env 例)

このライブラリで参照する主な環境変数:

- J-Quants（必須）
  - JQUANTS_REFRESH_TOKEN=your_refresh_token

- kabuステーション API（必須）
  - KABU_API_PASSWORD=your_kabu_password
  - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意、デフォルトあり

- Slack（必須）
  - SLACK_BOT_TOKEN=your_slack_bot_token
  - SLACK_CHANNEL_ID=your_channel_id

- DB パス（任意）
  - DUCKDB_PATH=data/kabusys.duckdb    # data.schema のデフォルト
  - SQLITE_PATH=data/monitoring.db     # 監視用（モジュールで使用される可能性）

- 実行環境 / ログ
  - KABUSYS_ENV=development|paper_trading|live
  - LOG_LEVEL=INFO|DEBUG|...（デフォルト INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（主要 API と実行例）

以下は代表的な使い方サンプルです。実際はアプリケーション側で適宜ラッパーや CLI を用意してください。

※ すべての例は既に必要な依存をインストールし、環境変数を設定している前提です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

2) 監査ログスキーマ初期化（既存接続へ追加）
```python
from kabusys.data import audit
audit.init_audit_schema(conn, transactional=True)
# もしくは専用 DB を作る
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.data import pipeline
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

run_daily_etl は以下を行います：
- 市場カレンダー ETL（先読み）
- 株価 ETL（差分取得 + backfill）
- 財務データ ETL（差分取得 + backfill）
- 品質チェック（check_missing_data, check_duplicates, check_spike, check_date_consistency）

戻り値は ETLResult オブジェクト（取得件数 / 保存件数 / 品質問題 / エラー等を含む）。

4) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
# known_codes に有効銘柄コードセットを渡すと記事に出現する銘柄を紐付ける
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

5) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved {saved} records")
```

6) J-Quants 生データ取得（単体利用）
```python
from kabusys.data import jquants_client as jq
# token は settings から自動取得されるため通常は省略可（モジュール内キャッシュと自動リフレッシュあり）
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,3,31))
# DuckDB に保存
saved = jq.save_daily_quotes(conn, records)
```

---

## 実装上の注意・運用メモ

- レート制御: jquants_client は 120 req/min を守る設計です（固定間隔スロットリング）。
- リトライ: ネットワークエラーや 429/408/5xx に対する指数バックオフリトライを実装。401 はトークン自動リフレッシュして 1 回リトライします。
- 冪等性: raw テーブルへの保存は ON CONFLICT を用いて冪等に行われます（重複や再実行に強い）。
- ニュース収集: URL 正規化やトラッキングパラメータ除去、SSRF 対策、gzip 解凍上限チェックを実装しています。
- 環境変数自動読み込み: パッケージインポート時にプロジェクトルート（.git または pyproject.toml）を基に `.env` / `.env.local` を読み込みます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要ファイル・モジュールは以下の通り（この README は提供されたコードベースに基づく）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得・保存・認証・レート制御）
    - news_collector.py        # RSS ニュース収集・保存・銘柄抽出
    - schema.py                # DuckDB スキーマ定義・初期化
    - pipeline.py              # ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py   # マーケットカレンダー管理（営業日判定・更新）
    - audit.py                 # 監査ログスキーマ（signal/order_request/execution）
    - quality.py               # データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/                  # 戦略関連（雛形 / 今後の拡張）
    - __init__.py
  - execution/                 # 発注実行関連（雛形 / 今後の拡張）
    - __init__.py
  - monitoring/                # 監視 / メトリクス（雛形 / 今後の拡張）
    - __init__.py

---

## 今後の拡張案（参考）

- strategy / execution 層の実装（シグナル生成 → 発注実行のフロー）
- Slack への通知機能の統合（settings で Slack 情報は定義済み）
- CLI / コンテナ化（Docker）による定期バッチ実行（ETL・カレンダー更新）
- 単体テストと CI 設定（自動環境ロードを無効化する仕組みあり）

---

必要であれば README の英訳、コマンド例の追加（systemd タイマー / cron / Docker Compose）、あるいは具体的な運用手順（運用フロー）も作成します。どの情報を追加したいか教えてください。
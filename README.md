# KabuSys

KabuSys は日本株のデータ取得・ETL・品質チェック・ニュース収集・監査ログを備えた自動売買プラットフォームのコアライブラリです。J-Quants API からの市場データ取得、RSS ベースのニュース収集、DuckDB を用いた三層データレイヤ（Raw / Processed / Feature）、品質チェック、発注周りの監査ログ管理などを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 受信時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードの取得・パース（defusedxml を使用）
  - URL 正規化とトラッキングパラメータ除去、SHA-256 ベースの記事ID生成で冪等性
  - SSRF 対策（スキーム検証、リダイレクト先検証、プライベートアドレス拒否）
  - 受信サイズ制限、gzip 解凍後も検査
  - DuckDB へのバルク保存（INSERT ... RETURNING）と銘柄コード紐付け

- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution / Audit のテーブル群を含むスキーマ
  - インデックス、外部キー、各種制約を備えた DDL を提供
  - 監査ログ（signal_events / order_requests / executions）用の初期化も提供

- ETL パイプライン
  - 差分更新（最終取得日からの差分 + バックフィル）
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 各ステップは独立したエラーハンドリングで継続実行

- データ品質チェック
  - 欠損データ検出、スパイク検出（前日比閾値）、重複チェック、日付整合性チェック
  - QualityIssue オブジェクト列で詳細を返す

- 監査 / トレーサビリティ
  - ビジネス日 → 戦略 → シグナル → 発注要求 → 約定 の UUID 連鎖で追跡可能
  - 発注要求は冪等キー（order_request_id）をサポート

---

## 前提・動作環境

- Python 3.10 以上（型ヒントの union 型 `X | None` を使用しています）
- 必要なパッケージ（一部）:
  - duckdb
  - defusedxml

必要に応じて他のパッケージ（logging 等）は標準ライブラリを使用します。

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを入手）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （開発用）pip install -e .

4. 環境変数設定
   - プロジェクトルートの `.env`（または `.env.local`）に必要な環境変数を設定します。
   - 自動で .env を読み込む仕組みがあります（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   最低限必要な環境変数（Settings から参照）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - DUCKDB_PATH (省略可: デフォルト data/kabusys.duckdb)
   - SQLITE_PATH (省略可: デフォルト data/monitoring.db)
   - KABUSYS_ENV (development / paper_trading / live、デフォルト development)
   - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト INFO)

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - サンプルスクリプトで初期化します（下記「使い方」参照）。

---

## 使い方（簡単なコード例）

以下は主要な操作の例です。Python スクリプトまたは REPL から実行します。

- DuckDB スキーマを初期化して接続を取得する
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

- 監査ログテーブルを既存の接続に追加する
```
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
```
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# conn は init_schema で得た接続
result = run_daily_etl(conn)
print(result.to_dict())
```

- 株価データのみ差分 ETL を手動実行する
```
from kabusys.data.pipeline import run_prices_etl
from datetime import date

fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- RSS ニュースの収集と保存
```
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードの集合（例）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- J-Quants クライアントを直接使ってデータ取得（テスト用）
```
from kabusys.data import jquants_client as jq

# トークン省略時は settings.jquants_refresh_token を使用して自動取得
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(quotes))
```

---

## ディレクトリ構成

リポジトリの主要ファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py                 -- パッケージ定義（__version__ = "0.1.0"）
  - config.py                   -- 環境変数 / 設定管理（.env 自動ロード、Settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py         -- J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py         -- RSS ニュース取得・前処理・DB保存・銘柄抽出
    - schema.py                 -- DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py               -- ETL パイプライン（差分更新 / 品質チェック）
    - audit.py                  -- 監査ログ（signal / order_request / executions）初期化
    - quality.py                -- データ品質チェック（欠損・スパイク・重複・日付整合性）
  - strategy/
    - __init__.py               -- 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py               -- 発注・ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py               -- 監視 / メトリクス（拡張ポイント）

---

## 実運用メモ・設計上の注意点

- 環境設定
  - 自動環境読み込みは config.py 内で `.env` / `.env.local` をプロジェクトルートから読み込みます。
  - テスト等で自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 認証
  - J-Quants の ID トークンはリフレッシュトークンから取得します。401 を受けた場合は自動でリフレッシュして再試行します（1 回のみ）。

- データ品質
  - ETL 実行後に品質チェックを行い、issue を返します。設計方針上、品質エラーが見つかっても ETL は継続し、呼び出し元が停止するか判断します。

- ニュース収集のセキュリティ
  - RSS 取得では SSRF の防御（スキーム検証、プライベートアドレス拒否、リダイレクト検査）や XML の安全パーシング、サイズ制限を実装しています。

- 冪等性
  - 生データ保存（raw_*）は ON CONFLICT / DO UPDATE 又は DO NOTHING を用いて冪等性を担保しています。

---

## 今後の拡張ポイント（参考）

- strategy / execution / monitoring パッケージは拡張ポイントとして用意されています。独自戦略やブローカー連携（kabu API ラッパー）を実装する際はここにモジュールを追加してください。
- Slack 通知やジョブスケジューラ（Airflow / cron）との統合を想定しています。
- AI スコアリング等は features / ai_scores テーブルを通じて統合可能です。

---

ご不明点や追加で README に載せたい内容（CI、詳しい .env.example、実行スクリプト例など）があれば教えてください。README を補足・拡張して作成します。
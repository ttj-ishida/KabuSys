# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（ライブラリ的なコードベース）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、DuckDB スキーマ／監査ログなどを備え、戦略・実行・監視層と連携するための基礎機能を提供します。

---

## 特徴（機能一覧）

- 環境変数／.env 自動読み込み（プロジェクトルート検出）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、市場カレンダー取得
  - レート制限（120 req/min）対応、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT）
- RSS ニュース収集
  - URL 正規化・トラッキングパラメータ除去、記事ID は SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートIP拒否）、gzip サイズ上限
  - DuckDB へ冪等保存（INSERT ... RETURNING）
  - 記事 → 銘柄コード紐付け（テキスト中の4桁コード抽出）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義・初期化ユーティリティ
  - 監査ログ用スキーマ（signal / order_request / execution）を別途初期化可能
- ETL パイプライン
  - 差分更新（最終取得日ベース）＋バックフィル、カレンダー先読み
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL 結果を ETLResult オブジェクトで返却
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日列挙
  - 夜間アップデートジョブ（カレンダー差分取得）
- データ品質チェックモジュール
  - 欠損データ、スパイク検出、重複、将来日付／非営業日データ検査
  - 複数チェックをまとめて実行し QualityIssue を返却

※ strategy / execution / monitoring パッケージはエントリポイントを想定した構造で、実装はそれぞれ拡張可能です。

---

## 前提（Prerequisites）

- Python 3.10+
  - 型ヒントで X | None 記法、typing 拡張を使用
- 主要依存ライブラリ（少なくとも以下をインストールしてください）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）
- J-Quants 等の外部 API トークン（環境変数で設定）

インストール例:
```bash
python -m pip install duckdb defusedxml
# あるいはプロジェクトの requirements.txt があれば:
# pip install -r requirements.txt
```

---

## 環境変数（必須 / 任意）

このパッケージは .env ファイル（プロジェクトルート）または OS 環境変数から設定を読み込みます。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH (任意, default: data/kabusys.duckdb) — DuckDB ファイルパス（":memory:" も可）
- SQLITE_PATH (任意, default: data/monitoring.db)
- KABUSYS_ENV (任意, default: development) — 有効値: development / paper_trading / live
- LOG_LEVEL (任意, default: INFO) — DEBUG/INFO/WARNING/ERROR/CRITICAL

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 必要ライブラリをインストール
   - pip install -r requirements.txt（存在する場合）
   - または個別に: pip install duckdb defusedxml
3. .env を作成（.env.example を参考に）
4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから実行:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # パスは環境に合わせて変更
     ```
   - 監査ログ用 DB を別に作る場合:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```
5. （任意）環境変数自動読み込みをテストや CI で無効化する場合:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 使い方（基本例）

以下は代表的な利用パターンのサンプルです。

- DuckDB 初期化および日次 ETL 実行:
```python
from datetime import date
from kabusys.data import schema, pipeline

# DB を初期化して接続を得る
conn = schema.init_schema("data/kabusys.duckdb")

# 今日のデータを取得・保存・品質チェック
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- J-Quants から直接データを取得して保存:
```python
from kabusys.data import jquants_client as jq
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
token = jq.get_id_token()  # settings からリフレッシュトークンを利用
records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,12,31))
saved = jq.save_daily_quotes(conn, records)
print("saved", saved)
```

- RSS ニュース収集ジョブ:
```python
from kabusys.data import news_collector, schema
import duckdb

conn = schema.init_schema("data/kabusys.duckdb")
results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

- 品質チェックだけを実行:
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today(), reference_date=date.today())
for i in issues:
    print(i)
```

注意:
- jquants_client は API のリクエスト制御（レートリミット、リトライ、401 リフレッシュ等）を組み込んでいます。大量取得時は設定を確認してください。
- DuckDB の接続はスレッドセーフに注意して取り扱ってください（用途により接続プール等を検討してください）。

---

## ディレクトリ構成

（プロジェクトルート: src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス（各種設定プロパティ）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save、認証、レート制御、リトライ）
    - news_collector.py
      - RSS 収集・前処理・DB 保存・銘柄抽出ロジック
    - schema.py
      - DuckDB スキーマ定義（Raw/Processed/Feature/Execution 層）と init_schema()
    - pipeline.py
      - 日次 ETL パイプライン（差分取得、保存、品質チェック）
    - calendar_management.py
      - 市場カレンダー管理、営業日判定、夜間更新ジョブ
    - audit.py
      - 監査ログ（signal / order_request / executions）スキーマ初期化
    - quality.py
      - データ品質チェック群（欠損、スパイク、重複、日付整合性）
  - strategy/
    - __init__.py (戦略層用のプレースホルダ)
  - execution/
    - __init__.py (発注/ブローカー連携用プレースホルダ)
  - monitoring/
    - __init__.py (監視／メトリクス用プレースホルダ)

---

## 開発メモ / 注意点

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml の存在）を基準に行われます。CI やテストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB への保存は可能な限り冪等（ON CONFLICT）で実装されていますが、外部からの直接操作やスキーマ変更には注意してください。
- news_collector はネットワークや XML パースエラーを慎重に扱っており、安全対策（SSRF、gzip/サイズ制限、defusedxml）を組み込んでいます。
- J-Quants クライアントは API の仕様変更やレート制限の変更に応じて調整が必要になる場合があります。

---

必要なら README の英語版、API ドキュメント（関数一覧・引数詳細）やサンプルスクリプト群を追加作成します。どの部分を優先してほしいか教えてください。
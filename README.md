# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）。  
J-Quants / kabuステーション 等からデータを取得し、DuckDB に保存・整形し、戦略→発注のための各種ユーティリティを提供します。

主な設計方針：
- データ取得は冪等（ON CONFLICT）で保存
- J-Quants API のレート制限・リトライ・トークン更新に対応
- ニュース収集は SSRF・XML Bomb 等に配慮した安全な実装
- DuckDB を中心としたデータレイヤ（Raw / Processed / Feature / Execution / Audit）
- 品質チェック（欠損・重複・スパイク・日付不整合）を実行可能

バージョン: 0.1.0

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）
  - 必須設定の取得とバリデーション

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、四半期財務、JPX マーケットカレンダー取得
  - ページネーション対応、レート制限（120 req/min）、指数バックオフリトライ
  - 401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得・前処理・正規化・重複排除
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成
  - SSRF、XML 攻撃、gzip bomb、大容量応答対策などの安全対策
  - raw_news / news_symbols への保存（トランザクション・チャンク挿入）

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックスや実行順を考慮した idempotent な init_schema

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日からバックフィル） → 保存 → 品質チェック
  - 日次 ETL の統合エントリ（run_daily_etl）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、期間内営業日列挙、夜間更新ジョブ

- 監査ログ（kabusys.data.audit）
  - signal / order_request / executions のトレーサビリティテーブル
  - UTC タイムゾーン固定、冪等キー（order_request_id）など

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、重複、スパイク（前日比閾値）、日付不整合の検出
  - QualityIssue オブジェクトで問題を集約

---

## 前提 / 必要環境

- Python 3.10+
  - 型注釈に `X | Y`（PEP 604）を使用しているため 3.10 以上を推奨
- 必要パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリ以外が増えた場合は requirements.txt を参照）

例（仮想環境でのインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージを編集可能インストールする場合:
# pip install -e .
```

---

## 環境変数 / 設定

自動でプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須は README 内で明記）:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack（通知など）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- システム設定
  - KABUSYS_ENV (任意, 値: development | paper_trading | live, デフォルト: development)
  - LOG_LEVEL (任意, DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

例 (.env.example)
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxx
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # 開発用: pip install -e . など
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定してください。
   - `.env.local` は開発マシン固有の上書きに使用できます。

4. DuckDB スキーマ初期化
   - スクリプトまたは REPL で schema.init_schema を呼ぶと DB と全テーブルが作成されます。

   例:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

5. 監査ログ（任意）
   - 監査専用 DB を初期化:
   ```python
   from kabusys.data import audit
   conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（例）

以下は主要なユースケースの簡単な使用例です。

- 日次 ETL を実行して J-Quants からデータ取得・保存・品質チェックを行う
```python
from datetime import date
import logging
from kabusys.data import schema, pipeline

logging.basicConfig(level=logging.INFO)

# DB 初期化（存在しなければ作成）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると today）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- RSS ニュース収集
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
# 既知銘柄コードセット（例）
known_codes = {"7203", "6758", "9984"}  # 実際は証券コード一覧をロード

# 実行
res = news_collector.run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

- J-Quants の株価を直接取得して保存
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

- 品質チェックを個別に実行
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date(2024,3,1))
for i in issues:
    print(i)
```

---

## 開発者向け補足

- 自動 .env ロードはプロジェクトルート検出（.git または pyproject.toml）を基に行われます。テストなどで無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- jquants_client の主な実装ポイント:
  - レート制限: 120 req/min（モジュール内で固定間隔スロットリング）
  - リトライ: 最大 3 回（指数バックオフ）、408/429/5xx に対応
  - 401 エラー時はリフレッシュトークンを使って ID トークンを再取得し 1 回リトライ
  - 保存関数は DuckDB に対して ON CONFLICT を使って冪等性を保証
- news_collector はセキュリティに配慮（SSRF 対策、XML パースの defusedxml、レスポンス上限、gzip 解凍後のサイズチェック等）。
- DuckDB スキーマは data/schema.py に全 DDL がまとまっています。新しいテーブルを追加する場合はスキーマ配列に追記してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
      (発注/ブローカー連携ロジックを配置)
    - strategy/
      - __init__.py
      (戦略ロジックを配置)
    - monitoring/
      - __init__.py
      (監視・メトリクス用コード)
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py

DuckDB スキーマや ETL の実装はすべて `kabusys.data` 以下にまとまっています。戦略（strategy）や実行（execution）はこの基盤を利用して構築してください。

---

## 今後の拡張案（参考）

- broker 接続モジュール（kabu-station 実装の拡張）
- 実際の注文送信・再試行ポリシーの実装（execution パッケージ）
- Slack などへの通知パイプライン（monitoring）
- CI 用のテストデータとモック API（jquants のレスポンスを再現するテストフィクスチャ）

---

必要であれば README にサンプル .env テンプレートや簡易 CLI の使い方、各モジュールの API リファレンス（関数一覧）を追加できます。どの情報を優先的に充実させるか教えてください。
# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログなどを提供し、DuckDB をバックエンドにして安定したパイプラインを構築できるよう設計されています。

主な設計方針の要点：
- API レート制限・リトライ制御（J-Quants クライアント）
- データ取得の冪等性（DuckDB への ON CONFLICT 挙動）
- Look-ahead bias 防止のため fetched_at 等で取得時刻をトレース
- ニュース収集での SSRF / XML 攻撃対策（リダイレクト検査、defusedxml、サイズ制限）
- ETL 中の品質チェック（欠損・スパイク・重複・日付整合性判定）
- 監査ログ（シグナル→発注→約定までのトレース）

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）の取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）の取得
  - JPX マーケットカレンダーの取得
  - レート制限・自動トークンリフレッシュ・リトライロジック

- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル
  - インデックス定義、監査ログ用スキーマの初期化

- ETL パイプライン
  - 差分更新（バックフィル対応）
  - 市場カレンダーの先読み
  - 品質チェック統合（quality モジュール）

- ニュース収集
  - RSS フィード取得、前処理、記事の一意化（URL 正規化 + SHA256 ベースID）
  - SSRF 防御、gzip/サイズチェック、defusedxml を用いたパース
  - raw_news / news_symbols への冪等保存

- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日リスト生成
  - calendar_update_job（夜間バッチでの差分更新）

- データ品質チェック
  - 欠損、スパイク（前日比）、重複、日付不整合検出
  - 問題は QualityIssue として集約

- 監査ログ（audit）
  - シグナル / 発注要求 / 約定 の監査テーブル群
  - UUID ベースのトレースと冪等キー（order_request_id）管理

---

## 必要要件（主な依存）

- Python 3.10 以上（タイプヒントに union types 等を使用）
- 主要ライブラリ（少なくとも以下をインストールしてください）
  - duckdb
  - defusedxml

（プロジェクトの pyproject.toml / requirements.txt があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成 & 有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. パッケージ／依存ライブラリをインストール
   - 最低限:
     ```
     pip install --upgrade pip
     pip install duckdb defusedxml
     ```
   - 開発用にパッケージとしてインストール（プロジェクトが pyproject を持つ場合）:
     ```
     pip install -e .
     ```
   - もし requirements.txt や pyproject.toml があればそちらを利用してください。

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` と（必要なら）`.env.local` を置くと自動で読み込まれます。
   - 自動ロードはデフォルトで有効。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 必要な環境変数

必須（未設定時は Settings が ValueError を投げます）:
- JQUANTS_REFRESH_TOKEN: J-Quants の Refresh Token（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV: execution 環境。許容値: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

.env ファイルの読み込み優先順位:
- OS 環境変数 > .env.local > .env

.env のパースはシェル形式に近く、export 処理やクォート・コメント等に対応します。

---

## 使い方（代表的な操作例）

Python REPL またはスクリプトから利用する例を示します。

- DuckDB スキーマを初期化（ファイル版）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- ETL（日次 ETL）を実行
```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema で作成済みを想定
result = pipeline.run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可
print(result.to_dict())
```

- ニュース収集ジョブを実行
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
```

- マーケットカレンダーの夜間更新（バッチ）
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

- 監査ログスキーマ初期化
```python
from kabusys.data import audit, schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)  # または audit.init_audit_db("data/audit.duckdb")
```

- J-Quants から直接データ取得（テストやユーティリティ用途）
```python
from kabusys.data import jquants_client as jq

# get_id_token() は settings から refresh token を参照してトークンを取得します
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 実装上の注意・設計メモ

- J-Quants クライアントは 120 req/min のレート制限に対応（固定間隔スロットリング）しています。
- HTTP の 401（認証切れ）受信時には自動的にリフレッシュトークンで id_token を再取得して 1 回だけリトライします。
- API 通信は指数バックオフのリトライを行います（最大試行回数 3 回、408/429/5xx を再試行対象）。
- DuckDB への保存は基本的に ON CONFLICT を利用して冪等性を確保しています。
- ニュース収集では URL の正規化（utm 等の除去）、記事ID の SHA-256 ハッシュ化、SSRF 対策、XML パースに defusedxml を使用しています。
- データ品質チェックは Fail-Fast ではなく、問題を全て収集して呼び出し元が対処を決定できるようになっています。

---

## ディレクトリ構成

（プロジェクトの src 配下に配置されている主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      - 環境変数/設定読み込みロジック
    - data/
      - __init__.py
      - jquants_client.py            - J-Quants API クライアント（取得・保存）
      - news_collector.py            - RSS ベースのニュース収集・保存
      - pipeline.py                  - ETL パイプライン（run_daily_etl 等）
      - schema.py                    - DuckDB スキーマ定義・初期化
      - calendar_management.py       - マーケットカレンダー管理（営業日判定等）
      - audit.py                     - 監査ログ（signal/events/order/executions）
      - quality.py                   - データ品質チェック
    - strategy/                       - 戦略実装用（パッケージ）
      - __init__.py
    - execution/                      - 発注・ブローカー連携用（パッケージ）
      - __init__.py
    - monitoring/                     - 監視用モジュール（パッケージ）
      - __init__.py

---

## よくある運用ワークフロー例

- 日次バッチ
  1. calendar_update_job を実行して市場カレンダーを取得（先読み）
  2. run_daily_etl を実行して株価・財務を差分更新
  3. ETL 後に quality.run_all_checks で品質問題を検出し、Slack 等で通知
  4. 特徴量を生成して戦略でシグナルを出す（strategy 層）
  5. signals を発行し、監査ログに保存してから発注実行（execution 層）

- ニュース収集
  - 定期的に run_news_collection を実行し raw_news / news_symbols を更新

---

## トラブルシューティング

- 環境変数未設定で ValueError が出る場合は、`.env` ファイルの有無とキー名（大文字）を確認してください。
- DuckDB に接続できない / ファイル書き込みに失敗する場合は、指定されたパスの親ディレクトリに書き込み権限があるか確認してください。
- J-Quants API エラー（レート超過や認証エラー）はログに詳細が出力されます。ログレベルを DEBUG に設定するとより詳細に追えます（LOG_LEVEL 環境変数）。

---

README はここまでです。必要であれば次のドキュメントを追加作成できます：
- .env.example のテンプレート
- 日次運用手順（cron / systemd / airflow での設定例）
- 戦略・発注フローのサンプルコード
- テストガイド（ユニットテスト、モックの置き方）
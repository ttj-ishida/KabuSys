# KabuSys

日本株向け自動売買データ基盤 / ランタイムライブラリ

KabuSys は J-Quants 等の外部データソースから株価・財務・市場カレンダー・ニュースを取得し、DuckDB に蓄積して戦略／実行層に供給するためのモジュール群です。ETL、データ品質チェック、ニュース収集、監査ログスキーマなど、実運用を想定した設計を備えています。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応、指数バックオフリトライ、401 発生時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録（Look‑ahead bias 対策）
  - DuckDB への冪等保存（ON CONFLICT を使った upsert）

- ETL パイプライン
  - 差分更新（最終取得日から未取得分のみ取得）
  - バックフィルによる API の後出し修正吸収
  - 日次 ETL エントリポイント（市場カレンダー → 株価 → 財務 → 品質チェック）

- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日一覧取得
  - 夜間バッチで JPX カレンダーを差分更新

- ニュース収集（RSS）
  - RSS フィード収集、前処理、記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策、受信サイズ上限、XML セキュリティ（defusedxml）
  - raw_news / news_symbols への冪等保存

- データ品質チェック
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
  - テストしやすい設計で、問題は一覧として返す（Fail‑Fast ではない）

- 監査ログ（Audit）
  - シグナル → 発注 → 約定までのトレーサビリティ用スキーマ
  - 発注の冪等性（order_request_id）や UTC タイムゾーン固定など運用向け設計

---

## 必要条件

- Python 3.10+
  - 型表記（|）や一部標準ライブラリの利用により Python 3.10 以降を想定しています
- 主要依存パッケージ（代表例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants / RSS ソース）

インストールはプロジェクトの requirements.txt を用意して行ってください（本リポジトリには付属していないため、上記を pip でインストールしてください）:

例:
```bash
python -m pip install "duckdb" "defusedxml"
```

---

## 環境変数 / 設定

KabuSys は .env ファイル（プロジェクトルート）または OS 環境変数から設定値を読み込みます。自動読み込みはデフォルトで有効です（`.git` または `pyproject.toml` を辿ってプロジェクトルートを特定します）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（必須は README 例）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、 allowed: development, paper_trading, live; デフォルト: development)
- LOG_LEVEL (任意、 allowed: DEBUG, INFO, WARNING, ERROR, CRITICAL; デフォルト: INFO)

注意: トークンやパスワード等の機密情報はリポジトリにコミットしないでください。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   ```

4. .env を作成して必要な環境変数を設定
   - 上の「環境変数 / 設定」を参照
   - テスト用に最低限 JQUANTS_REFRESH_TOKEN 等を設定してください

5. DuckDB スキーマ初期化（Python REPL やスクリプトから）
   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   ```

---

## 使い方（主な API と簡単な例）

以下は代表的な利用例（Python スクリプト／REPL で実行）。

- 日次 ETL の実行（市場カレンダー／株価／財務／品質チェック）:
```python
from kabusys.data import pipeline, schema
from kabusys.config import settings

# DB 初期化（1回だけ）
conn = schema.init_schema(settings.duckdb_path)

# 日次 ETL 実行（target_date を指定しなければ今日は対象）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- 単独で株価 ETL を実行:
```python
from kabusys.data import pipeline, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

- ニュース収集ジョブの実行:
```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
known_codes = {"7203", "6758", "9432"}  # 事前に保持している有効銘柄コードセット
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- 監査スキーマを追加で初期化:
```python
from kabusys.data import audit, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
audit.init_audit_schema(conn, transactional=True)
```

- J-Quants から直接トークン取得 / データ取得（低レベル API）:
```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings から refresh token を使用
prices = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

ログレベルは環境変数 `LOG_LEVEL` で制御します。

---

## 推奨運用フロー

- 開発環境: `KABUSYS_ENV=development`
- バックフィル・差分更新設定は pipeline の引数で制御（backfill_days 等）
- 定期実行: 日次 ETL は CI/CD や cron／Airflow から pipeline.run_daily_etl を呼ぶ
- カレンダー更新は夜間に calendar_management.calendar_update_job を定期実行
- ニュース収集は複数ソースを並列に取得するスケジュールで実行

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主なモジュール一覧:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定読み込みロジック、自動 .env 読み込み
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・リトライ・保存ロジック）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - news_collector.py
      - RSS 取得・前処理・保存・銘柄抽出
    - calendar_management.py
      - 市場カレンダー操作（is_trading_day, next_trading_day 等）と更新ジョブ
    - audit.py
      - 監査ログスキーマの定義と初期化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
    - （戦略実装用プレースホルダ）
  - execution/
    - __init__.py
    - （発注・ブローカー連携等の実装用プレースホルダ）
  - monitoring/
    - __init__.py
    - （監視関連のプレースホルダ）

---

## 注意点 / 運用上のヒント

- セキュリティ:
  - .env に機密情報を保存する場合はリポジトリに含めない（.gitignore を利用）
  - news_collector は外部 URL を取得するため SSRF 対策や受信サイズ制限を備えていますが、運用時も取得先を厳密に管理してください

- DB:
  - DuckDB はローカルファイルベースで軽量ですが、並列書き込みや高負荷時の挙動に注意してください
  - 監査ログや実運用のトランザクション要件に応じて DB 運用設計を行ってください

- テスト:
  - config の自動 .env 読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト時に便利）

---

この README はコードベース（src/kabusys/*）の現状に基づいて作成しています。より具体的な運用手順（デプロイ、CI/CD、監視アラート設定など）は利用環境に応じて追加してください。質問や追加したいセクションがあれば教えてください。
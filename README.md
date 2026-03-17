# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買・データプラットフォームのコアライブラリです。J-Quants API からマーケットデータ・財務データ・カレンダーを取得し、DuckDB に冪等的に格納する ETL パイプライン、RSS ベースのニュース収集、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などの基盤機能を提供します。

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レートリミット対応（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し look-ahead bias に配慮
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分取得（最終取得日ベース）、バックフィル、品質チェックの一括実行
  - run_daily_etl による日次フローの提供
- ニュース収集（RSS）
  - RSS フィード取得・前処理・正規化・記事ID生成（URL正規化 → SHA-256）
  - SSRF 対策、レスポンスサイズ制限、defusedxml による XML 攻撃対策
  - DuckDB への冪等保存（INSERT ... RETURNING）と銘柄コード抽出（4桁）
- マーケットカレンダー管理
  - 営業日判定、前後の営業日取得、夜間カレンダー更新ジョブ
  - DB 登録値優先、未登録日は曜日フォールバック
- データ品質チェック
  - 欠損・スパイク（急騰・急落）・重複・日付不整合の検出
  - QualityIssue オブジェクトで問題を集約
- 監査ログ（audit）
  - signal → order_request → executions のトレーサビリティを保持する監査スキーマ
  - 発注の冪等キー、UTC タイムゾーン固定など運用を考慮した設計

---

## 動作環境・依存関係

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml

（開発環境やパッケージ定義は pyproject.toml / requirements.txt に従ってください）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージ開発インストール（プロジェクトルートに pyproject.toml がある場合）
pip install -e .
```

---

## 環境変数 / 設定

KabuSys は .env ファイルまたは環境変数から設定を読み込みます。プロジェクトルート（.git または pyproject.toml を基準）を自動検出して `.env` と `.env.local` を読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

オプション（デフォルト値や挙動）:
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH: DuckDB DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

設定の読み取りは `from kabusys.config import settings` で行えます（プロパティ経由でバリデーション済みの値が得られます）。

---

## セットアップ手順（概要）

1. Python 仮想環境を作る
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # その他パッケージがあれば requirements.txt / pyproject.toml に従う
   ```

3. 環境変数を設定（.env/.env.local をプロジェクトルートに作成）
   - 上記の必須環境変数を設定してください。

4. DuckDB スキーマ初期化
   - 例: Python REPL またはスクリプトで init_schema を呼ぶ
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   - 監査ログ専用 DB を使う場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   audit_conn.close()
   ```

---

## 使い方（主要 API の例）

以下は代表的な使い方サンプルです。詳細は各モジュールの docstring を参照してください。

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 市場カレンダー夜間更新ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
conn.close()
```

- RSS ニュース収集（既知銘柄セットを使って銘柄紐付け）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードの集合
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: new_saved_count}
conn.close()
```

- J-Quants の ID トークン取得（必要に応じて直接取得）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用してトークンを取得
```

- データ品質チェックの手動実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

---

## 主要モジュール説明

- kabusys.config
  - 環境変数の読み込み・バリデーションを実装。自動 .env ロード機構あり。
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、ページネーション、リトライ、データ整形・保存機能。
- kabusys.data.news_collector
  - RSS フィード取得、前処理、DuckDB への記事保存、銘柄抽出。
- kabusys.data.schema
  - DuckDB の DDL（Raw / Processed / Feature / Execution レイヤ）と初期化関数。
- kabusys.data.pipeline
  - ETL の差分取得ロジックと日次 ETL エントリポイント（run_daily_etl）。
- kabusys.data.calendar_management
  - カレンダー更新ジョブ、営業日判定ユーティリティ（next/prev/get_trading_days など）。
- kabusys.data.audit
  - 監査用テーブル定義・初期化（signal / order_request / executions）。
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合のチェック実装。

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（抜粋）:
```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ schema.py
   │  ├─ pipeline.py
   │  ├─ calendar_management.py
   │  ├─ audit.py
   │  └─ quality.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py
```

---

## 運用上の注意 / ベストプラクティス

- 環境変数とシークレットは `.env` に保存する場合、リポジトリにコミットしない（.gitignore に追加）。
- J-Quants のレートリミット（120 req/min）に注意。jquants_client はスロットリングを実装していますが、外部からの過剰な同時呼び出しは避けること。
- DuckDB ファイルのバックアップ・排他制御を運用面で考慮する（同一ファイルに複数プロセスで同時書き込みすると競合する可能性）。
- audit スキーマはトランザクション周りを慎重に扱う（init_audit_schema の transactional パラメータを理解して使う）。
- ニュース収集では外部 RSS の可用性・スキーマ差分に注意。fetch_rss は比較的寛容にフォールバックしますが、ソース差異に対応する必要があります。

---

## 開発・貢献

- コーディング規約、テスト、CI 設定はプロジェクトの pyproject.toml / .github/workflows などに従ってください。
- 自動環境ロード機能はテストで不要な場合、`KABUSYS_DISABLE_AUTO_ENV_LOAD` を有効にして無効化できます。

---

README は開発時の参照用に必要な情報をまとめています。各モジュールの詳細な使い方や API の引数・戻り値はソースコードの docstring を参照してください。必要であれば、README に使い方の具体的な CLI 例やユースケース（Paper trading ワークフロー、監査ログのクエリ例等）を追記できます。
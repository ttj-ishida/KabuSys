# KabuSys

日本株自動売買システムのライブラリ群（KabuSys）。  
データ取得（J‑Quants）、ETLパイプライン、ニュース収集、DuckDBスキーマ、監査ログ用スキーマ等を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームの基盤となるモジュール群です。  
主に以下を目的としています。

- J‑Quants API から株価・財務・市場カレンダーを安全に取得して DuckDB に保存する
- RSS からニュースを収集し正規化して保存・銘柄紐付けする
- データ品質チェック（欠損・重複・スパイク・日付整合性）を実行する
- ETL（差分取得・バックフィル・品質チェック）のワークフローを提供する
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマを提供する

設計上の特徴（抜粋）:
- API レート制御・リトライ（指数バックオフ）・トークン自動リフレッシュ
- Look‑ahead bias 対策（fetched_at の記録）
- DuckDB への冪等保存（ON CONFLICT による重複排除）
- RSS 収集における SSRF 防止、XML の安全パース、サイズ制限などセキュリティ配慮
- 品質チェックは全件検出を行い呼び出し側で対応を判断できる

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 判定
- J‑Quants API クライアント（kabusys.data.jquants_client）
  - ID トークン取得（リフレッシュトークン経由）
  - 日足（OHLCV）・財務（四半期）・市場カレンダー取得（ページネーション対応）
  - レートリミット、リトライ、401 時のトークンリフレッシュ
  - DuckDB への保存関数（save_* 系） — 冪等処理を行う
- RSS ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、テキスト前処理、記事ID生成（正規化URL→SHA‑256）
  - SSRF 防止（スキーム検証・プライベートIP検出・リダイレクト検査）
  - defusedxml による XML パース
  - DuckDB へのバルク保存（トランザクション・チャンク処理）
  - 銘柄コード抽出・news_symbols 保存
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL
  - init_schema(db_path) で初期化し接続を返す
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分算出 + backfill）
  - 日次 ETL（run_daily_etl）：カレンダー→株価→財務→品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日取得・期間の営業日列挙
  - calendar_update_job による夜間差分更新
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査用テーブルと初期化関数
  - init_audit_schema / init_audit_db を提供
- 品質チェック（kabusys.data.quality）
  - 欠損データ・スパイク・重複・日付不整合のチェック関数と集約実行

---

## セットアップ手順

前提:
- Python 3.9+（型注釈の記法や一部パッケージの互換性を想定）
- ネットワークから外部 API（J‑Quants）や RSS に接続できる環境

推奨依存パッケージ（例）:
- duckdb
- defusedxml

例: 仮想環境作成からインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API パスワード
- SLACK_BOT_TOKEN        : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID       : Slack チャネル ID

オプション（デフォルト値あり）
- KABUSYS_ENV            : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL              : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : SQLite（監視用）パス（デフォルト: data/monitoring.db）

.env 自動ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を順に読み込みます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主な API/コマンド例）

Python スクリプト内で直接呼び出すケースを想定した例を示します。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリを自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2) 監査ログ用スキーマを追加（既存接続へ）
```python
from kabusys.data.audit import init_audit_schema

# conn は init_schema から取得した接続
init_audit_schema(conn, transactional=True)
```

3) J‑Quants の ID トークン取得
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # env の JQUANTS_REFRESH_TOKEN を使って取得
```

4) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

5) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は既知銘柄コードのセット（例: データベースから読み出す）
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

6) 個別 ETL の実行（差分更新）
```python
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

7) 品質チェックのみ実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=None, reference_date=date.today())
for i in issues:
    print(i)
```

ログレベルや環境は環境変数（KABUSYS_ENV / LOG_LEVEL）で制御できます。

---

## ディレクトリ構成

以下はこのリポジトリの主要ファイル構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J‑Quants API クライアント（取得・保存）
    - news_collector.py      # RSS ニュース収集・保存
    - schema.py              # DuckDB スキーマ定義・初期化
    - pipeline.py            # ETL パイプライン（差分更新・run_daily_etl 等）
    - calendar_management.py # 市場カレンダー管理（営業日判定等）
    - audit.py               # 監査ログスキーマの定義と初期化
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記に加え、プロジェクトルートに pyproject.toml / .git などが想定されます。）

---

## 注意事項・設計上のポイント

- J‑Quants API のレート制限（120 req/min）を遵守するため内部でスロットリングを実装しています。大規模なバッチ処理を行う場合は呼び出し頻度に注意してください。
- ニュース収集では SSRF・XML Bomb・メモリ DoS 等に対応した複数の防御策を実装していますが、外部コンテンツを扱うため運用時は信頼できるフィードの管理を行ってください。
- DuckDB の接続は軽量ですが、複数プロセスによる同時書き込み等の運用は注意が必要です（ロックや排他制御）。
- audit スキーマはトレーサビリティを目的としており、削除しない前提の設計です。パーティショニングやアーカイブ運用を検討してください。
- 自動 .env 読み込みはテスト時に邪魔な場合があるため、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

---

## 貢献・開発

- コードスタイル、型注釈、エラーハンドリングに配慮した実装を行っています。新しい機能の追加や修正は PR を通じてお願いします。
- テスト: 各ネットワーク依存部分（HTTP 呼び出し・外部 API）はモック化を想定しています。ユニットテストでは環境変数や _urlopen 等を差し替えてテストしてください。

---

README に記載の内容はコードベースより抜粋しています。詳細な API 仕様やデータモデル（カラム定義等）は各モジュールのドキュメント（ソース内 docstring）を参照してください。
# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants / RSS などの外部データソースから市況データ・財務データ・ニュースを取得して DuckDB に保存し、ETL・品質チェック・マーケットカレンダー・監査ログを提供します。戦略層・実行層との接続を想定した基盤コンポーネント群を含みます。

主な設計方針：
- データの冪等性（INSERT ... ON CONFLICT）を重視
- API のレート制御・リトライ・トークン自動更新を内蔵
- SSRF / XML Bomb 等のセキュリティ対策を考慮したニュース収集
- DuckDB を用いたローカルデータプラットフォーム設計

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - リトライ（指数バックオフ）、401 時のトークン自動更新、レート制限（120 req/min）
  - DuckDB へ idempotent に保存する save_* 関数群

- ETL パイプライン
  - 差分更新 / バックフィル / カレンダー先読み / 品質チェックをまとめて実行する日次 ETL
  - 品質チェック（欠損、重複、スパイク、日付不整合）

- ニュース収集
  - RSS から記事取得、テキスト前処理、URL 正規化、記事 ID（SHA-256）生成
  - SSRF 対策・受信サイズ制限・defusedxml による安全な XML パース
  - raw_news / news_symbols への冪等保存

- マーケットカレンダー管理
  - 営業日判定、前後の営業日検索、期間内営業日取得
  - 夜間バッチでカレンダー差分更新

- 監査ログ（Audit）
  - signal_events / order_requests / executions といった監査テーブルの初期化
  - 発注→約定までのトレーサビリティを保証

- スキーマ管理
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema / init_audit_db 等の初期化ユーティリティ

---

## 要件 / 推奨環境

- Python 3.10 以上（型記法（|）や TypedDict を使用しています）
- 主要依存ライブラリ（インストール必須）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）

パッケージをローカルで使う場合（開発用）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージを開発インストールする場合
pip install -e .
```

（プロジェクトに pyproject.toml / requirements.txt があればそこから依存をインストールしてください）

---

## 環境変数（設定）

設定は .env ファイルまたは環境変数から読み込まれます。プロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` が自動で読み込まれます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な必須環境変数：
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID（必須）

その他オプション：
- KABUSYS_ENV: 実行環境（development, paper_trading, live）。デフォルト "development"
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルト "INFO"
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効にするフラグ（"1" 等で有効）

.env の読み込みルールは細かい挙動（クォート、コメント、export プレフィックス等）に対応しています。

簡易 .env 例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. Python の仮想環境作成・依存インストール
   - 例: pip install duckdb defusedxml

2. 環境変数を設定（.env をプロジェクトルートに配置）
   - 上の必須変数を .env に記載

3. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb
     ```
   - 監査ログ用 DB の初期化（別 DB にしたい場合）:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

4. （任意）SQLite 等の監視 DB を準備（プロジェクト内の監視モジュールが利用する場合）

---

## 使い方（主要 API と実行例）

以下は代表的な利用パターンの例です。実運用ではログ設定・例外処理・ジョブスケジューラ（cron / Airflow 等）での運用を想定します。

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

# DB 初期化（初回のみ）
conn = init_schema(settings.duckdb_path)

# 日次 ETL 実行（target_date を指定することで過去日の再実行も可能）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# known_codes は銘柄コードセット（例: 証券一覧やマスターから取得）
known_codes = {"7203", "6758", "9984"}

results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print("saved calendar records:", saved)
```

- J-Quants の直接呼び出し（トークン自動取得・ページネーション対応）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
quotes = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
# 取得結果を DB に保存する場合は jquants_client.save_daily_quotes を使う
```

- 品質チェックの単体実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 注意点 / 実装上のポイント

- J-Quants クライアントはレート制御（120 req/min）を行い、リトライや 401 自動更新を備えています。大量取得時や並列処理時はこの制約に注意してください。
- ニュース収集は RSS の安全性（SSRF・XML Bomb 等）に配慮していますが、外部ソースの変更や特殊フィードにより想定外の挙動が発生する可能性があります。ログ監視を推奨します。
- DuckDB のスキーマは冪等であり、init_schema は既存テーブルを上書きしません。監査スキーマは init_audit_schema / init_audit_db で追加できます。
- settings（環境変数）は Settings クラス経由で取得できます。必須値が未設定の場合は ValueError が発生します。
- 日次 ETL は品質チェックで見つかった問題を収集しますが、ETL 自体は基本的に続行し、呼び出し側が致命的かどうか判断する設計です。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース収集・保存ロジック
    - schema.py                — DuckDB スキーマ定義・初期化
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — マーケットカレンダー管理（判定・更新）
    - audit.py                 — 監査ログスキーマ初期化
    - quality.py               — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（README に記載の API は主に data パッケージにあり、strategy / execution / monitoring は今後の拡張ポイントとして空のパッケージを用意しています）

---

## 開発・運用のヒント

- 自動運用：run_daily_etl や calendar_update_job、run_news_collection を cron / systemd timer / Airflow / Prefect 等で定期実行して運用します。
- ロギング：LOG_LEVEL を環境変数で切替可能。運用時は INFO/DEBUG を適宜選択し、ログ集約（Cloud/ファイル）を行ってください。
- テスト：外部 API をモックして単体テストを作成してください（jquants_client の _urlopen や _RateLimiter などは置き換えが可能）。
- セキュリティ：.env にシークレットを置く場合は権限管理を徹底してください。.env をリポジトリにコミットしないでください。

---

README は以上です。必要であれば以下を生成します：
- .env.example の完全なテンプレート
- サンプルの起動スクリプト（systemd / cron 用）
- より詳細な API リファレンス（関数ごとの引数・戻り値まとめ）

どれを追加しますか？
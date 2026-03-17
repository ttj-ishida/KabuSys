# KabuSys

日本株自動売買システム用ユーティリティライブラリ（データ取得・ETL・スキーマ・監査・ニュース収集など）

## プロジェクト概要
KabuSys は日本株の自動売買プラットフォーム向けに設計された補助ライブラリ群です。主に以下を提供します：

- J-Quants API からの市場データ（株価日足、財務データ、マーケットカレンダー）取得クライアント
- RSS ベースのニュース収集・前処理・DB保存
- DuckDB によるデータスキーマ定義と初期化
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（シグナル→発注→約定のトレース用テーブル群）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、API レート制御、リトライ、冪等性（ON CONFLICT）やセキュリティ対策（SSRF対策・XML攻撃対策）を重視しています。

## 主な機能一覧
- jquants_client
  - get_id_token（リフレッシュトークンで idToken を取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - save_* 系で DuckDB に冪等保存
  - RateLimiter・リトライ・401 自動リフレッシュなどの実装
- data.schema
  - init_schema(db_path) — DuckDB の全テーブル／インデックスを作成
  - get_connection(db_path)
- data.pipeline
  - run_daily_etl — 日次 ETL パイプライン（カレンダー→株価→財務→品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- data.news_collector
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
  - RSS 正規化、トラッキングパラメータ削除、SSRF 回避、gzip サイズ制限、defusedxml 使用
- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- data.audit
  - 監査用スキーマ初期化（signal_events / order_requests / executions 等）
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（品質問題を一覧で取得）

## 動作要件
- Python 3.10 以上（コード内で | 型注釈などを使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ：urllib, json, datetime, logging, hashlib, ipaddress, socket など

requirements.txt がある場合はそれを使用してください。なければ最低限上記パッケージをインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# または requirements.txt があれば:
# pip install -r requirements.txt
```

## セットアップ手順（簡易）
1. リポジトリをクローン／配置
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数を設定（またはプロジェクトルートに .env/.env.local を置く）
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
4. DuckDB スキーマを初期化

例:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

監査ログ専用 DB を初期化する場合:
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/audit.duckdb")
```

## 必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN ・・・ J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD       ・・・ kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL       ・・・ kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN         ・・・ Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID        ・・・ Slack チャンネル ID（必須）
- DUCKDB_PATH             ・・・ DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH             ・・・ SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV             ・・・ 動作環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL               ・・・ ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

.env の例（プロジェクトルートに .env を置くと自動読み込みされます）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: settings プロパティは未設定の必須 env を要求すると ValueError を投げます（例: settings.jquants_refresh_token）。

## 使い方（主な例）

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（市場データ取得→保存→品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 取得→raw_news 保存→銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

# known_codes は既知の銘柄コード集合（例: '7203','6758' ...）
known_codes = {"7203", "6758"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

saved = calendar_update_job(conn)
print("saved:", saved)
```

- 監査スキーマの初期化（既存の conn に追加）
```python
from kabusys.data import audit
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

audit.init_audit_schema(conn, transactional=True)
```

## トラブルシューティング（よくある問題）
- ValueError: 環境変数が見つからない
  - JQUANTS_REFRESH_TOKEN など必須変数が未設定の可能性。`.env` を確認してください。
- duckdb import エラー
  - duckdb パッケージがインストールされているか確認してください。
- ネットワーク系の例外（urllib.error.URLError 等）
  - API の到達性、プロキシやファイアウォール、URL のスキーム（http/https）を確認してください。
- RSS 取得が失敗して記事が保存されない
  - サイズ上限（デフォルト 10MB）や gzip 解凍失敗、XML パースエラー（defusedxml により保護）等が原因になることがあります。ログを確認してください。

## ディレクトリ構成
以下は本リポジトリ内の主要ファイル／モジュール構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理（.env 自動読み込みロジック、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      — RSS ニュース収集・正規化・DB 保存
    - schema.py              — DuckDB スキーマ定義と init_schema
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査ログテーブル定義・初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

上記のモジュール群は、さらに戦略層（strategy）・実行層（execution）・監視（monitoring）と組み合わせて利用することを想定しています。

## 開発上の注意点 / 設計ポリシー（抜粋）
- API レート制御（120 req/min）に従った実装
- リトライと指数バックオフ、401 の自動リフレッシュ対応
- DuckDB への保存は冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）
- RSS はトラッキングパラメータ除去→URL正規化→SHA-256 先頭 32 文字で記事IDを生成（冪等）
- SSRF 対策、XML の安全パース、レスポンスサイズ制限などセキュリティ配慮
- 品質チェックは Fail-Fast ではなく全チェックを行い、呼び出し元が結果に応じて判断

---

不明点があれば、使用したいユースケース（例: 初回ロード手順、定期バッチの実行方法、カスタム RSS ソース追加など）を教えてください。具体例に基づいて README を拡充します。
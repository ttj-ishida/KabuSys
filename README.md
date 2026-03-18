# KabuSys

日本株自動売買プラットフォームのコアライブラリです。  
データ収集（J-Quants / RSS ニュース）・ETL・品質チェック・スキーマ定義・監査ログなど、トレーディングシステムの基盤機能を提供します。

主な設計方針
- データの冪等性（DuckDB へ ON CONFLICT）を重視
- API レート制限とリトライ制御（J-Quants クライアント）
- Look‑ahead bias 防止のため fetched_at 等のトレーサビリティを保持
- ニュース収集におけるセキュリティ対策（SSRF、XML Bomb、サイズ制限）
- DB スキーマは Raw / Processed / Feature / Execution（監査含む）で分離

---

## 機能一覧

- 環境変数/設定管理
  - .env / .env.local の自動読み込み（ルートの .git または pyproject.toml を検出）
  - 必須キー取得時の検証
- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得
  - RateLimiter（120 req/min）と指数バックオフ、401時のトークン自動リフレッシュ
  - DuckDB への冪等保存（save_* 系）
- ニュース収集（RSS）
  - RSS 取得、前処理（URL 除去・空白正規化）、ID 生成（正規化 URL の SHA-256）、DuckDB への挿入
  - SSRF 対策、defusedxml による XML パース保護、受信サイズ制限
  - 銘柄コード抽出（4桁）と news_symbols への紐付け
- ETL パイプライン
  - 差分取得（最終取得日からの差分／バックフィル対応）
  - run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック の順）
  - 個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック
  - 欠損データ、スパイク（前日比閾値）、主キー重複、日付不整合（未来日など）
  - 問題は QualityIssue オブジェクトで集約（error / warning）
- DuckDB スキーマ管理
  - init_schema：全テーブル・インデックスを作成（Raw/Processed/Feature/Execution）
  - 監査ログ用スキーマ（signal_events, order_requests, executions）と初期化ヘルパ（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提
- Python 3.8+ 推奨（型注釈や TypedDict、duckdb 等の互換性のため）
- duckdb, defusedxml 等が必要

基本インストール例（プロジェクトルートで実行）
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクト配布で setup.py / pyproject.toml があれば pip install -e . も想定）

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨される環境変数（.env の例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # 有効値: development, paper_trading, live
- LOG_LEVEL=INFO

例（.env）
```
JQUANTS_REFRESH_TOKEN=YOUR_REFRESH_TOKEN
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（簡単なサンプル）

下記は対話的に使う際の最小例です。プロダクションではジョブスケジューラやワーカーから呼び出してください。

1) DuckDB スキーマを初期化して接続を取得
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())  # ETLResult の概要
```

3) ニュース収集ジョブ（RSS を取得して raw_news に保存）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は抽出対象の銘柄コードセット（無ければ抽出をスキップ）
known_codes = {"7203", "6758", "9432"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

4) 監査ログ用 DB を初期化（監査専用 DB を別ファイルに分ける場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# もしくは既存 conn に対して init_audit_schema(conn)
```

5) J-Quants API を直接利用（トークン取得等）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意点
- settings（kabusys.config.settings）から環境設定を取得できます。
- 自動で .env を読み込む挙動はプロジェクトルートを基準にします（CWD 非依存）。
- run_daily_etl 等は内部で可能な限りエラーを局所的に扱い、他のステップは継続する設計です。戻り値の ETLResult で詳細を確認してください。

---

## ディレクトリ構成

主要なファイル・モジュールのツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（fetch / save）
    - news_collector.py       # RSS ニュース収集・保存・銘柄抽出
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  # マーケットカレンダー管理・営業日判定
    - schema.py               # DuckDB スキーマ定義・初期化
    - audit.py                # 監査ログ（signal/events/order_requests/executions）
    - quality.py              # データ品質チェック
    - pipeline.py             # ETL のエントリを含む（再掲）
  - strategy/
    - __init__.py             # 戦略関連（実装はこのツリーで拡張）
  - execution/
    - __init__.py             # 注文・実行・ブローカー連携（拡張地点）
  - monitoring/
    - __init__.py             # 監視・メトリクス関連（拡張地点）

主な機能は data パッケージに集中しています。strategy, execution, monitoring は拡張用のプレースホルダです。

---

## 実装で注意する点 / 補足

- J-Quants クライアントはレート制御・リトライ・401 の自動リフレッシュを備えています。大量取得時は設定を尊重してください。
- ニュース収集はセキュリティ（SSRF、XML Bomb、Gzip Bomb、外部IP へのリダイレクト）に配慮して実装されています。外部リダイレクトや private アドレスへのアクセスはブロックされます。
- DuckDB の初期化は冪等（IF NOT EXISTS）で実行されます。init_schema は既存テーブルを壊しません。
- 監査スキーマは UTC を前提にしています（init_audit_schema は TimeZone を UTC に設定）。
- settings.env の値（KABUSYS_ENV）は "development" / "paper_trading" / "live" のいずれかである必要があります。
- 自動 .env ロードの順序: OS 環境 > .env.local > .env（.env.local は .env を上書き）。テスト時に自動ロードを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

この README はコードベースの概要・初期セットアップ・主要な操作方法を示しています。  
詳細な運用設計・本番構成（認証情報管理、監査・バックアップ、監視、CI/CD、ブローカー連携実装等）は別途ドキュメント化してください。
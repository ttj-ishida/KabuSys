# KabuSys

日本株自動売買プラットフォーム（KabuSys）の軽量コアライブラリです。  
データ取得（J-Quants）、DuckDB スキーマ、監査ログ、品質チェック、および取引フローのための基盤的モジュール群を提供します。

主な設計方針：
- データレイヤを Raw / Processed / Feature / Execution の 3+1 層で整理
- J-Quants API のレート制限・リトライ・トークンリフレッシュ対応
- DuckDB を使った冪等的な永続化（ON CONFLICT DO UPDATE）
- 発注から約定までを UUID で完全トレース可能な監査ログ
- データ品質チェック（欠損・異常値・重複・日付不整合）

バージョン: 0.1.0

---

## 機能一覧

- 環境変数・設定管理（自動 .env 読み込み、必須チェック）
  - 自動読み込み優先度: OS 環境 > .env.local > .env
  - テスト用途の KABUSYS_DISABLE_AUTO_ENV_LOAD
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制限（120 req/min）制御、リトライ（指数バックオフ、最大 3 回）
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）
  - fetched_at（UTC）で取得時刻を記録
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル群とインデックスを定義
  - init_schema() による冪等的初期化
- 監査ログ（注文フローのトレーサビリティ）
  - signal_events, order_requests, executions 等を定義
  - order_request_id を冪等キーとして二重発注回避
  - init_audit_schema()/init_audit_db() を提供
- データ品質チェック
  - 欠損データ検出、スパイク検出（前日比閾値）、重複チェック、日付整合性チェック
  - run_all_checks() でまとめて実行し QualityIssue のリストを返す

---

## 要件

- Python 3.10+
  - 型注釈に PEP 604（`|`）を利用しているため 3.10 以上を想定
- 依存パッケージ（最低限）
  - duckdb
- 標準ライブラリ: logging, urllib, json, datetime, pathlib など

インストール（例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# （パッケージ配布があれば pip install -e . など）
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境の作成と依存インストール
   - pip install duckdb
3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD 依存せずパッケージ内パスから探索）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

推奨の .env（例）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須環境変数（Settings にて参照／検証）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション:
- KABUSYS_API_BASE_URL（既定: http://localhost:18080/kabusapi）
- DUCKDB_PATH（既定: data/kabusys.duckdb）
- SQLITE_PATH（既定: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

---

## 使い方（コード例）

以下は代表的な利用例です。実運用前に各種トークン・接続先を正しく設定してください。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path を返します（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
records = fetch_daily_quotes(code="7203")  # トヨタ等、code を省略すると全銘柄
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

3) 財務データやマーケットカレンダーの取得・保存
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
records = fetch_financial_statements(code="7203")
save_financial_statements(conn, records)

from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar
cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

4) 監査ログの初期化（既存の conn に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # conn は init_schema で得た DuckDB 接続
```

または監査専用 DB を作る:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

5) データ品質チェック
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity, issue.detail)
```

設計ノート:
- J-Quants クライアントは内部で rate limiter を使います。大量取得を行う場合でも 120 req/min に従います。
- API 呼び出しは最大 3 回のリトライ（408/429/5xx 等）を行い、429 の場合は Retry-After を尊重します。
- get_id_token() はリフレッシュトークンから idToken を取得し、モジュール内でキャッシュします（ページネーション間で共有）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py              -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py    -- J-Quants API クライアント（取得・保存ロジック）
      - schema.py           -- DuckDB スキーマ定義・初期化
      - audit.py            -- 監査ログ（注文フローのトレーサビリティ）
      - quality.py          -- データ品質チェック
      - (その他: news, executions 等の将来的モジュール)
    - strategy/
      - __init__.py         -- 戦略層用プレースホルダ
    - execution/
      - __init__.py         -- 実行層用プレースホルダ
    - monitoring/
      - __init__.py         -- 監視・メトリクス用プレースホルダ

ドキュメント参照:
- DataSchema.md, DataPlatform.md（コード内ドキュメントで参照されている設計資料）

---

## 開発・貢献

- 自動 .env 読み込みの無効化はテストで便利です:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- type hints と静的解析を通すことで保守性を高めています。フォーマット・lint を整えることを推奨します。

---

## ライセンス / 注意事項

- 本リポジトリのコードは取引ロジックそのものを含まない基盤ライブラリです。実際の売買を行う場合は十分なテスト・監査を行い、法令や証券会社の規約に従ってください。
- 実際の運用環境（特に live モード）では、環境変数・シークレットの管理・ログ出力に注意し、十分な権限分離とバックアップを行ってください。

---

必要であれば README に含めるサンプル .env.example や、CI / デプロイ手順、より詳細な API 使用例（ページネーションを含む）を追加できます。どの情報を追加したいか教えてください。
# KabuSys

日本株向け自動売買システムのコアライブラリ（ミニマム実装）。  
データ取得（J-Quants / RSS）、ETL、DuckDB スキーマ、品質チェック、監査ログ用スキーマなどを提供します。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買プラットフォームの基盤コンポーネント群です。本コードベースは以下の主要機能を持ち、実運用で必要なトレーサビリティやデータ品質保守、外部 API の扱い方（レート制御・リトライ・認証トークン更新）等を考慮した設計になっています。

主な設計方針：
- データ取得は冪等（重複挿入を避ける）に実装
- API 呼び出しはレート制限とリトライを実装（J-Quants）
- ニュース収集は SSRF / XML 攻撃対策、サイズ制限等の防御を実施
- DuckDB を中心に Raw / Processed / Feature / Execution / Audit 層のスキーマを定義
- ETL は差分取得・バックフィル・品質チェックを含む一連の処理を提供

---

## 機能一覧

- 環境設定管理
  - .env（および .env.local）を自動で読み込む（無効化可）
  - 必須値チェック（取得時に未設定なら例外）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - daily quotes（OHLCV）、financial statements、market calendar 取得
  - 固定間隔レートリミット（120 req/min）
  - 指数バックオフによるリトライ（408/429/5xx 等）
  - 401 時にリフレッシュトークンで自動更新して再試行
  - DuckDB への冪等保存用 save_* 関数
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、記事ID の生成（正規化 URL → SHA-256）
  - defusedxml を使った安全な XML パース
  - SSRF 対策（スキーム検証、プライベート IP 検出、リダイレクト検査）
  - レスポンスサイズ制限、gzip 解凍後のサイズチェック
  - DuckDB へ冪等保存（INSERT ... ON CONFLICT / RETURNING を使用）
  - テキストから銘柄コード抽出（4桁）と news_symbols の紐付け
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤの DDL 定義
  - 読み込み用の init_schema(), get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日からの差分判定）、バックフィル、保存
  - 日次 ETL の統合エントリ run_daily_etl()
  - 品質チェック統合（kabusys.data.quality）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次/前営業日の計算、カレンダーの夜間更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution のトレーサビリティ用スキーマ
  - 監査用 DB 初期化補助
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（急騰/急落）、日付整合性チェック
  - QualityIssue オブジェクトで問題を集約

※ strategy、execution、monitoring パッケージはプレースホルダ（このコードベースでは未実装）です。

---

## 動作要件（推奨）

- Python 3.9+
- 依存パッケージ（主なもの）
  - duckdb
  - defusedxml

（プロジェクト配布時は requirements.txt を用意してください。ここでは例示）

インストール例：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数

自動でプロジェクトルート（.git または pyproject.toml を持つ親ディレクトリ）から `.env` と `.env.local` を読み込みます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（README 内で使用されるもの）：

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client が ID トークンを取得するために使用。

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード（execution 関連で使用想定）。

- KABU_API_BASE_URL (任意)  
  kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン（monitoring 等で使用想定）

- SLACK_CHANNEL_ID (必須)  
  Slack 通知対象チャンネル ID

- DUCKDB_PATH (任意)  
  DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH (任意)  
  監視用 SQLite（デフォルト: data/monitoring.db）

- KABUSYS_ENV (任意)  
  実行環境: development / paper_trading / live（デフォルト: development）

- LOG_LEVEL (任意)  
  ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例 .env の一部（サンプル）:
```
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=yyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install duckdb defusedxml
   ```

3. 環境変数を準備
   - プロジェクトルートに `.env` を作成し、必要な値を設定します（上記参照）。
   - テスト時や CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードをオフにできます。

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトから:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # もしくは in-memory:
   # conn = schema.init_schema(":memory:")
   ```
   監査ログ専用 DB を別途作りたい場合:
   ```python
   from kabusys.data import audit
   conn = audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な操作例）

以下はライブラリの代表的な利用例です。実行は仮想環境内で行ってください。

- J-Quants から日次データを取得して保存（ETL 実行）
```python
from datetime import date
import duckdb

from kabusys.data import schema, pipeline

# DB 初期化（ファイルがなければ作成）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL（省略時は今日が対象。戻り値は ETLResult）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブの実行（RSS）
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
# known_codes を与えると銘柄紐付けを実行（空なら紐付けスキップ）
known_codes = {"7203", "6758", "9984"}
res = news_collector.run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

- J-Quants の生データ取得（個別）
```python
from kabusys.data import jquants_client as jq
# トークンは settings.jquants_refresh_token を使う（.env に設定）
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# DuckDB に保存
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)
```

- 品質チェックの実行
```python
from kabusys.data import quality, schema
conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

- カレンダーの夜間更新ジョブ
```python
from kabusys.data import calendar_management, schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

---

## 主要モジュール一覧（ディレクトリ構成）

リポジトリの主要ファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（settings をエクスポート）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制御・リトライ・トークン更新・保存関数）
    - news_collector.py
      - RSS 収集、前処理、DuckDB への保存、銘柄抽出・紐付け
    - schema.py
      - DuckDB の DDL 定義と init_schema()
    - pipeline.py
      - ETL の差分ロジック、run_daily_etl()
    - calendar_management.py
      - 営業日判定、calendar_update_job 等
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py
      - 監査ログ用 DDL と初期化（init_audit_db）
  - strategy/
    - __init__.py  # 戦略関連プレースホルダ（拡張ポイント）
  - execution/
    - __init__.py  # 発注・ブローカ連携プレースホルダ
  - monitoring/
    - __init__.py  # 監視・アラート用プレースホルダ

---

## 設計上の注意点 / セキュリティ考慮

- API レート制御（J-Quants）: 固定間隔スロットリングを採用し 120 req/min を守る設計。
- 認証: 401 で自動的に ID トークンをリフレッシュするが、再帰防止のためリフレッシュは 1 回のみ。
- RSS/NLP:
  - defusedxml を使用し XML Bomb などの脆弱性を軽減。
  - URL スキームを限定（http/https のみ）、プライベート IP へのアクセスを拒否して SSRF を防止。
  - レスポンスサイズ制限（デフォルト 10 MB）と gzip 解凍後のチェックを行う。
- DB 保存: 多くの保存処理は ON CONFLICT / DO UPDATE / DO NOTHING を用いて冪等性を確保。
- 監査ログ: order_request_id 等で冪等性を確保し、トレーサビリティを維持するスキーマを持つ。

---

## 拡張・運用のヒント

- strategy/ と execution/ パッケージは戦略ロジック・ブローカ接続を実装するための拡張ポイントです。戦略は signal_events に記録し、order_requests を経て executions に反映するフローを想定しています。
- 本ライブラリは DuckDB を中心に設計されているため、運用時は定期的なバックアップと VACUUM（必要なら）を検討してください。
- CI / テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境変数の自動読み込みを抑え、テスト専用の環境値を注入してください。

---

## 最後に

この README はコードベースの現状実装（データ取得・ETL・スキーマ定義・品質チェック・ニュース収集等）に基づく概要と使い方をまとめたものです。戦略実装やブローカ連携、監視周りはプロジェクト要件に応じて実装を追加してください。

ご要望があれば、README にサンプル .env.example、requirements.txt の提案、CI / Cron バッチ実行例や Docker 化手順などの追記を作成します。
# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
J-Quants / kabuステーション 等の外部データ・ブローカーと連携して、データ収集（ETL）、品質チェック、ニュース収集、監査ログ、実行レイヤーのスキーマ管理を提供します。

主な設計方針：
- データの冪等性（ON CONFLICT による上書き/非重複）を重視
- API レート制限・リトライ・トークン自動リフレッシュ対応
- Look-ahead bias を防ぐため取得時刻（UTC）を記録
- RSS ニュース収集において SSRF / XML Bomb / 大容量レスポンス対策などセキュリティ考慮

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルートを探索）
  - 必須環境変数チェック（Settings クラス）

- J-Quants API クライアント（data/jquants_client.py）
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レートリミット制御、再試行（指数バックオフ）、401 時トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（raw_prices, raw_financials, market_calendar）

- RSS ニュース収集（data/news_collector.py）
  - RSS からニュースを取得、前処理（URL除去・空白正規化）
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 で記事ID生成（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト検査）
  - defusedxml を使った XML パース安全化
  - DuckDB への冪等保存（raw_news / news_symbols）

- データスキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution / Audit 用の DuckDB テーブル定義
  - init_schema() による初期化ユーティリティ

- ETL パイプライン（data/pipeline.py）
  - 差分更新（最後取得日に基づく差分取得、バックフィル対応）
  - 市場カレンダー先読み
  - 品質チェック呼び出しと結果集約（data/quality.py）

- カレンダー管理（data/calendar_management.py）
  - 営業日判定、前後営業日取得、期間の営業日列挙
  - 夜間バッチのカレンダー更新ジョブ

- 品質チェック（data/quality.py）
  - 欠損データ、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue オブジェクトで報告

- 監査ログ（data/audit.py）
  - シグナル→発注→約定までのトレーサビリティ用テーブル群と初期化ユーティリティ
  - order_request_id を冪等キーとして使用

---

## 必要要件 / 依存パッケージ

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリで多くの HTTP/URI 処理を行います（urllib 等）

インストール例（最低限）:
```bash
python -m pip install "duckdb" "defusedxml"
# またはプロジェクト配布パッケージがあれば: pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. Python 仮想環境を準備して依存をインストール
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# その他必要なパッケージがあれば追加インストール
```

3. 環境変数を設定
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 必須項目（例）:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack 通知先チャンネルID
- 任意 / デフォルト:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（デフォルト）

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB スキーマの初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

5. （監査ログを別DBで管理したい場合）
```python
from kabusys.data import audit
conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（基本例）

以下は主要機能を呼び出す最小例です。実運用ではログ設定や例外処理、ジョブスケジューラ（cron / Airflow 等）と組み合わせてください。

- 日次 ETL の実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline

# DB 初期化（既に init 済みなら get_connection）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次ETLを実行（引数で target_date や id_token を渡せます）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ（RSS を収集して raw_news に保存、既知銘柄で symbols を紐付け）
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードのセット（例: {'7203','6758', ...}）
known_codes = {"7203", "6758"}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- カレンダー夜間バッチ実行
```python
from kabusys.data import calendar_management, schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved={saved}")
```

- 監査ログスキーマ初期化（既存 conn に追加）
```python
from kabusys.data import audit, schema
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
```

- J-Quants から直接データを取得する（テストや部分取得）
```python
from kabusys.data import jquants_client as jq
# トークンは settings が参照する環境変数から取得されます
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 環境変数の自動読み込み挙動

- 自動ロード対象ファイル: プロジェクトルートの `.env` と `.env.local`
- 優先度: OS 環境変数 > .env.local > .env
- 自動ロードを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 自動検出されるプロジェクトルート:
  - このパッケージ内から親ディレクトリを辿り `.git` または `pyproject.toml` の存在を基準に探します。
  - 見つからない場合は自動ロードをスキップします。

.env のパースは以下に対応:
- `export KEY=val` 形式
- シングル・ダブルクォート付値、エスケープ、インラインコメントの扱い
- コメント行 / 空行を無視

必要な必須環境変数は Settings クラスからアクセスすると ValueError で明示されます。

---

## ディレクトリ構成

リポジトリ内の主要ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存）
    - news_collector.py          — RSS ニュース収集・保存ロジック
    - schema.py                  — DuckDB スキーマ定義 / init_schema()
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     — 市場カレンダー管理 / ヘルパー
    - audit.py                   — 監査ログ（シグナル→発注→約定）
    - quality.py                 — データ品質チェック
  - strategy/                     — 戦略関連（未実装のパッケージプレースホルダ）
  - execution/                    — 発注・実行関連（未実装のパッケージプレースホルダ）
  - monitoring/                   — 監視関連（未実装のパッケージプレースホルダ）

---

## 開発メモ / 注意点

- DuckDB を使用するため、データの保存・クエリはローカルファイルで完結できます。運用時はバックアップや排他アクセス（複数プロセスの同時書き込み）を設計してください。
- J-Quants API はレート制限（120 req/min）に注意。クライアントは内部でスロットリングを実施しますが、複数並列プロセスでの呼び出しはさらに注意が必要です。
- ニュース収集は外部 URL を扱うため SSRF / XML 攻撃対策を実装しています。テスト時に _urlopen をモックして外部アクセスを避けられます。
- ログレベル・環境（development / paper_trading / live）は環境変数で制御してください。live 環境では注文実行などを慎重に扱ってください（このコードベースには実際のブローカー連携の実装は含まれていません）。

---

この README はコードベースからの抜粋に基づいて作成しています。運用や拡張の際は各モジュールの docstring を参照してください。質問やサンプル実行例が必要であればお知らせください。
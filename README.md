# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータ取得・品質管理・ETL・監査ログ基盤を備えた自動売買プラットフォームのライブラリ群です。J-Quants API から市場データや財務データ、JPX カレンダーを取得し、DuckDB に冪等的に保存します。品質チェック・差分更新・監査ログ（発注から約定までのトレーサビリティ）を設計原則として実装しています。

---

## 特徴（概要）

- J-Quants API クライアント
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、市場カレンダーを取得
  - API レートリミット（120 req/min）対応（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）およびトークン自動リフレッシュ（401 対応）
  - 取得時刻（fetched_at）を UTC で記録し look-ahead bias を防止
  - ページネーション対応

- データ基盤（DuckDB）
  - Raw / Processed / Feature / Execution（監査含む）を想定したスキーマ定義
  - ON CONFLICT DO UPDATE による冪等的保存
  - スキーマ初期化ユーティリティ（init_schema）

- ETL パイプライン
  - 日次差分更新（最終取得日からの差分/バックフィル）
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - エラーが発生しても他のステップは継続（Fail-Fast ではない）

- 品質チェック（quality モジュール）
  - 欠損データ / 主キー重複 / 株価スパイク / 日付不整合を検出
  - 問題は QualityIssue データクラスに集約（severity により上流での判断可能）

- 監査ログ（audit モジュール）
  - シグナル → 発注要求 → 約定 を UUID 連鎖でトレース可能にするテーブル群
  - 発注の冪等性（order_request_id）とタイムスタンプは UTC 固定

---

## 必要条件

- Python 3.10 以上
  - 型注釈に X | Y 形式（PEP 604）を使用しているため 3.10+ が必要です
- duckdb（DuckDB Python バインディング）
- ネットワークアクセス（J-Quants API）

必要に応じて仮想環境を作成してください（venv, poetry 等）。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# プロジェクトを editable インストールする場合
# pip install -e .
```

（本リポジトリに requirements.txt がある場合はそちらを使用してください）

---

## 環境変数（設定）

自動ロード:
- パッケージロード時にプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env`、`.env.local` を自動読み込みします。
- 自動読み込みを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途等）

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション等の API パスワード（発注モジュール利用時）
- SLACK_BOT_TOKEN: Slack 通知を行う場合の Bot Token
- SLACK_CHANNEL_ID: Slack の通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live"), デフォルト "development"
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"), デフォルト "INFO"
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH: 監視用 sqlite ファイルパス（デフォルト "data/monitoring.db"）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効にする（値は任意）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（初期化）

1. 依存ライブラリをインストール
   - duckdb をインストールしてください（pip install duckdb）
   - プロジェクトをパッケージとして使う場合は pip install -e .（setup があれば）

2. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか環境変数をエクスポートしてください。
   - 必須変数（JQUANTS_REFRESH_TOKEN など）を設定すること。

3. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで以下を実行してスキーマを作成します。

```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH の値を返します
conn = schema.init_schema(settings.duckdb_path)
# あるいはファイルパスを直接指定
# conn = schema.init_schema("data/kabusys.duckdb")
```

4. 監査ログスキーマの初期化（必要な場合）
```python
from kabusys.data import audit
# 既存接続に監査テーブルを追加
audit.init_audit_schema(conn)

# または監査専用 DB を作成
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要 API と実行例）

- 簡単な日次 ETL 実行例

```python
from kabusys.data import schema, pipeline
from kabusys.config import settings

# DB 初期化（初回のみ）
conn = schema.init_schema(settings.duckdb_path)

# 日次 ETL を実行（target_date を指定しない場合は本日）
result = pipeline.run_daily_etl(conn)

# 結果確認
print(result.to_dict())
# ETLResult.has_errors / has_quality_errors で判定可能
```

- 差分更新や個別ジョブの呼び出し
  - run_calendar_etl / run_prices_etl / run_financials_etl は個別に実行可能。
  - id_token をテスト注入することでネットワークをモックしやすい設計。

- J-Quants の ID トークン取得
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得
```

- 品質チェックの単体実行
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 設計上の注意点 / 動作ポリシー

- API レート制限（120 req/min）を守るため、固定間隔のスロットリングを導入しています。大量の銘柄ループを行うと API に到達できない場合があるため、ETL 実行頻度・並列性は注意してください。
- 取得したデータには fetched_at を付与し、いつデータを得たかを明確にしています（look-ahead bias 回避）。
- ETL は冪等性を重視しています。save_* 関数は ON CONFLICT DO UPDATE を使用して重複を排除します。
- 品質チェックは fail-fast ではなくすべての問題を収集して呼び出し元に返します。ETL の続行可否は呼び出し元の判断に委ねています。

---

## ディレクトリ構成

（プロジェクトのソースは src/kabusys 配下に存在します）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント（取得 / 保存ロジック）
      - schema.py              — DuckDB スキーマ定義と初期化
      - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
      - audit.py               — 監査ログ（発注 → 約定のトレーサビリティ）
      - quality.py             — データ品質チェック
    - strategy/
      - __init__.py            — 戦略層（未実装のエントリポイント）
    - execution/
      - __init__.py            — 発注 / 約定管理（未実装のエントリポイント）
    - monitoring/
      - __init__.py            — 監視・通知関連（未実装のエントリポイント）

---

## 開発 / 貢献

- コードはモジュール毎に責務を分け、テスト容易性を考慮して id_token 等の注入をサポートしています。
- PR / Issue の際は再現方法とログ（debug レベル）を添えてください。
- 自動読み込みされる .env のパースはシェル風のクォートやコメント表記に対応していますが、複雑なケースは明示的に環境変数をエクスポートすることを推奨します。

---

## 参考・補足

- 設定クラス Settings（kabusys.config.settings）を通じて設定へアクセスできます。
- KABUSYS_ENV の有効値: development / paper_trading / live
- LOG_LEVEL の有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL
- DuckDB の初期化時に親ディレクトリが存在しない場合は自動作成されます。
- 監査ログは UTC タイムゾーンで timestamp を保存するよう初期化で設定されます。

---

必要であれば README に次の項目を追加できます:
- 実運用時のデーモン化方法（systemd / cron / Airflow 例）
- ローカル開発用の .env.example
- 実行時のログ設定例（logging 設定、Sentry/Slack 通知統合）
- strategy / execution 層の利用例・API仕様

追記希望があれば具体的に教えてください。
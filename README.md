# KabuSys

日本株自動売買システムのライブラリ群（データ取得・ETL・品質管理・監査ログ等）。

このリポジトリは、J-Quants 等の外部データソースから日本株のマーケットデータ・財務データ・ニュースを取得し、DuckDB に三層（Raw / Processed / Feature）スキーマで保存、品質チェックや監査ログを提供するためのコンポーネント群を含みます。実際の発注／約定処理や戦略実行ロジックは別モジュールで実装可能なよう拡張点を用意しています。

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時の fetched_at により Look-ahead バイアスを防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分更新（最終取得日に基づく自動算出）、バックフィル機構
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
- ニュース収集（RSS）
  - RSS フィードの取得、URL 正規化（utm 等の除去）、SHA-256 による記事ID生成
  - SSRF・XML Bom 対策（スキーム検証、defusedxml、ホストのプライベートアドレス検査）
  - DuckDB への冪等保存（INSERT ... RETURNING、チャンク処理）
  - 記事と銘柄コードの紐付け（記事内の4桁銘柄コード抽出）
- DuckDB スキーマ定義
  - Raw / Processed / Feature / Execution / Audit 向けのテーブル群とインデックス
  - スキーマ初期化ユーティリティ（init_schema、init_audit_schema）
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、主キー重複、日付不整合（未来日付／非営業日データ）検出
  - 問題を QualityIssue として収集（Fail-Fast ではなく全件収集）
- 監査ログ（audit）
  - signal → order_request → execution の階層でトレーサビリティを保存
  - 発注の冪等キー（order_request_id）や broker 側の約定ID を考慮した設計

---

## 前提 / 要件

- Python 3.10 以上（PEP 604 の型記法（|）を使用）
- 必要なパッケージ（主なもの）
  - duckdb
  - defusedxml
  - （その他 標準ライブラリのみで実装された部分多数）

pip 環境にインストールする際は requirements や pyproject.toml を参照してください（本 README では最低限の依存を記載しています）。

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動（pyproject.toml がある想定）

   ```
   git clone <リポジトリURL>
   cd <project-root>
   ```

2. 仮想環境を作成・有効化（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. パッケージを開発モードでインストール（pyproject.toml / setup がある想定）

   ```
   pip install -e .
   ```

4. 必要なライブラリを個別にインストール（例）

   ```
   pip install duckdb defusedxml
   ```

5. 環境変数の設定
   - プロジェクトルートの `.env`（および `.env.local`）に設定を書くと、自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須のもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN : 通知用 Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID : 通知先 Slack チャネル ID（必須）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : SQLite（monitoring 用）ファイルパス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## データベース初期化

DuckDB スキーマを作成するには Python から次のように呼び出します。

- メモリ DB（テスト用）:

  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```

- ファイル DB:

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  ```

監査ログ（audit）テーブルを追加するには:

```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema で初期化済みの接続
init_audit_schema(conn)
```

---

## 使い方（コード例）

- 日次 ETL 実行（株価 / 財務 / カレンダー取得 + 品質チェック）:

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 単独で株価 ETL を実行:

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema(settings.duckdb_path)
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- ニュース収集ジョブ:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(settings.duckdb_path)
# known_codes は有効銘柄コードセット。ない場合は紐付けをスキップ
results = run_news_collection(conn, sources=None, known_codes=set(["7203", "6758"]))
print(results)  # {source_name: 新規保存件数}
```

- カレンダー夜間バッチ更新:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

- 品質チェック単体実行:

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
issues = run_all_checks(conn, target_date=None, reference_date=date.today())
for i in issues:
    print(i)
```

注意:
- J-Quants API 呼び出しはレート制御とリトライを実装していますが、実運用時は API 利用制限・認可を確認してください。
- run_daily_etl 等は内部で例外を捕捉して処理を続行します。戻り値（ETLResult）の errors / quality_issues を確認して運用判断してください。

---

## 自動 .env 読み込みの挙動

- 起点は本モジュールのファイル位置から親ディレクトリを上へ探索し、.git または pyproject.toml を検出した場所をプロジェクトルートと見なします。
- 読み込み順序（優先度）:
  1. OS 環境変数
  2. .env.local（既存の OS 環境変数を上書きしないが .env を上書きする）
  3. .env（既存 OS 環境変数を変更しない）
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートに pyproject.toml / .git 等がある前提、以下は src/kabusys 以下）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - calendar_management.py
      - schema.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
      (戦略関連モジュールを配置)
    - execution/
      - __init__.py
      (発注・ブローカー連携モジュールを配置)
    - monitoring/
      - __init__.py
      (監視・メトリクス関連)

---

## 運用上の注意 / 設計上のポイント

- J-Quants のレート制限（120 req/min）遵守のため、クライアント側にスロットリングを実装しています。大量データ一括取得時は注意してください。
- ニュース収集は外部フィードを解析するため、XML の脆弱性（XML bomb）や SSRF に対する防御を実装しています。外部 URL の扱いには常に注意してください。
- DuckDB を永続ストレージとして利用します。大規模運用ではディスク容量やバックアップ方針を検討してください。
- 監査ログは削除しないことを前提とした設計です（FK は ON DELETE RESTRICT）。長期保存の方針を立ててください。

---

## 貢献・拡張

- strategy, execution, monitoring パッケージは拡張ポイントです。ここに実際の戦略ロジックやブローカ接続、監視アラート処理を実装してください。
- テスト時は env 自動ロードを無効化し、明示的にテスト用の環境変数をセットすることを推奨します。

---

この README はコードベースの主要な機能と使い方をまとめた概要です。詳細は各モジュール（特に kabusys/data/*.py と kabusys/config.py）内の docstring を参照してください。必要であれば、実行スクリプトやデプロイ手順のサンプルも追加します。
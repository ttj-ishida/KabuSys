# KabuSys

KabuSys は日本株向けの自動売買プラットフォームの骨組みを提供するライブラリ群です。  
データ取得（J-Quants）、ニュース収集（RSS）、DuckDB を用いたデータスキーマ、ETL パイプライン、データ品質チェック、監査ログ（取引トレーサビリティ）などを備えています。

> 現時点では strategy / execution / monitoring のパッケージが用意されていますが、実装はプロジェクトに合わせて追加する想定です。

---

## 主な特徴（機能一覧）

- 環境変数読み込み / 設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須設定チェック（未設定時は ValueError）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）を遵守するスロットリング実装
  - リトライ（指数バックオフ、最大3回）、401 受信時は自動トークンリフレッシュ
  - 取得日時（fetched_at）を UTC で付与
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード取得・パース（defusedxml を使用）
  - URL 正規化とトラッキングパラメータ除去、記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証 / プライベートIPブロック / リダイレクト検査）
  - レスポンスサイズ制限（最大 10MB、gzip 解凍後も検査）
  - DuckDB に対するバルク挿入、INSERT ... RETURNING を使用して実際に挿入された件数を取得
  - 銘柄コード抽出（4桁数字）と news_symbols への紐付け

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層を含むテーブル定義（冪等に作成）
  - インデックス定義、監査ログ用スキーマ初期化 API あり

- ETL パイプライン (`kabusys.data.pipeline`)
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新、バックフィル（デフォルト 3 日）、カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・スパイク・重複・日付不整合）の実行フロー

- データ品質チェック (`kabusys.data.quality`)
  - QualityIssue を返す形でチェック結果を集約（エラー/警告の区別）
  - ETL の停止は呼び出し側で判断（Fail-Fast ではない）

- 監査ログ（トレーサビリティ） (`kabusys.data.audit`)
  - signal_events / order_requests / executions テーブルなどを定義
  - UUID ベースのトレーサビリティ階層、UTC タイムスタンプ

---

## 前提条件

- Python 3.10+
  - 型注釈（例: `Path | None`）を使用しているため 3.10 以上を推奨します。
- 必要なパッケージ（最小セット）
  - duckdb
  - defusedxml
  - （標準ライブラリのみで動く部分も多いですが、実運用ではロギング、HTTP クライアント拡張等を追加で導入することがあります）

インストール例:
```
python -m pip install duckdb defusedxml
# またはプロジェクトパッケージを editable インストールする場合
python -m pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## 環境変数 / 設定

自動ロード順序: OS 環境変数 > .env.local > .env  
プロジェクトルートは .git または pyproject.toml を基準に検出します。  
自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

主要な必須環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

その他（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で無効化)

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定値はコードから `from kabusys.config import settings` を使って参照できます（例: `settings.jquants_refresh_token`）。

---

## セットアップ手順（簡易）

1. リポジトリをチェックアウト
2. Python 環境を準備（venv 推奨）
3. 依存パッケージをインストール
   ```
   python -m pip install -r requirements.txt
   # または最低限
   python -m pip install duckdb defusedxml
   ```
4. .env（または環境変数）を用意
5. DuckDB スキーマを初期化
   - プログラム的に初期化する例（Python REPL やスクリプト内で）:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ（audit）スキーマを追加する:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方（代表的な例）

- J-Quants のトークン取得
  ```python
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を使って取得
  ```

- DuckDB スキーマ初期化（再掲）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")  # 事前に init_schema を実行済みのこと
  result = run_daily_etl(conn, target_date=date.today())  # ETLResult を返す
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS を取得して保存）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes を与えると記事→銘柄の紐付けも行う
  known_codes = {"7203", "6758", "9432"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- raw データ保存（jquants_client の関数を直接利用）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)
  ```

---

## ディレクトリ構成

以下はソースツリー（主要ファイル）の抜粋です:

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（取得・保存）
    - news_collector.py           # RSS ニュース収集・前処理・保存
    - schema.py                   # DuckDB スキーマ定義・初期化
    - pipeline.py                 # ETL パイプライン（差分取得・品質チェック）
    - audit.py                    # 監査ログ（トレーサビリティ）
    - quality.py                  # データ品質チェック
  - strategy/
    - __init__.py                  # 戦略関連の入れ物（実装はプロジェクト側で）
  - execution/
    - __init__.py                  # 発注関連の入れ物（実装はプロジェクト側で）
  - monitoring/
    - __init__.py                  # 監視機能（実装はプロジェクト側で）

---

## 注意事項 / 設計上のポイント

- J-Quants API
  - レート制限 120 req/min をモジュール内でスロットリングして守ります。
  - 408/429/5xx 系はリトライ対象（指数バックオフ）、401 は自動的にトークンリフレッシュして1回リトライします。

- ニュース収集
  - SSRF 対策（スキーム検証・ホストがプライベートかのチェック・リダイレクト検査）を実装しています。
  - レスポンスサイズ上限や gzip 解凍後のチェックにより DoS 対策を行っています。

- DuckDB
  - スキーマ初期化関数は冪等（既存テーブルはスキップ）です。初回は init_schema() を呼んでください。
  - INSERT の多くは ON CONFLICT を用いて冪等性を保証しています。

- テスト
  - config モジュールは KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env 読み込みを無効化できます（テスト環境で利用）。

---

## 拡張のヒント

- strategy / execution 層に独自の戦略ロジック・発注ドライバを実装して、signal_queue / order_requests を通じたワークフローを構築してください。
- 監視・アラート（Slack 通知など）は monitoring パッケージに実装し、ETLResult や QualityIssue を使って通知するのが自然です。
- 実運用での並列化やスケジューリングは外部ジョブランナー（cron, Airflow, Prefect 等）やメッセージキューを組み合わせて実装してください。

---

もし README に追加したいサンプルや、CI / テスト手順、あるいは strategy や execution の具体的なテンプレートが必要であれば教えてください。必要に応じて README を拡張してテンプレートやサンプルコードを追加します。
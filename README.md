# KabuSys

日本株向けの自動売買・データ基盤ライブラリ集です。  
J-Quants API からの市場データ取得、DuckDB ベースのスキーマ定義・初期化、ETL パイプライン、ニュース収集、カレンダー管理、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

---

## 主な特長

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダー等を取得
  - API レート制御（120 req/min）・リトライ（指数バックオフ）・401 の自動トークンリフレッシュ対応
  - データ取得時に fetched_at を UTC で記録（Look-ahead バイアス対策）
- DuckDB ベースのデータスキーマ（Raw / Processed / Feature / Execution 層）
  - 冪等な保存（ON CONFLICT/DO UPDATE）を行うユーティリティを用意
- ETL パイプライン
  - 差分更新・バックフィル（後出し修正吸収）・品質チェック（欠損・スパイク・重複・日付不整合）
  - run_daily_etl による日次一括処理
- ニュース収集モジュール
  - RSS からの記事取得、前処理、記事ID生成（URL 正規化 + SHA-256）、DuckDB への冪等保存
  - SSRF 対策、defusedxml による XML 攻撃対策、レスポンスサイズ制限（メモリ DoS 対策）
- マーケットカレンダー管理
  - 営業日判定・前後営業日探索・夜間カレンダー更新ジョブ
- 監査ログ（Audit）
  - シグナル→発注要求→約定の階層的トレーサビリティ用テーブル群、UTC タイムスタンプ管理

---

## 必要条件 / 依存ライブラリ

- Python 3.10 以上（型注釈で `X | Y` を使用）
- 以下の主要依存（例）
  - duckdb
  - defusedxml

推奨: 仮想環境を使用してください。

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 必要に応じて他のパッケージを追加
```

（プロジェクト配布で requirements.txt を用意していればそれを利用してください。）

---

## 環境変数（.env）

自動読み込み: パッケージはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）にある `.env` / `.env.local` を自動で読み込みます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token の元になります。
- KABU_API_PASSWORD (必須)
  - kabuステーション等の API 用パスワード
- KABU_API_BASE_URL (任意)
  - デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)
  - Slack 通知等に使用する Bot トークン
- SLACK_CHANNEL_ID (必須)
  - Slack 通知先チャンネル ID
- DUCKDB_PATH (任意)
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)
  - デフォルト: data/monitoring.db
- KABUSYS_ENV (任意)
  - 有効値: development, paper_trading, live
  - デフォルト: development
- LOG_LEVEL (任意)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - デフォルト: INFO

例（`.env`）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   # 他の必要パッケージを追加
   ```

3. 環境変数を設定（.env を作成）
   - 上記の `.env` 例を参考に必要な値を設定

4. DuckDB スキーマ初期化（Python から）
   ```python
   from kabusys.data import schema

   # ファイル DB を初期化（親ディレクトリがなければ自動作成）
   conn = schema.init_schema("data/kabusys.duckdb")
   # 監査ログテーブルを追加する場合
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   ```

   - 監査ログ専用 DB を別ファイルに作る場合:
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要な API と実行例）

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import pipeline, schema

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 個別 ETL ジョブ
  - 株価差分ETL:
    ```python
    from kabusys.data import pipeline, schema
    conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
    fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
    ```
  - カレンダー更新ジョブ（バッチ）
    ```python
    from kabusys.data import calendar_management, schema
    conn = schema.get_connection("data/kabusys.duckdb")
    saved = calendar_management.calendar_update_job(conn)
    ```

- ニュース収集ジョブ
  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # sources を渡さなければ DEFAULT_RSS_SOURCES を使用
  results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
  print(results)  # {source_name: 新規保存件数}
  ```

- J-Quants から直接データ取得（テストや小規模取得）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.config import settings

  id_token = jq.get_id_token()  # settings.jquants_refresh_token を用いる
  records = jq.fetch_daily_quotes(id_token=id_token, code="7203", date_from=date(2024,1,1), date_to=date(2024,3,1))
  ```

- 自動環境読み込みを無効にする（テスト用）
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 主なモジュールとディレクトリ構成

（プロジェクトルートに `src/kabusys` がある想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義、自動 .env ロードロジック、必須変数チェック
  - data/
    - __init__.py
    - schema.py
      - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution）
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - pipeline.py
      - ETL パイプライン（差分更新・バックフィル・品質チェック）
    - news_collector.py
      - RSS 取得、前処理、ID 生成、保存、銘柄抽出（SSRF/XML/サイズ対策あり）
    - calendar_management.py
      - JPX カレンダー管理、営業日判定、夜間更新ジョブ
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）初期化ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
    - （戦略実装用のプレースホルダ）
  - execution/
    - __init__.py
    - （発注実装用のプレースホルダ）
  - monitoring/
    - __init__.py
    - （監視・メトリクス用プレースホルダ）

---

## 設計上の注意点 / セキュリティ

- J-Quants API:
  - レート制限（120 req/min）を守るため固定間隔スロットリングを実装
  - リトライ（408/429/5xx）および 401 のトークン自動リフレッシュを実装
- ニュース収集:
  - defusedxml を利用して XML 攻撃を防止
  - リダイレクト先のスキーム検証・プライベート IP（SSRF）チェックを実装
  - レスポンスサイズ、gzip 解凍後のサイズを制限してメモリ DoS を防止
- DB 保存:
  - 冪等性を考慮した INSERT（ON CONFLICT）を利用
  - 大量挿入時はチャンク処理・トランザクション単位でのコミットを行い整合性を担保

---

## よくある作業

- スキーマを初期化して ETL を定期実行（cron / systemd timer 等）
- ニュース収集を定期実行して raw_news を蓄積し、記事と銘柄の紐付けを行う
- 監査ログを別 DB に切り出して運用（監査データは削除しない前提）

---

README に記載のない詳細は各モジュールの docstring を参照してください（src/kabusys/** 内に詳細な説明があります）。質問や補足があれば教えてください。
# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
J-Quants や RSS を用いたデータ収集、DuckDB ベースのスキーマ管理、ETL パイプライン、ニュース収集・銘柄紐付け、品質チェック、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです：

- J-Quants API から株価 / 財務 / 市場カレンダーを取得して DuckDB に格納する ETL パイプライン
- RSS フィードからニュース記事を収集し正規化して DB に保存、銘柄コードと紐付け
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）用スキーマ
- 市場カレンダー管理（営業日判定等）

設計上の特徴：
- API レート制御とリトライ（J-Quants クライアント）
- 冪等な DB 保存（INSERT ... ON CONFLICT）
- SSRF / XML Bomb / large response 対策を考慮したニュース収集
- DuckDB を用いたローカルデータベース（軽量で高速）

---

## 機能一覧

- データ取得
  - 株価日足（OHLCV）取得・ページネーション対応
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
- データ保存
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution / audit 等のテーブル）
  - 冪等保存関数（raw_prices, raw_financials, market_calendar, raw_news, news_symbols 等）
- ETL
  - 差分更新（最終取得日からの差分を自動算出）
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
- ニュース収集
  - RSS フィード取得、前処理（URL除去・空白正規化）、記事ID生成（正規化URL の SHA-256）
  - SSRF / 圧縮応答 / XML パース例外対策
  - raw_news への保存・news_symbols への銘柄紐付け
- 品質チェック
  - 欠損データ検出、スパイク検出、重複検出、日付整合性チェック
- マーケットカレンダー管理
  - 営業日判定／次・前営業日の取得／期間内営業日列挙
  - 夜間バッチでのカレンダー更新ジョブ
- 監査ログ（audit）
  - signal_events / order_requests / executions の定義と初期化

---

## 必要条件（依存関係）

- Python 3.10 以上（コード中の型ヒント等の構文に依存）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, json, logging, datetime 等）

依存パッケージはプロジェクトに requirements.txt があればそちらを使用してください。最低限のインストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数（設定）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須の環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード
- SLACK_BOT_TOKEN       : Slack 通知用トークン
- SLACK_CHANNEL_ID      : Slack チャネル ID

任意／デフォルト:
- KABUSYS_ENV : `development` | `paper_trading` | `live` （デフォルト: development）
- LOG_LEVEL : `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL` （デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 dotenv 読み込みを無効化（値は任意）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（モニタリング DB）パス（デフォルト: data/monitoring.db）
- KABUS_API_BASE_URL : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）

.env の読み込みルール:
- OS 環境変数が最優先
- `.env.local` は `.env` の上書き
- `.env`/.env.local が存在しない場合はスキップ（パッケージ配布後の挙動に配慮）

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境作成と依存インストール

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # その他必要パッケージがあれば追加
   ```

3. 環境変数設定
   - プロジェクトルートに `.env` を作成して必須変数を設定するか、OS 環境変数で設定してください。
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. DuckDB スキーマ初期化（最初に一度）
   - Python REPL やスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # 監査ログテーブルを別途初期化する場合:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     conn.close()
     ```

---

## 使い方（主要な操作例）

以下は Python から各機能を利用する例です。

- J-Quants の ID トークン取得:
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を利用して POST で取得
  ```

- 日次 ETL 実行:
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定することも可能
  print(result.to_dict())
  conn.close()
  ```

- RSS ニュース収集（既知コードセットを使った銘柄抽出）:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  result = run_news_collection(conn, known_codes=known_codes)
  print(result)  # {source_name: 新規保存数}
  conn.close()
  ```

- スキーマの部分初期化（監査ログ専用）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  conn.close()
  ```

- 品質チェックを個別に実行:
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  conn.close()
  ```

ログレベルや環境は環境変数（LOG_LEVEL / KABUSYS_ENV）で制御できます。

---

## 便利なポイント / 実装上の注意

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探して行います。CI やテストで自動読み込みを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants クライアントは 120 req/min のレート制御、リトライ、401 の自動リフレッシュを実装しています。
- ニュース収集は安全性（SSRF 防止、XML パースの安全化、受信サイズ制限）に配慮しています。
- DuckDB に対する INSERT は可能な限り冪等（ON CONFLICT）で設計されています。
- 全ての監査ログ TIMESTAMP は UTC を前提としています（audit.init_audit_schema は `SET TimeZone='UTC'` を実行します）。

---

## ディレクトリ構成

主要ファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                    (設定 / 環境変数読み込み)
  - data/
    - __init__.py
    - jquants_client.py          (J-Quants API クライアント・取得/保存)
    - news_collector.py         (RSS ニュース収集 / 保存 / 銘柄抽出)
    - pipeline.py               (ETL パイプライン：prices / financials / calendar / run_daily_etl)
    - schema.py                 (DuckDB スキーマ定義と初期化)
    - calendar_management.py    (営業日判定、カレンダー更新ジョブ)
    - audit.py                  (監査ログスキーマ / 初期化)
    - quality.py                (データ品質チェック)
  - strategy/
    - __init__.py               (戦略層用エントリプレースホルダ)
  - execution/
    - __init__.py               (実行層用エントリプレースホルダ)
  - monitoring/
    - __init__.py               (モニタリング層用エントリプレースホルダ)

この README はライブラリの上位説明です。各モジュール内には詳細な docstring があり、関数ごとの使い方・引数・返り値・例外などが記載されています。実運用のためには、環境変数の適切な管理（秘密情報の取り扱い）、バックアップ、監視・アラートの整備を行ってください。

---

開発・運用に関する質問や、具体的な利用シナリオ（バックフィル調整、品質チェックポリシー、Slack 通知統合など）があれば、目的に合わせた README 拡張や使用例を作成します。
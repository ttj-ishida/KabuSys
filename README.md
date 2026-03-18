# KabuSys

KabuSys は日本株の自動売買・データ基盤を想定した Python ライブラリ群です。  
DuckDB をデータレイクとして用い、J-Quants API からの差分取得（株価・財務・マーケットカレンダー）、RSS ニュース収集、品質チェック、特徴量計算、監査ログ等を含むデータプラットフォーム／リサーチ／発注基盤の基礎的な機能群を提供します。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- データ取得・保存
  - J-Quants API クライアント（fetch / save の冪等処理、レート制御、リトライ、トークン自動リフレッシュ）
  - 株価日足・財務データ・マーケットカレンダー取得（ページネーション対応）
  - raw_* テーブルへの冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）

- ETL・データパイプライン
  - 差分更新（最終取得日ベースの差分取得 + バックフィル）
  - 日次 ETL エントリポイント（run_daily_etl）

- データ品質管理
  - 欠損・重複・スパイク（前日比閾値）・日付不整合チェック（quality モジュール）
  - 品質チェックをまとめて実行（run_all_checks）

- ニュース収集
  - RSS フィード収集（SSRF 対策、gzip/サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への保存（冪等、チャンク挿入、銘柄抽出）

- スキーマ管理（DuckDB）
  - init_schema() による DuckDB のテーブル・インデックス一括初期化
  - 監査ログ用スキーマ（init_audit_schema / init_audit_db）

- リサーチ／特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）

- マーケットカレンダー管理
  - 営業日判定 / 前後営業日取得 / 期間の営業日列挙 / カレンダー更新ジョブ

- 監査・トレーサビリティ
  - signal / order_request / execution の監査テーブル群（監査ログ初期化関数を提供）

---

## 必要な環境

- Python 3.10 以上（typing の構文に依存）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

requirements.txt がある場合はそちらを参照してください。最小限の依存は上記の通りで、HTTP は標準ライブラリ urllib を使用しています。

---

## セットアップ

1. リポジトリをクローン／ダウンロード

   git clone を想定:
   - git clone <repository-url>
   - cd <repository>

2. 仮想環境を作成・有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. パッケージをインストール

   開発中にローカルで使う場合:
   - pip install -e .

   または必要な依存だけを入れる場合:
   - pip install duckdb defusedxml

4. 環境変数の設定

   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと、自動的にロードされます（モジュール内で自動読み込みが行われます）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（Settings クラスで参照）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabu ステーション API パスワード
   - SLACK_BOT_TOKEN : Slack 通知用 Bot Token
   - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 初期化（DuckDB スキーマ）

DuckDB ファイルを作り、テーブル群を初期化します。以下は Python からの例です。

例: データベースを初期化して接続を取得する
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Settings.duckdb_path で取得可能（Path オブジェクト）
conn = init_schema(settings.duckdb_path)
```

監査ログ専用 DB を初期化する場合:
```
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

注意: init_schema はテーブル作成を冪等に行います（既にあるテーブルはスキップ）。

---

## 使い方：主要ユースケース例

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")  # または get_connection()
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブの実行
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に用意した有効銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

- J-Quants から日足を取得して保存（テスト／ユーティリティ）
```
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print("saved", saved)
```

- リサーチ用ファクター計算（例: モメンタム）
```
from datetime import date
from kabusys.research import calc_momentum
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2024,1,31))
# factors は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
```

- Z スコア正規化
```
from kabusys.data.stats import zscore_normalize

normalized = zscore_normalize(factors, ["mom_1m", "ma200_dev"])
```

---

## 設定 / 環境変数の説明（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用 Slack 設定（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development"|"paper_trading"|"live")（デフォルト: development）
- LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/...）  
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効にする（テスト時に便利）

Settings API の例:
```
from kabusys.config import settings
print(settings.duckdb_path, settings.is_dev, settings.log_level)
```

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      （環境変数 / 設定管理）
  - data/
    - __init__.py
    - jquants_client.py            （J-Quants API クライアント）
    - news_collector.py            （RSS ニュース収集）
    - schema.py                    （DuckDB スキーマ定義・init）
    - pipeline.py                  （ETL パイプライン、run_daily_etl 等）
    - etl.py                       （公開インターフェース）
    - quality.py                   （データ品質チェック）
    - stats.py                     （統計ユーティリティ / zscore）
    - calendar_management.py       （マーケットカレンダー管理）
    - audit.py                      （監査ログスキーマ）
    - features.py                   （特徴量ユーティリティの再エクスポート）
  - research/
    - __init__.py
    - feature_exploration.py       （将来リターン・IC・summary 等）
    - factor_research.py           （momentum / volatility / value 等）
  - strategy/                      （戦略関連: 空パッケージ）
  - execution/                     （発注実装: 空パッケージ）
  - monitoring/                    （監視用: 空パッケージ）

（上記はこのコードベースに含まれる主なモジュールです。詳細はソースの docstring を参照してください）

---

## 注意点 / 設計上のポイント

- DuckDB を中心に設計されており、raw / processed / feature / execution 層でテーブルを分離しています。
- J-Quants クライアントはレートリミット（120 req/min）、リトライ、401 のトークン自動リフレッシュ、ページネーション対応を備えています。
- ニュース収集は SSRF 対策、gzip サイズチェック、XML パースの安全化（defusedxml）などセキュリティと DoS 対策を盛り込んでいます。
- データ品質チェック（quality モジュール）は Fail-Fast ではなく全件検出して呼び出し元で判断できる設計です。
- 本コードは「リサーチ / データ基盤 / 発注基盤」の基礎実装群を提供しますが、実際の発注（ブローカー連携）や本番運用時の詳細（リスク制御、接続設定、永続的な監視）は別途実装が必要です。

---

## 貢献・開発

- テストや CI を追加してカバレッジを高めてください。
- 外部 API キーはリポジトリにコミットしないでください。`.env.example` を用意して README に記載することを推奨します。
- Issue / PR の際は既存のデータモデルや冪等性の設計意図を尊重してください（ON CONFLICT の利用、UTC タイムスタンプ、監査ログ不削除方針など）。

---

もし README に追記してほしい具体的なコマンド例（systemd ジョブ、Airflow / cron 連携例、Docker 化手順など）があれば教えてください。必要に応じてサンプル .env.example も作成します。
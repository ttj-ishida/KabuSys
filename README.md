# KabuSys

日本株向けの自動売買プラットフォーム基盤（プロトタイプ）です。  
J-Quants / kabuステーション等の外部データソースや、DuckDB を用いた局所データベース、ニュース収集、ETL・品質チェック、監査ログなどを含むデータ基盤と実行層の骨組みを提供します。

バージョン: 0.1.0

---

## 主な特徴（概要）

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）とリトライ、401 時のトークン自動リフレッシュ処理
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB へ冪等的に保存（ON CONFLICT / DO UPDATE）
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得 + バックフィル）
  - 市場カレンダー先読み、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL 実行エントリーポイント
- ニュース収集
  - RSS フィードから記事を収集・正規化して DuckDB に保存
  - URL 正規化・トラッキングパラメータ除去、SSRF 対策、Gzip サイズチェック
  - 銘柄コード抽出と記事⇔銘柄の紐付け
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日リスト取得、夜間バッチ更新ジョブ
- 監査ログ（Audit）
  - シグナル→発注→約定までのトレーサビリティ用スキーマ（UUID 冠連鎖）
  - order_request_id による冪等、UTC タイムゾーン固定
- DuckDB ベースのスキーマ定義（Raw / Processed / Feature / Execution / Audit）

---

## 機能一覧（もう少し具体的に）

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（総合 ETL）
- data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
- data.schema
  - init_schema, get_connection（DuckDB スキーマ初期化・接続）
- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- data.audit
  - init_audit_schema, init_audit_db（監査ログスキーマ初期化）
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- 環境・設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート検出）、必須設定取得ラッパー（Settings）

---

## 要件

- Python 3.9+（型注釈で | を使用しているため 3.10 以上を推奨する場合あり）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, json, logging, datetime 等）

（プロジェクトの pyproject.toml / requirements.txt を用意している場合はそちらを参照してください）

---

## インストール

1. リポジトリをクローンしてローカルへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   例（pip を使う場合）:
   ```
   pip install duckdb defusedxml
   # またはプロジェクトに requirements があればそれを使用
   # pip install -r requirements.txt
   ```

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

---

## 環境変数 / 設定

自動でプロジェクトルート（.git または pyproject.toml）を探索し、.env / .env.local を読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

その他オプション:
- KABUSYS_ENV: environment（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）。デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）

設定取得例（コード内での利用）:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
db_path = settings.duckdb_path
```

注意: Settings の必須キーが未設定の場合 ValueError が発生します。

---

## 初期セットアップ（DB スキーマ初期化例）

DuckDB スキーマを初期化して接続を取得します。

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# ":memory:" を指定すればインメモリ DB を使用可能
```

監査ログ専用 DB の初期化:
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
# または既存 conn に監査スキーマを追加
# audit.init_audit_schema(conn)
```

---

## 使い方（代表的な操作例）

1) 日次 ETL の実行（市場カレンダー取得 → 株価・財務データ取得 → 品質チェック）
```python
from kabusys.data import schema, pipeline
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース収集ジョブの実行（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data import schema, news_collector

conn = schema.init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に用意した銘柄コードセット
res = news_collector.run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数, ...}
```

3) カレンダー夜間バッチ更新
```python
from kabusys.data import schema, calendar_management

conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

4) J-Quants トークン取得 / API 呼び出し（テスト用）
```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## ログ / 環境モード

- KABUSYS_ENV により振る舞いやリスク（paper_trading / live）を区別できます。settings.is_live / is_paper / is_dev を参照可能。
- LOG_LEVEL を設定してログ出力量を調整します。

---

## セキュリティと設計上の注意点

- J-Quants クライアントは ID トークンを自動リフレッシュし、ページネーション間でトークンキャッシュを共有します。
- ニュース収集では以下の対策を講じています:
  - defusedxml を用いた XML パース（XML Bomb 対策）
  - HTTP リダイレクト先のスキーム・ホストの検証（SSRF 対策）
  - レスポンスサイズの上限（MAX_RESPONSE_BYTES）を設け、Gzip 展開後もチェック
  - 記事 ID は URL 正規化後の SHA-256（先頭 32 文字）で冪等性を担保
- DuckDB への保存は可能な限り冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を考慮しています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                       -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - schema.py                      -- DuckDB スキーマ定義 / init_schema
      - jquants_client.py              -- J-Quants API クライアント
      - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
      - news_collector.py              -- RSS 収集・保存・紐付け
      - calendar_management.py         -- マーケットカレンダー管理
      - quality.py                     -- データ品質チェック
      - audit.py                       -- 監査ログスキーマ初期化
      - pipeline.py
    - strategy/                         -- 戦略層（空のパッケージ）
    - execution/                        -- 実行層（空のパッケージ）
    - monitoring/                       -- 監視関連（空のパッケージ）

---

## 開発 / 貢献

- 小さなユーティリティ単位でのモジュール設計のため、ユニットテストが書きやすくなっています（外部ネットワークはモック可能）。
- .env.example をプロジェクトルートに置いて、必要な環境変数を明示すると良いです。
- 外部 API の呼び出しやネットワーク処理はリトライ・レート制御・時間依存処理があるため、CI ではモックを推奨します。

---

README に含めるべき追加情報（例）
- 実運用用の注意（リアルマネー運用時のリスク管理）
- テストの実行方法、CI 設定例
- ライセンス情報

必要であれば上記を含めた補足 README を作成します。どの部分を詳細化しますか？
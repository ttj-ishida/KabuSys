# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
J-Quants API や RSS フィードから市場データ・ニュースを収集し、DuckDB に蓄積して ETL→品質チェック→戦略/実行へつなぐための基盤モジュール群を提供します。

バージョン: 0.1.0

---

## 概要

このプロジェクトは、次のような機能を持つ日本株自動売買向けデータ基盤／ランタイムの一部を実装しています。

- J-Quants API を用いた株価（OHLCV）、財務データ、JPX カレンダーの取得
- RSS からのニュース収集と銘柄抽出
- DuckDB を用いたデータスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 市場カレンダー管理（営業日判定・前後営業日検索）
- 監査ログ（シグナル→オーダー→約定のトレーサビリティ）用スキーマ
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）
- 環境変数経由の設定管理（.env 自動読み込みを含む）

設計上の注意点として、API レート制御、リトライ、Look-ahead バイアス防止（fetched_at 記録）、冪等性（ON CONFLICT）などを重視しています。

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数の取得（.env/.env.local 自動読込、必須キーの検査）
- kabusys.data.jquants_client
  - J-Quants API クライアント（認証・レートリミット・リトライ・データ取得・DuckDB 保存関数）
- kabusys.data.news_collector
  - RSS フィード取得、XML パース（defusedxml）、記事正規化、DuckDB への保存、銘柄抽出（4桁コード）
- kabusys.data.schema
  - DuckDB のスキーマ定義・初期化（raw/processed/feature/execution 層）、インデックス作成
- kabusys.data.pipeline
  - 差分 ETL（prices/financials/market_calendar）の実装、run_daily_etl（品質チェックを含む）
- kabusys.data.calendar_management
  - market_calendar を用いた営業日判定、next/prev_trading_day、夜間更新ジョブ
- kabusys.data.audit
  - 監査用テーブル（signal_events / order_requests / executions）と初期化関数
- kabusys.data.quality
  - データ品質チェック群（欠損・重複・スパイク・日付不整合）
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - 戦略・発注・監視のためのパッケージ基盤（本コード内では空パッケージとして定義）

---

## 前提 / 必要環境

- Python 3.10 以上（PEP 604 の型記法や型ヒント等を使用）
- 必要なパッケージ（例）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリを取得
   - Git からクローンするか、ソースを配置します。

2. Python 仮想環境（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャネル ID
   - 任意（デフォルトあり）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルトはローカル）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な操作例）

以下は Python REPL やスクリプトからライブラリを利用する典型的な例です。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

- 監査ログスキーマを追加（既存接続へ）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema で得た接続
```

- 日次 ETL 実行（株価 / 財務 / カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄コードの集合（例: {"7203","6758",...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(res)  # {source_name: 新規保存件数}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved", saved)
```

- J-Quants API の直接利用（ID トークン取得 / データ取得）
```python
from kabusys.data import jquants_client as jq
token = jq.get_id_token()  # settings.jquants_refresh_token を使って POST で取得
prices = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 設定値の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

## 環境変数の自動ロードについて

- パッケージはプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動ロードします。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - .env.local は .env の上書き（override=True）
- 自動ロードを無効化するには環境変数を設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数が未設定の場合、settings の対応プロパティを参照すると ValueError が発生します（例: settings.jquants_refresh_token）。

---

## ロギング

- 各モジュールは標準 logging を使用します。実行環境側でハンドラ・レベルを設定して下さい。settings.log_level を利用してログレベルを制御できます。

---

## ディレクトリ構成

（プロジェクトルートの `src/kabusys` を中心に）主要ファイル:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py         -- J-Quants API クライアント（取得・保存）
      - news_collector.py         -- RSS ニュース収集・保存・銘柄抽出
      - schema.py                 -- DuckDB スキーマ定義 & init_schema / get_connection
      - pipeline.py               -- ETL パイプライン（差分取得・品質チェック）
      - calendar_management.py    -- 市場カレンダーの管理・検索・更新ジョブ
      - audit.py                  -- 監査ログ（signal/order/execution）スキーマ
      - quality.py                -- データ品質チェック群
    - strategy/
      - __init__.py               -- 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py               -- 発注・約定管理（拡張ポイント）
    - monitoring/
      - __init__.py               -- 監視機能（拡張ポイント）

---

## 注意点 / 設計上のポイント

- API 呼び出しに対してはレート制御（120 req/min）とリトライ（指数バックオフ）を実装。401 はトークン自動リフレッシュを試みます。
- データ保存は冪等性を担保（DuckDB 上の INSERT ... ON CONFLICT DO UPDATE / DO NOTHING を利用）。
- ニュース収集では SSRF 対策（スキーム検証、プライベートアドレス拒否）、XML パース安全化（defusedxml）、受信サイズ制限が実装されています。
- 市場カレンダーが未取得の場合、土日ベースのフォールバックを行いますが、DB に登録があればそれを優先します。
- 監査ログはトレーサビリティを重視し、削除を想定しない運用（FK は ON DELETE RESTRICT 等）です。

---

## 今後の拡張案（例）

- kabuステーション API との実際の発注実装（execution パッケージ）
- 戦略のサンプル実装とバックテストフレームワーク（strategy パッケージ）
- モニタリング / アラート（monitoring）
- CLI や cron/airflow 用のラッパー実装

---

不明点や README に追記したい使用例・運用手順があれば教えてください。README を用途（開発者向け / 運用向け）に合わせて調整します。
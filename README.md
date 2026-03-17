# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。J-Quants API や RSS フィード等からデータを取得・保存し、ETL・品質チェック・監査ログ・マーケットカレンダー管理などの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的に設計された Python パッケージです。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する（冪等処理）
- RSS フィードからニュース記事を収集し、記事と銘柄コードの紐付けを行う
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）を提供する
- マーケットカレンダーの管理・営業日判定ユーティリティを提供する
- 監査ログ（シグナル→発注→約定）用のスキーマと初期化機能を提供する
- データ品質チェック（欠損、重複、スパイク、日付不整合）を実行する

設計上の特徴：
- J-Quants API のレート制限（120 req/min）を守る RateLimiter を実装
- API リトライ・指数バックオフ、401 の自動トークンリフレッシュ対応
- データ取得時に fetched_at を UTC で記録し、Look-ahead Bias を防止
- DuckDB への保存は ON CONFLICT で冪等化
- RSS 収集は SSRF・XML Bomb 等に配慮した堅牢な実装

---

## 機能一覧

- 環境変数 / .env 自動読み込み（`kabusys.config`）
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーの取得
  - ページネーション対応、リトライ、レート制御、トークンキャッシュ
  - DuckDB へ保存するための save_* 関数（冪等）
- ニュース収集（`kabusys.data.news_collector`）
  - RSS フィード取得・前処理・記事ID生成（URL 正規化 + SHA-256）
  - SSRF 防止、受信サイズ上限、XML セーフパース（defusedxml）
  - raw_news / news_symbols への安全なバルク保存
- スキーマ定義・初期化（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - init_schema() により DuckDB を初期化
- ETL パイプライン（`kabusys.data.pipeline`）
  - 日次 ETL 実行（run_daily_etl）: カレンダー→株価→財務→品質チェック
  - 差分取得・バックフィル・品質チェック（結果を ETLResult で返却）
- マーケットカレンダー管理（`kabusys.data.calendar_management`）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間差分更新
- 監査ログ（`kabusys.data.audit`）
  - signal_events / order_requests / executions テーブルとインデックス
  - init_audit_schema / init_audit_db
- 品質チェック（`kabusys.data.quality`）
  - 欠損データ、スパイク、重複、日付不整合の検出
  - QualityIssue オブジェクトで詳細を返す

---

## セットアップ手順

前提
- Python 3.10 以上（typing の `X | Y` を使用しているため）
- DuckDB、defusedxml などの外部依存をインストールしてください

推奨的な手順（プロジェクトルートに pyproject.toml がある想定）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) / .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml

   （プロジェクトに requirements/pyproject があればそれに従ってください）

3. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

環境変数（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

オプション（デフォルト値あり）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を指定すると .env 自動ロードを無効化
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）

よく使う .env の例（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単な例）

初期化と日次 ETL 実行（最小例）:

```python
from pathlib import Path
import datetime
import duckdb

from kabusys.data import schema, pipeline
from kabusys.config import settings

# DB 初期化（ファイルがなければ作成）
db_path = settings.duckdb_path  # もしくは Path("data/kabusys.duckdb")
conn = schema.init_schema(db_path)

# 日次 ETL を実行（今日を対象）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

RSS ニュース収集の実行例:

```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# 既知銘柄コードのセット（例）
known_codes = {"7203", "6758", "9984"}

# デフォルトソース（Yahoo Finance のビジネスカテゴリ）を使用して収集
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
```

監査ログスキーマを追加する（既存の DuckDB 接続に）:

```python
from kabusys.data import audit, schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

カレンダーの夜間更新ジョブを実行する:

```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")
```

J-Quants の ID トークンを明示的に取得する例:

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用してトークンを取得
```

注意点:
- run_daily_etl 等は内部で例外処理を行い、ETLResult にエラー情報を蓄積します。呼び出し側でログや通知の判断を行ってください。
- .env 自動読み込みはプロジェクトルートを基準に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると良いです。

---

## ディレクトリ構成

主要なファイル・モジュールの一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py  (パッケージ初期化、__version__)
  - config.py    (環境変数・設定の読み込み / Settings)
  - data/
    - __init__.py
    - jquants_client.py        (J-Quants API クライアント、保存用関数含む)
    - news_collector.py       (RSS 取得・前処理・raw_news 保存)
    - schema.py               (DuckDB スキーマ DDL / init_schema)
    - pipeline.py             (ETL パイプライン：run_daily_etl など)
    - calendar_management.py  (マーケットカレンダー管理)
    - audit.py                (監査ログスキーマ初期化)
    - quality.py              (データ品質チェック)
  - strategy/
    - __init__.py             (戦略層のための名前空間)
  - execution/
    - __init__.py             (発注/実行層のための名前空間)
  - monitoring/
    - __init__.py             (監視関連の名前空間)

各モジュールの役割:
- config: 環境変数の安全な読み込み・検証、Settings オブジェクトを提供
- data: データ取得・保存・ETL・品質チェック・監査ログなどの中心機能
- strategy / execution / monitoring: 今後の拡張領域（現在は名前空間のみ）

---

## 注意事項・運用面のヒント

- Python バージョンは 3.10 以上を推奨します（型表記に | を使用）。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb。複数プロセスからの同時書き込みには注意してください（運用設計を行ってください）。
- J-Quants API のレート制限を守るため、ライブラリは内部で RateLimiter を使用しています。大量バックフィル等を行う際は考慮してください。
- ニュースフィードの取得は外部 URL に依存するため、ネットワークやフィードの変更により変化します。SSRF や XML 攻撃対策は組み込まれていますが、実運用時は監視を行ってください。
- 品質チェックは Fail-Fast ではありません。結果を確認し、必要に応じてアラートや手動介入を行ってください。
- 本ライブラリは署名・暗号化・秘密管理などの機能は含みません。シークレットは適切な手段で管理してください（Vault、Secrets Manager 等）。

---

## 貢献・拡張

- strategy、execution、monitoring パッケージは戦略ロジックやブローカー接続、監視プラグラムを実装するための拡張ポイントです。
- テストを追加する際は、環境自動ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用し、依存外部コールはモックしてください（例: news_collector._urlopen、jquants_client._request 等を差し替え可能）。

---

必要であれば、README に具体的な例（cron/airflow による ETL スケジューリング、Dockerfile、CI 設計、ユニットテストのサンプル）を追加できます。どの情報を追加したいか教えてください。
# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。J-Quants API から市場データ・財務データ・カレンダーを取得して DuckDB に蓄積し、特徴量エンジニアリング、シグナル生成、ニュース収集、カレンダー管理、ETL パイプライン、監査ログなどを一貫してサポートします。

バージョン: 0.1.0

---

## 主な機能

- データ取得・保存
  - J-Quants からの日次株価（OHLCV）、四半期財務データ、JPX カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ）
  - DuckDB への冪等的保存（ON CONFLICT / upsert）

- ETL パイプライン
  - 差分取得（最終取得日からの再取得・バックフィル）
  - カレンダー先読み、品質チェック（欠損・スパイク等の検出）

- 特徴量（Feature）生成
  - モメンタム / バリュー / ボラティリティ / 流動性等を計算し Z スコア正規化して features テーブルへ保存（冪等）

- シグナル生成
  - 正規化済みファクターと AI スコアを統合して final_score を算出し BUY/SELL シグナルを生成（冪等、Bear レジーム抑制、エグジット条件）

- ニュース収集
  - RSS フィード取得、XML の堅牢パース（defusedxml）、URL 正規化、記事保存、銘柄紐付け（news_symbols）

- マーケットカレンダー管理
  - JPX カレンダーの差分更新、営業日判定・前後営業日取得などユーティリティ

- 監査ログ / 発注監査設計
  - signal_events, order_requests, executions などトレーサビリティ用テーブルを提供

---

## 前提 / 必要環境

- Python 3.10+（typing union syntax 等を利用）
- 必須 Python パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード等）
- J-Quants API のリフレッシュトークン、kabuステーション API パスワード、Slack トークン等の環境変数

パッケージインストール例（仮）:
```bash
python -m pip install duckdb defusedxml
```

※ 実運用では追加パッケージ（ログ集約、Slack クライアント等）を別途導入する可能性があります。

---

## 環境変数 / 設定

kabusys は .env ファイルまたは環境変数から設定を読み込みます（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）

任意 / デフォルト:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | ...（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=DEBUG
```

読み込みルール:
- OS 環境変数 > .env.local > .env の優先順でロード
- .env.local があれば .env の上書きが可能

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 環境を作成して依存パッケージをインストール
   - 例: python -m venv .venv && source .venv/bin/activate
   - pip install -r requirements.txt（requirements.txt があれば）
   - 必要なら duckdb, defusedxml をインストール
3. プロジェクトルートに .env を作成し、必要な環境変数を設定
4. DuckDB スキーマを初期化
   - 以下の Python スクリプト例を実行

例: スキーマ初期化
```python
from pathlib import Path
from kabusys.data.schema import init_schema
db_path = Path("data/kabusys.duckdb")
conn = init_schema(db_path)
conn.close()
```

デフォルトの DB パスを使用せずメモリで試す場合:
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
# テスト実行
conn.close()
```

---

## 基本的な使い方（コード例）

以下は主要 API の利用例です。多くの関数は duckdb 接続と対象日付（date）を受け取ります。

- ETL（日次）実行例:
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（既に初期化済みなら get_connection を使う）
conn = init_schema("data/kabusys.duckdb")

# 当日分の ETL を実行
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量ビルド（feature_engineering.build_features）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {n}")
```

- シグナル生成（signal_generator.generate_signals）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"signals written: {total}")
```

- ニュース収集ジョブ（RSS 収集）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄セットを用意
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- 各種 API は冪等設計で、同じ date を上書きする方式（DELETE -> INSERT など）を採用しています。
- J-Quants へのリクエストは内部でレート制御・リトライが行われます。

---

## 主要モジュール / ディレクトリ構成

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数設定読み込み / Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証・ページネーション・保存ユーティリティ）
    - schema.py
      - DuckDB スキーマ定義と init_schema
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - news_collector.py
      - RSS 取得・パース・raw_news 保存・銘柄抽出
    - calendar_management.py
      - 市場カレンダー更新と営業日ユーティリティ
    - features.py
      - zscore_normalize の再エクスポート
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）
    - (その他: quality モジュール等が想定される)
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブルへのファクター正規化・UPSERT
    - signal_generator.py
      - final_score の計算、BUY/SELL シグナル生成
  - execution/
    - __init__.py
      - （発注/実行層の実装用プレースホルダ）
  - monitoring/
    - （監視系 / メトリクス系の実装場所想定）

ファイルごとの責務はソース内ドキュメントに詳述されています（各モジュールの docstring を参照してください）。

---

## 運用上の注意点 / 補足

- セキュリティ:
  - RSS パースで defusedxml を使い XML Bomb 対策を行っています。
  - News Collector は SSRF 対策（リダイレクト検証、プライベートアドレス拒否）を実装しています。
  - 環境変数（API キー等）は漏洩しないよう管理してください。

- Look-ahead Bias 回避:
  - 特徴量／シグナル生成は target_date 時点で「実際に利用可能なデータのみ」を参照する設計です（fetched_at トラッキング等）。

- 冗長性 / 冪等性:
  - DB への保存は基本的に冪等（ON CONFLICT / DELETE → INSERT）で行われます。ETL を複数回実行しても重複データが発生しにくい設計です。

- テスト:
  - 多くの関数は id_token や DB 接続の注入が可能で、ユニットテストがしやすい設計になっています。

---

## ライセンス / コントリビューション

（本リポジトリにライセンスファイルがある場合はそちらを参照してください。コントリビューションガイドラインは別途用意してください。）

---

README に記載のない使い方や、実行時に出るエラーのトラブルシュート、追加のユーティリティ（品質チェックや execution 層の実装）について支援が必要でしたら、使用ケース・期待する動作を教えてください。
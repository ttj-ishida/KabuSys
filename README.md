# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ/スキーマ管理などを含むモジュールで構成されています。DuckDB を組み込みデータベースとして利用します。

---

## 主要機能（概要）

- データ取得
  - J-Quants API から株価（日足）、財務データ、マーケットカレンダーを取得（ページネーション/リトライ/トークン自動リフレッシュ対応）
- ETL（差分更新）
  - 差分取得・保存（冪等性を考慮した保存処理）、品質チェックフレームワークとの連携
- データスキーマ管理
  - DuckDB 用のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 研究・特徴量
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - Zスコア正規化ユーティリティ
- 戦略（Signal）
  - 特徴量 + AI スコアを統合して final_score を計算、BUY/SELL シグナルを生成
  - Bear レジーム判定、エグジット（ストップロス等）
- ニュース収集
  - RSS から記事を取得、正規化・SSRF対策・トラッキングパラメータ削除、DuckDB に保存
- カレンダー管理
  - JPX カレンダーを取得・保存、営業日判定 / 前後営業日検索など
- 監査ログ
  - シグナル → 発注 → 約定 のトレーサビリティを記録する監査テーブル定義

---

## 必要条件（依存ライブラリ・環境）

最低限の Python パッケージ例:

- Python 3.8+
- duckdb
- defusedxml

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（プロジェクト内の実際の pyproject.toml / requirements.txt があればそちらを利用してください）

---

## 環境変数 / 設定

設定は .env ファイルまたは環境変数で行います。自動で .env / .env.local をプロジェクトルートから読み込みます（ただしテスト等で無効化可能）。

必須の環境変数（Settings クラス参照）:

- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャネルID

任意・デフォルト値あり:

- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` / `INFO` / ...（デフォルト: INFO）

自動 .env 読み込みを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例 .env（参考）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをチェックアウトする

2. 仮想環境を作成して依存をインストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# その他必要なパッケージがあれば追加で pip install してください
```

3. 環境変数（.env）を作成する（上記を参照）

4. DuckDB スキーマ初期化

Python コンソールまたはスクリプトで:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

db_path = settings.duckdb_path  # または pathlib.Path("data/kabusys.duckdb")
conn = init_schema(db_path)
# conn は duckdb.DuckDBPyConnection インスタンス
```

init_schema は必要なテーブルをすべて作成します（冪等）。

---

## 使い方（主要 API と実行例）

以下はライブラリの主要なエントリポイントと簡単な使用例です。すべて DuckDB 接続 (duckdb.DuckDBPyConnection) を受け取ります。

- ETL（日次パイプライン）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

run_daily_etl は市場カレンダー、株価、財務データを差分取得して保存し（backfill あり）、品質チェックを実行します。ETLResult で取得/保存数や品質問題・エラーを参照できます。

- 特徴量作成（Feature Engineering）

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date(2025, 1, 20))
print(f"features upserted: {count}")
```

build_features は research モジュールのファクター計算結果を正規化して `features` テーブルに UPSERT（実質は日付単位の置換）します。

- シグナル生成

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = generate_signals(conn, target_date=date(2025, 1, 20))
print(f"signals written: {n}")
```

generate_signals は `features` と `ai_scores` を統合して BUY/SELL シグナルを `signals` テーブルに保存します。weights や threshold のカスタマイズ可能。

- ニュース収集ジョブ（RSS）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄一覧を用意
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## ロギング

ログレベルは環境変数 LOG_LEVEL で制御します。`settings.log_level` で検証済みの値のみ受け入れます（DEBUG / INFO / ...）。

ライブラリは標準ライブラリの logging を利用します。アプリ側でハンドラ/フォーマットを設定してください。

例:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

---

## ディレクトリ構成（主要ファイルと説明）

以下は `src/kabusys` 配下のおおまかな構成（コードベースより抜粋）です。

- src/kabusys/
  - __init__.py  — パッケージの定義（__version__ = "0.1.0"）
  - config.py  — 環境変数 / 設定の管理（Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py  — RSS 収集・前処理・DB 保存
    - schema.py  — DuckDB スキーマ定義・初期化（init_schema / get_connection）
    - stats.py  — zscore_normalize 等の統計ユーティリティ
    - pipeline.py  — ETL パイプライン（run_daily_etl 他）
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - audit.py  — 監査ログ用テーブル定義
    - features.py — data.stats の公開ラッパー
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン、IC、統計サマリー等（研究用）
    - factor_research.py — momentum / volatility / value のファクター計算
  - strategy/
    - __init__.py  — build_features / generate_signals の公開
    - feature_engineering.py — ファクター正規化と features テーブルへの保存
    - signal_generator.py — final_score 計算と signals への保存
  - execution/  — 発注・実行関連（空の __init__.py がある想定）
  - monitoring/ — 監視・モニタリング関連（モジュール群が想定される）

（README に掲載している構成は現行コードの主要ファイルを要約したものです）

---

## 設計上の注意点 / 運用メモ

- データの冪等性に配慮しており、DB への保存は ON CONFLICT などを活用して上書きまたはスキップする実装になっています。
- ルックアヘッドバイアス回避のため、すべての計算は target_date 時点までに「システムが知りうる」データのみを使用するよう設計されています。
- J-Quants API のレート制限（120 req/min）・リトライ・トークンリフレッシュを考慮した実装があります。
- ニュース収集は SSRF 対策（リダイレクト先検査、プライベートIP拒否）や XML の安全なパース（defusedxml）を組み込んでいます。
- DuckDB のスキーマは監査・実行層まで含むため、本番環境で利用する場合はバックアップ/保護に留意してください。
- KABUSYS_ENV を `live` に設定すると実運用用ロジック（必要に応じた分岐）を有効化する想定です。運用前に設定値とアクセス権を確認してください。

---

## 開発 / 貢献

- コード内の docstring とコメントに仕様・セクション参照（例: StrategyModel.md, DataPlatform.md）が多数あります。これらの外部ドキュメントを合わせて参照すると設計意図が理解しやすくなります。
- テストや CI のセットアップは本リポジトリに依存します。外部 API を呼ぶ部分はモック化してテストしてください（jquants_client._request などの差し替えが容易な設計）。

---

必要であれば、この README に次の追加情報を加えます：
- 実行スクリプト（CLI）や systemd / cron での日次バッチ例
- さらに細かい DB スキーマ説明（各テーブルカラムの意味）
- サンプル .env.example ファイル
- 開発用の Makefile / tox / pre-commit 設定例

どれを追加したいか教えてください。
# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量作成、戦略のシグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、研究〜運用に必要な主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 主要機能

- J-Quants API クライアント
  - 株価（OHLCV）、財務データ、JPX カレンダーをページネーション対応で取得
  - レート制御、リトライ、401 トークン自動リフレッシュ
- ETL パイプライン
  - 差分更新、バックフィル、品質チェック（quality モジュール連携）
  - 日次 ETL のエントリポイント（run_daily_etl）
- DuckDB ベースのスキーマ定義・初期化（init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
- ニュース収集
  - RSS 取得、前処理、記事保存（重複回避）、銘柄抽出・紐付け
  - SSRF 対策、受信サイズ制限、XML 安全パーサ使用
- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Zスコア正規化ユーティリティ
- 戦略
  - 特徴量構築（build_features）: research で算出した raw factor を統合・正規化して features テーブルへ保存
  - シグナル生成（generate_signals）: features と ai_scores を統合して BUY/SELL シグナルを作成
- 監査ログ（audit モジュール）
  - signal → order_request → executions のトレーサビリティを保持する監査テーブル群

---

## 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリのみで動くユーティリティも多く含まれますが、実行には上記の外部パッケージが必要です。

pip インストール例:
```bash
pip install duckdb defusedxml
```

※ パッケージ管理・配布は環境に合わせて行ってください。

---

## セットアップ

1. リポジトリをクローン／展開する
2. 仮想環境を作成して依存をインストール
3. 環境変数を用意（.env または OS 環境変数）

必要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
- KABU_API_PASSWORD : kabu ステーション API のパスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack チャネル ID

任意 / デフォルトあり
- KABU_API_BASE_URL : kabu API のベース URL（既定: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（監視用）パス（既定: data/monitoring.db）
- KABUSYS_ENV : 環境 ("development" | "paper_trading" | "live")（既定: development）
- LOG_LEVEL : ログレベル ("DEBUG","INFO",...)（既定: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する場合に `1` を設定

.env の自動読み込みについて
- パッケージ起点のファイル（__file__）から上位ディレクトリを辿り、`.git` または `pyproject.toml` を検出したディレクトリをプロジェクトルートとみなします。
- 読み込み順: OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト用途等）。

例: .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=yyyyyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期化

DuckDB スキーマを作成する例:

```python
from kabusys.data.schema import init_schema

# ファイルに永続化する場合
conn = init_schema("data/kabusys.duckdb")

# インメモリ DB を使う場合
# conn = init_schema(":memory:")
```

既存 DB に接続するだけなら:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

---

## 主要な使い方（例）

- 日次 ETL（株価 / 財務 / カレンダー の差分取得と保存）:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- マーケットカレンダー更新ジョブ:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- ニュース収集（RSS）と銘柄紐付け:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 特徴量構築（strategy.feature_engineering.build_features）:

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print("features upserted:", count)
```

- シグナル生成（strategy.signal_generator.generate_signals）:

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2024,1,31))
print("signals written:", n)
```

---

## 設計上のポイント / 運用上の注意

- J-Quants クライアントはレート制御（120 req/min）とリトライ、401 発生時の自動トークン再取得を実装しています。
- ETL や feature/signal の各操作は「日付単位で DELETE → INSERT（置換）」することで冪等性を確保しています。
- NewsCollector は SSRF 対策・XML の安全パース・最大受信サイズ制限を行い、記事 ID は正規化 URL の SHA-256 の先頭を使用して冪等性を保証します。
- ローカル開発時は KABUSYS_ENV=development、ペーパートレード用に paper_trading、本番は live を使用します（設定値は Settings で検証されます）。
- DB のスキーマには一部の外部キーの ON DELETE 動作が DuckDB のバージョン差異で制約されるため、削除時はアプリ側で整合性を取る必要があります（コード内コメント参照）。

---

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下に配置）

- kabusys/
  - __init__.py
  - config.py  ← 環境変数・設定
  - data/
    - __init__.py
    - jquants_client.py         ← J-Quants API クライアント
    - pipeline.py               ← ETL パイプライン（run_daily_etl 等）
    - schema.py                 ← DuckDB スキーマ定義・init_schema
    - stats.py                  ← 統計ユーティリティ（zscore_normalize）
    - news_collector.py         ← RSS ニュース収集・保存
    - calendar_management.py    ← カレンダー管理・ジョブ
    - features.py               ← data.stats の再エクスポート
    - audit.py                  ← 監査ログ用DDL（signal_events 等）
    - (その他: quality, etc. は別モジュール想定)
  - research/
    - __init__.py
    - factor_research.py        ← モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py    ← 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py    ← build_features
    - signal_generator.py       ← generate_signals
  - execution/                  ← 発注・execution 層（初期化ファイルあり）
  - monitoring/                 ← 監視関連（存在する場合）

---

## 追加情報

- ログレベルや環境は Settings クラスで検証され、無効な値は例外になります。許可される環境値は: development, paper_trading, live。
- DUCKDB の初期化時に必要な親ディレクトリが自動作成されます。
- DuckDB を直接操作することで高速な分析処理が行えます。戦略・研究用の SQL / Python ハイブリッド処理が想定されています。

---

問題や拡張要望、特定機能の利用例（サンプルコード）を希望される場合は、どの操作（ETL / ニュース収集 / シグナル生成 等）についての具体例が欲しいか教えてください。
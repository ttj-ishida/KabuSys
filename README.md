# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
DuckDB を用いたデータレイヤ、J-Quants からのデータ取得、ニュース収集、ファクター計算、特徴量正規化、戦略シグナル生成、ETL パイプライン等を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を備えたモジュール群で構成されるライブラリです。

- J-Quants API を用いた株価・財務・カレンダー取得（認証 / ページネーション / レート制御 / 再試行付き）
- DuckDB によるスキーマ定義と冪等なデータ保存（ON CONFLICT / トランザクション）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究 (research) 用ファクター計算、Z スコア正規化、特徴量合成
- 戦略層: 特徴量からシグナル（BUY/SELL）の生成
- ニュース収集（RSS）と記事→銘柄紐付け、SSRF / XML 安全対策
- 発注・実行・監査のテーブル設計（実装のためのスキーマ群）

設計方針として、ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）、外部 API への不要な依存回避、冪等性（再実行安全）を重視しています。

---

## 主な機能一覧

- data/schema.init_schema(db_path): DuckDB スキーマを初期化
- data/jquants_client:
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レート制御、リトライ、トークン自動リフレッシュ対応
- data/pipeline.run_daily_etl: 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
- data/news_collector.run_news_collection: RSS 収集 → raw_news 保存 → 銘柄抽出・紐付け
- research.factor_research: mom / volatility / value 等のファクター計算
- strategy.feature_engineering.build_features: ファクターを正規化・クリップして features テーブルへUPSERT
- strategy.signal_generator.generate_signals: features と ai_scores を統合して BUY / SELL シグナルを作成
- data/calendar_management: 営業日判定 / next/prev trading day 等のユーティリティ
- data/stats.zscore_normalize: クロスセクション Z スコア正規化ユーティリティ

---

## 要件（主な Python パッケージ）

本リポジトリのコードは標準ライブラリに加え、少なくとも以下のパッケージを必要とします。

- Python 3.9 以上（typing | union 型などの利用想定）
- duckdb
- defusedxml

インストール例（仮）:

```bash
python -m pip install duckdb defusedxml
# プロジェクトが配布パッケージ化されている場合:
# pip install -e .
```

（実際の requirements.txt / pyproject.toml があればそちらを利用してください）

---

## セットアップ手順（クイックスタート）

1. リポジトリを取得して依存をインストール

```bash
git clone <repo-url>
cd <repo-dir>
python -m pip install -r requirements.txt   # もしあれば
# または最低限:
python -m pip install duckdb defusedxml
```

2. 環境変数の設定

必須環境変数（例）:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

デフォルト DB パス（任意で変更可）:

- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (monitoring 用、デフォルト: data/monitoring.db)

.env ファイルをプロジェクトルートに配置すると、自動的に読み込まれます（.env.local は優先して上書き）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env):

```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

3. データベーススキーマ初期化

Python REPL かスクリプトで:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: も可
```

init_schema は必要なディレクトリを作成し、すべてのテーブルを冪等に作成します。

---

## 使い方（主要ワークフロー例）

- 日次 ETL の実行（市場カレンダー、株価、財務、品質チェック）

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量の構築（features テーブルへの書き込み）

```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブルへ書き込み）

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

- ニュース収集ジョブ（RSS → raw_news、news_symbols へ紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（抽出に使用）
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- J-Quants から直接データを取得して保存する（低レベル API）

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))
saved = jq.save_daily_quotes(conn, records)
```

---

## 重要な設計・挙動メモ

- 自動環境変数ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` → `.env.local` の順で読み込みます。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - テストなどで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 冪等性:
  - jquants_client の保存関数は ON CONFLICT / DO UPDATE を利用しており、再実行による重複を防ぎます。
  - feature/signal の書き込みは一時的に該当日を DELETE してから一括挿入することで日付単位の置換（冪等）を保証します。

- セキュリティ / 安全性:
  - news_collector は SSRF 対策（スキーム検査、プライベートIPブロッキング、リダイレクト検査）、XML の安全パーサ（defusedxml）、レスポンスサイズ制限を実装しています。
  - jquants_client はレート制御（120 req/min）、指数バックオフによるリトライ、401 時のトークン自動リフレッシュを備えています。

- 研究・戦略層:
  - factor_research / feature_engineering / signal_generator は「target_date 時点で利用可能なデータのみ」を用いることで将来情報の漏洩を防ぎます。
  - signal_generator は AI スコアやレジーム情報を考慮し、Bear 相場時の BUY シグナル抑制、ストップロスやスコア低下に基づくエグジット判定を行います。

---

## 主要モジュール一覧（ハイレベル）

- kabusys.config: 環境変数 / 設定管理
- kabusys.data
  - jquants_client.py: J-Quants API クライアント + 保存
  - schema.py: DuckDB スキーマ定義 / init_schema
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - news_collector.py: RSS 取得・前処理・保存・銘柄抽出
  - calendar_management.py: 営業日管理ユーティリティ
  - stats.py: zscore_normalize 等
- kabusys.research: factor 計算・探索用関数
- kabusys.strategy: build_features / generate_signals
- kabusys.execution: （発注層用のプレースホルダ / 将来的な実装）

---

## ディレクトリ構成

（リポジトリの主要部分）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - stats.py
      - features.py
      - audit.py
      - pipeline.py
      - (その他 data 関連モジュール)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - (research 用ユーティリティ)
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/ (監視・モニタリング用モジュール（未詳）)
    - (その他のユーティリティ)

---

## 開発・デバッグのヒント

- ログレベルは `LOG_LEVEL` 環境変数で設定（DEBUG/INFO/...）。KABUSYS_ENV による挙動差分（development / paper_trading / live）があります。
- DB の初期化後は DuckDB への SQL を直接実行してテーブルの中身やインデックスを確認できます。
- 単体テスト・統合テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い、環境変数の自動読み込みを抑制してテスト用設定を注入してください。
- news_collector のネットワークリクエストはテストしにくいため `_urlopen` をモックすると良いです。

---

必要であれば README に含める具体的な .env.example、CI / テスト実行方法、依存関係ロックファイルの追記、または各モジュールの API リファレンス（関数引数・戻り値の詳細）を追加します。どの部分を拡張しますか？
# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。データ取得（J-Quants）、ETL、ファクター算出、特徴量エンジニアリング、シグナル生成、ニュース収集、DuckDB スキーマ管理など、戦略の研究から本番実行までの基盤機能を提供します。

## 主要機能
- J-Quants API クライアント（データ取得・トークン自動更新・レート制御・リトライ）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェックフロー）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ、features テーブルへの UPSERT）
- シグナル生成（複数コンポーネントを重み付けして final_score を算出、BUY/SELL 判定）
- ニュース収集（RSS 取得、前処理、記事保存、銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- セキュリティ配慮（SSRF対策、XMLパースに defusedxml を使用、レスポンスサイズ上限など）

## 要件（代表）
- Python 3.10+
- duckdb
- defusedxml
- （標準ライブラリで多くを賄う設計ですが、実行環境に応じて他パッケージが必要になる場合があります）

インストールはプロジェクト配布方法に依存します。開発環境では通常の仮想環境を作成して pip install -e . 等で導入してください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
pip install -e .
```

## 環境設定
設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot token（必須）
- SLACK_CHANNEL_ID: Slack channel ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

.env のサンプル（例）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

## セットアップ手順（概要）
1. リポジトリをクローンして仮想環境を作成する
2. 依存パッケージをインストール（少なくとも duckdb, defusedxml）
3. `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化

DuckDB スキーマ初期化例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

またはコマンドラインで簡易スクリプトを作ることもできます。

## 基本的な使い方（コード例）
以下はライブラリの代表的な利用例です。

- DuckDB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（市場カレンダー、株価、財務を差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn)  # 設定に基づき今日分を処理
print(res.to_dict())
```

- 特徴量（features）構築
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date(2026, 1, 31))
print(f"features upserted: {count}")
```

- シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals

n = generate_signals(conn, target_date=date(2026, 1, 31))
print(f"signals generated: {n}")
```

- ニュース収集（既知の銘柄コードセットを渡して紐付け）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は Set[str]（例: {"7203", "6758", ...}）
result = run_news_collection(conn, known_codes={"7203", "6758"})
print(result)
```

- J-Quants から日足を取得して保存（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
saved = save_daily_quotes(conn, records)
print(saved)
```

## 実行上の注意点
- ETL / シグナル生成等は DuckDB 上のテーブルを前提とします。必ず init_schema() を使ってスキーマを作成してください。
- 環境変数（特に JQUANTS_REFRESH_TOKEN 等）の未設定は Settings により ValueError が発生します。
- KABUSYS_ENV により挙動（本番/ペーパー）を分けられます。値は development / paper_trading / live のいずれかにしてください。
- ニュース収集・RSS 取得では SSRF 対策、レスポンスサイズチェック、gzip 解凍上限等を実装していますが、外部ソースの扱いには注意してください。

## 推奨ワークフロー（例）
1. DuckDB スキーマ初期化
2. run_daily_etl() でデータ取得・保存・品質チェック
3. build_features() で特徴量を作成
4. generate_signals() でシグナルを生成（必要に応じて weight や threshold を引数で調整）
5. シグナルは信頼できる監査・発注フローへ渡して実行

## ディレクトリ構成
（主要ファイルを抜粋）

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ schema.py
   │  ├─ stats.py
   │  ├─ pipeline.py
   │  ├─ features.py
   │  ├─ calendar_management.py
   │  ├─ audit.py
   │  └─ ... (quality 等の補助モジュール)
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py
   │  ├─ feature_exploration.py
   │  └─ ... (研究用ユーティリティ)
   ├─ strategy/
   │  ├─ __init__.py
   │  ├─ feature_engineering.py
   │  └─ signal_generator.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/   (未詳細実装部分)
```

各サブパッケージの役割:
- data: データ取得／保存／DuckDBスキーマ／ETL／ニュース収集 等
- research: ファクター計算や研究用統計ツール
- strategy: 特徴量構築とシグナル生成
- execution: 発注・約定やポジション管理のための層（インターフェース）
- monitoring: 監視・メトリクス関連（将来的な機能）

## テスト・デバッグ
- 環境変数の自動読み込みは .env/.env.local をプロジェクトルートから探索して行われます。テスト時に自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 関数の多くは DuckDB の接続オブジェクトを引数に取るため、インメモリ DB（":memory:"）でユニットテストを実行できます:
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

## 貢献・拡張
- 新しいファクターや AI スコアの統合は research/ と strategy/ の拡張で対応できます。
- execution 層は証券会社 API に応じて実装を差し替え可能なインターフェース設計を想定しています。
- ニュースソースを追加する場合は data/news_collector.DEFAULT_RSS_SOURCES を拡張してください。

---

不明点や追加してほしい使用例（CLI スクリプト、cron ジョブ定義、Slack 通知のサンプル等）があればお知らせください。README に追記します。
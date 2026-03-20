# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築のための共通ライブラリです。  
主に以下の領域をカバーします。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータスキーマと永続化（冪等保存）
- ETL（差分更新、バックフィル、品質チェック）
- 研究（research）で算出した生ファクターの正規化・統合
- 戦略（strategy）用の特徴量生成 / シグナル生成
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダーの管理（営業日判定等）
- 発注・監査ログ向けのスキーマ（監査トレーサビリティ）

設計方針として、ルックアヘッドバイアス対策、冪等性、API レート制御、トレーサビリティを重視しています。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、トークン自動リフレッシュ、レートリミット）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次差分 ETL（prices / financials / market_calendar）、品質チェック連携
  - news_collector: RSS ニュース収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定、next/prev_trading_day、夜間カレンダー更新ジョブ
  - stats: Z スコア正規化等の統計ユーティリティ
- research/
  - factor_research: momentum/value/volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリ
- strategy/
  - feature_engineering: 生ファクターの正規化・ユニバースフィルタ、features テーブルへの UPSERT
  - signal_generator: features と ai_scores を統合して final_score を計算、BUY/SELL シグナル生成、signals テーブルへの書き込み
- audit / execution / monitoring 用のスキーマとフレームワーク（監査ログ、order_requests, executions 等）
- 環境設定読み込み（.env 自動読み込み、環境変数管理）

---

## 前提 / 必要環境

- Python 3.10 以上（型アノテーションで | を使用）
- 依存パッケージ（代表例）:
  - duckdb
  - defusedxml

インストール例:
```
python -m pip install duckdb defusedxml
```

（パッケージ化されている場合は `pip install -e .` 等でインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得
2. 仮想環境を作成して依存パッケージをインストール
3. 環境変数の設定 (.env)

例: `.env`（プロジェクトルート）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabuステーション (必要なら)
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（省略時: data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb

# 実行環境 (development | paper_trading | live)
KABUSYS_ENV=development

# ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
LOG_LEVEL=INFO
```

注意:
- パッケージの `kabusys.config` はプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動読み込みします。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須環境変数が未設定の場合は `kabusys.config.Settings` のプロパティで例外が発生します（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）。

4. DuckDB スキーマ初期化

Python REPL / スクリプトから:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
```

これで必要なテーブルとインデックスが作成されます（冪等）。

---

## 使い方（主なユースケース）

以下は代表的な利用例（Python スクリプト内または REPL）。

- 日次 ETL（市場カレンダー・株価・財務の差分取得と保存）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量の構築（features テーブルへ書き込み）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成（features / ai_scores / positions を参照して signals を更新）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {n}")
```

- RSS ニュース収集と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（DBから取得して利用する想定）
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # ソース毎の新規保存数
```

- マーケットカレンダー / 営業日判定
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
d = date(2024, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- J-Quants 生データ取得（プログラム的）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = save_daily_quotes(conn, records)
print(saved)
```

---

## 設定と注意点

- 環境変数は Settings プロパティ経由で取得されます（kabusys.config.Settings）。
  - 有効な環境値:
    - KABUSYS_ENV: "development", "paper_trading", "live"
    - LOG_LEVEL: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
- 自動 .env 読み込みの挙動:
  - 読み込み優先順位: OS 環境 > .env.local > .env
  - テスト時に自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制御やリトライは jquants_client 内で管理されます（120 req/min、指数バックオフ等）。
- DuckDB 側のトランザクションは多くの書き込みで使用しており、失敗時は明示的にロールバック処理が試みられる設計です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - audit（監査用DDL/ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - （その他モジュール: monitoring 等は __all__ に記述がありますが、実装は該当ファイルをご確認ください）

---

## テスト / 開発

- ユニットテストやモックを使って API 呼び出しやネットワークアクセスを代替してください。
- jquants_client の id_token キャッシュや _urlopen はテスト時に差し替え可能（モック化を想定）。
- DuckDB のインメモリ接続（db_path=":memory:"）でテストが可能です。

---

## 貢献 / 注意事項

- 本リポジトリは金融データ・発注に関わるため、実運用で使用する際は各種リスク（API レート、認証情報流出、発注の二重実行等）に十分注意してください。
- 実際の発注連携を行う場合は paper_trading モードで十分に検証を行ってください。

---

ライセンス: リポジトリ内に明示的なライセンス表記がない場合は、利用前にライセンス情報の確認を推奨します。
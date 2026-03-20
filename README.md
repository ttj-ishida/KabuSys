# KabuSys

日本株向けの自動売買基盤ライブラリ。データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ/監査ログなどを備え、研究 → バックテスト → 実運用に繋がる基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を主目的とする Python パッケージ群です。

- J-Quants API からの差分取得（株価・財務・カレンダー）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）スキーマ管理
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量の正規化（Z スコア）と features テーブルへの永続化
- features + AI スコア統合による売買シグナル生成（BUY / SELL）
- RSS フィードからのニュース収集と銘柄紐付け
- JPX カレンダー管理（営業日/半日/SQ判定）
- 発注・約定・監査ログのためのスキーマ（監査トレーサビリティ設計）

設計方針として「ルックアヘッドバイアスの回避」「冪等性（ON CONFLICT 等）」「外部 API のレート制御・リトライ」「DB トランザクションによる原子性」を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント、ID トークン自動リフレッシュ、ページネーション、レート制御、保存用ユーティリティ（save_*）。
- data/schema.py
  - DuckDB 用スキーマ定義・初期化（init_schema）、接続取得ユーティリティ。
- data/pipeline.py
  - 日次 ETL（run_daily_etl）、差分取得・バックフィル・品質チェックの統合。
- data/news_collector.py
  - RSS 収集、前処理、raw_news への保存、銘柄抽出・紐付け。
- data/calendar_management.py
  - market_calendar の更新と営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
- data/stats.py
  - zscore_normalize（クロスセクション Z スコア正規化）。
- research/*
  - ファクター計算（calc_momentum / calc_volatility / calc_value）、特徴量探索（IC 計算・forward returns・summary）。
- strategy/*
  - build_features（特徴量の集計・正規化・features テーブルへの upsert）
  - generate_signals（features + ai_scores 統合 → signals テーブルへ upsert）
- config.py
  - .env 自動読み込み（プロジェクトルート検出）、必須環境変数取得ラッパー（Settings クラス）

---

## 前提条件

- Python 3.10 以上（typing の union 型（|） を使用しているため）
- 必要な主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）
- J-Quants のリフレッシュトークン等の環境変数設定

（依存の細かいバージョンはプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成します。

   ```
   git clone <repository-url>
   cd <repository>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -U pip
   ```

2. 必要パッケージをインストールします（例）。

   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements/pyproject があればそちらを利用してください）

3. 環境変数を設定します。プロジェクトルートに `.env` を置くと自動で読み込まれます（config.py の自動ロード）。自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション等の API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   オプション:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化
   - KABUSYS_DB (※パス名は settings で DUCKDB_PATH / SQLITE_PATH を使用): DUCKDB_PATH, SQLITE_PATH

   例 `.env`（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 初期化（DuckDB スキーマ作成）

DuckDB ファイル（例: data/kabusys.duckdb）を初期化します。

Python から:

```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection オブジェクト
```

- init_schema は必要なすべてのテーブルとインデックスを作成します（冪等）。
- ":memory:" を渡すとインメモリ DB を使用できます。

---

## 使い方（主要ワークフロー）

以下は典型的な日次バッチの流れ例です。

1. DuckDB 初期化（上記参照）
2. 日次 ETL 実行（J-Quants から差分取得して保存）

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB を初期化（1 回）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. 特徴量構築（build_features）

```python
from datetime import date
from kabusys.strategy import build_features
# conn は duckdb 接続、target_date は ETL と同じ営業日
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4. シグナル生成（generate_signals）

```python
from kabusys.strategy import generate_signals
n_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n_signals}")
```

5. ニュース収集ジョブ（RSS → raw_news + news_symbols）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6. カレンダーの夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## よく使う API（抜粋）

- data.schema.init_schema(db_path) -> duckdb connection
- data.schema.get_connection(db_path) -> duckdb connection（既存 DB）
- data.pipeline.run_daily_etl(conn, target_date=None, ...) -> ETLResult
- strategy.build_features(conn, target_date) -> int (upsert count)
- strategy.generate_signals(conn, target_date, threshold=0.6, weights=None) -> int
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None) -> dict
- data.calendar_management.is_trading_day(conn, date) -> bool
- data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(conn, records)
- data.stats.zscore_normalize(records, columns) -> normalized records

各関数の詳細は docstring を参照してください（引数の意味・返り値・例外条件が記載されています）。

---

## ディレクトリ構成

主要なファイル/フォルダ構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定読み込み
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py         — RSS ニュース収集 / 前処理 / 保存
    - schema.py                 — DuckDB スキーマ定義 & init_schema
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — マーケットカレンダー管理
    - audit.py                  — 監査ログ / トレーサビリティ用 DDL（未完）
    - features.py               — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py        — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py    — forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py    — build_features
    - signal_generator.py       — generate_signals
  - execution/                  — 発注/実行関連（パッケージプレースホルダ）
  - monitoring/                 — 監視系モジュール（プレースホルダ）
- その他: pyproject.toml / README.md（本ファイル）等

---

## 開発・テスト

- 自動読み込みされる .env はプロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）を起点に探索します。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。
- DB をインメモリでテストするには `init_schema(":memory:")` を利用してください。
- ネットワーク依存（J-Quants / RSS）部分はユニットテストでモックすることを推奨します（例: news_collector._urlopen や jquants_client._request をモック）。

---

## 注意事項 / TODO

- 実運用（特に live 環境）では十分なログ、監視、リスク管理を別途構築してください。
- strategy/signal_generator はポジション管理・サイズ算出・発注ロジックを含んでいません。execution 層との統合が必要です。
- audit.py の DDL は監査用に用意されていますが、アプリケーションレイヤでの連携実装が必要です。
- J-Quants の API 利用制限や認証情報の管理は運用者側で安全に行ってください。

---

この README はコードベースの主な使い方と概観をまとめたものです。各モジュールの詳細は該当ファイルの docstring を参照してください。質問やドキュメント追加の希望があれば教えてください。
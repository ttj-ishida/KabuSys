# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
J-Quants からの市場データ取得、DuckDB によるデータ管理、特徴量生成、シグナル生成、ニュース収集、発注・約定・監査のためのスキーマ/ユーティリティを提供します。本リポジトリはライブラリ層（data / research / strategy / execution / monitoring など）を中心に実装されています。

---

## 主な特徴（機能一覧）

- データ取得
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動更新、レート制御、リトライ）
  - RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事ID の冪等化）
- 永続化・スキーマ
  - DuckDB 用の完全なスキーマ定義（Raw / Processed / Feature / Execution / Audit 層）
  - スキーマ初期化ユーティリティ（init_schema）
- ETL パイプライン
  - 日次差分 ETL（市場カレンダー、株価日足、財務データ）＋品質チェック
  - 差分取得・バックフィル・ロギングを考慮
- 研究（research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ / 流動性）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング
  - 生ファクターの統合・Z スコア正規化・ユニバースフィルタ・features テーブルへの冪等保存
- シグナル生成
  - 正規化済みファクターと AI スコアを統合し final_score を算出、BUY/SELL シグナル生成（売買ルール・エグジット条件含む）
- ニュース処理
  - RSS 取得 → raw_news 保存 → 銘柄抽出（4 桁コード）→ news_symbols への紐付け
- 監査 / トレーサビリティ
  - signal_events / order_requests / executions など監査ログ用テーブル群（UUID ベースの連鎖でトレース可能）

---

## 前提・依存関係

- Python 3.10 以上（型ヒントに | 演算子や typing 拡張を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib 等）を多用

実際の運用では追加の依存（Slack クライアント、kabu ステーション連携ライブラリ 等）やテストツールが必要になる可能性があります。用途に応じて requirements.txt を整備してください。

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを入手）してプロジェクトルートへ移動。

2. 仮想環境を作成して有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （開発用）pip install -e . などでローカルパッケージとしてインストール可能

4. 環境変数（.env）を準備
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（パッケージ初期化で .env/.env.local を自動ロード、無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID : Slack チャネル ID
   - 任意 / デフォルトあり
     - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると自動 .env ロードを無効化
     - KABU_API_BASE_URL : kabusapi のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : モニタリング用 SQLite（デフォルト: data/monitoring.db）
     - LOG_LEVEL : DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）

5. DuckDB スキーマ初期化（例）
   - Python REPL / スクリプトから:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

---

## 基本的な使い方（コード例）

下記は主要ユースケースの簡単な例です。詳細は各モジュールを参照してください。

- DB 初期化

```python
from kabusys.data.schema import init_schema

# ファイルパスは settings.duckdb_path を使うのが便利
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（J-Quants トークンは settings が参照）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）作成

```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 5))
print(f"features upserted: {n}")
```

- シグナル生成

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 5))
print(f"signals generated: {count}")
```

- ニュース収集ジョブ実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes = set(...) を渡すと記事から銘柄抽出して news_symbols に紐付ける
result = run_news_collection(conn, sources=None, known_codes=None)
print(result)
```

---

## 主要モジュールと役割（概要）

- kabusys.config
  - 環境変数読み込み / Settings クラス（KABUSYS_ENV 判定、必須チェック）
  - .env 自動ロード（.git や pyproject.toml をプロジェクトルートとして探索）
- kabusys.data.jquants_client
  - J-Quants API の認証・取得・保存ユーティリティ（fetch_*, save_*）
  - レートリミット / リトライ / トークン自動更新
- kabusys.data.schema
  - DuckDB 用 DDL 定義と init_schema、get_connection
  - テーブル群（raw_prices, prices_daily, features, signals, audit 等）
- kabusys.data.pipeline
  - 日次 ETL（市場カレンダー、株価、財務）と差分取得ロジック
- kabusys.data.news_collector
  - RSS フィード取得、記事正規化、raw_news への保存、銘柄抽出と紐付け
- kabusys.data.calendar_management
  - 営業日判定・次/前営業日算出・カレンダー更新ジョブ
- kabusys.data.stats
  - zscore_normalize など統計ユーティリティ
- kabusys.research
  - calc_momentum, calc_volatility, calc_value（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary（研究用ユーティリティ）
- kabusys.strategy
  - build_features（特徴量構築）
  - generate_signals（シグナル生成）
- kabusys.execution / kabusys.monitoring
  - 発注・約定・監視に関するプレースホルダ（実装を追加して利用）

---

## 推奨ワークフロー（運用例）

1. .env に必要情報を設定（J-Quants トークンなど）。
2. DuckDB のスキーマを init_schema() で作成。
3. nightly cron / GitHub Actions などで run_daily_etl() を実行しデータを更新。
4. 研究 / バックテストで kabusys.research の関数を使ってファクター評価。
5. 定期的に build_features() → generate_signals() を実行し signals を更新。
6. 実運用では execution 層を実装して signal_queue → order_requests → executions のフローを実現。
7. 監査テーブル（audit）で全フローをトレース。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (オプション、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (オプション、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (オプション、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — 設定ミスはエラーになります
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

---

## ディレクトリ構成（抜粋）

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
    - calendar_management.py
    - audit.py
    - features.py
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
  - monitoring/
    - (モニタリング関連コードを追加)
- pyproject.toml / setup.cfg / README.md (このファイル)
- .env.example (プロジェクトルートに置くことを推奨)

各ファイルは上記 README 内で説明した機能に対応しています。詳細な API（関数引数や戻り値の仕様）はソース内の docstring を参照してください。

---

## 注意事項 / セキュリティ

- J-Quants トークンや kabu API の資格情報は `.env` 等で管理し、バージョン管理システムにコミットしないでください。
- news_collector では SSRF 対策・XML パースの安全化（defusedxml）を実施していますが、追加のセキュリティレビューを推奨します。
- 実際の発注（execution）を行う場合は冪等制御・リスク管理・ロギングを厳格に実装してください（本リポジトリは発注インターフェースの下地を提供しますが、ブローカー接続の実装・検証は必要です）。

---

ご希望であれば、README に入れるサンプル .env.example、requirements.txt、あるいは具体的な運用手順（例: cron / systemd unit / コンテナ化）を追記します。どの情報を優先して追加しますか？
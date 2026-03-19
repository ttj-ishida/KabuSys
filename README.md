# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データ取得（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、監査・スキーマ管理など、量化投資システムに必要な主要コンポーネントを持ちます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計されたモジュール群です。

- J-Quants API を用いた市場データ（株価・財務・カレンダー）の取得と DuckDB への永続化
- データ品質チェックおよび差分 ETL（差分取得・バックフィル）
- 研究環境で計算した生ファクターを用いた特徴量生成（Z スコア正規化等）
- 正規化済み特徴量＋AI スコアを統合して売買シグナルを生成
- RSS ベースのニュース収集と記事→銘柄の紐付け
- DuckDB スキーマ定義と監査ログ（発注→約定トレーサビリティ）

設計上、発注 API（実際の証券会社接続）は execution 層に分離され、strategy 層や data 層は発注ロジックへ直接依存しないようになっています。

---

## 主な機能一覧

- 環境設定読み込み・管理（`.env`, `.env.local`, 環境変数）
- J-Quants API クライアント
  - データ取得（株価日足 / 財務 / 市場カレンダー）
  - レートリミット制御、リトライ、トークン自動リフレッシュ
- DuckDB スキーマ定義と初期化（豊富な Raw / Processed / Feature / Execution テーブル）
- ETL パイプライン（差分更新・品質チェック・バックフィル）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（final_score 計算、Bear フィルタ、BUY/SELL の冪等な書き込み）
- ニュース収集（RSS 取得、正規化、SSRF 対策、記事保存・銘柄抽出）
- マーケットカレンダー管理（営業日判定、前後営業日の取得）
- 監査ログ（signal_events / order_requests / executions 等）※監査用 DDL あり
- 共通統計ユーティリティ（Z スコア正規化等）

---

## 動作環境 / 前提

- Python 3.10 以上（PEP 604 の `X | None` 等で型記法を使用）
- 推奨パッケージ（最小限）:
  - duckdb
  - defusedxml

最小インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージをeditableでインストールする場合（setup.py/pyproject がある想定）
# pip install -e .
```

---

## 必要な環境変数

以下の環境変数を設定してください（`.env` または OS 環境変数）。パッケージの `kabusys.config.Settings` によって読み込まれます。プロジェクトルート（.git または pyproject.toml）を起点として自動的に `.env` / `.env.local` をロードします。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション等のパスワード（execution 連携用）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack 通知先チャネル ID

任意（デフォルトあり）:
- KABUSYS_ENV            : 実行環境 ("development" | "paper_trading" | "live")。デフォルト: development
- LOG_LEVEL              : ログレベル ("DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL")。デフォルト: INFO
- DUCKDB_PATH            : DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH            : 監視用 SQLite パス。デフォルト: data/monitoring.db

注意: Settings のプロパティは未設定時に ValueError を投げるものがあります（必須項目）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / コピー
2. Python 仮想環境を作成し activate
3. 必要パッケージをインストール
   - 例: pip install duckdb defusedxml
4. 環境変数を設定（`.env` をプロジェクトルートに作成）
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB スキーマを初期化
   - Python スクリプト例:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```
6. ETL 実行や戦略処理を行うスクリプトを実行

---

## 使い方（主要 API 例）

以下は代表的な利用例です。各モジュールは DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取る設計です。

- DuckDB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants から市場データを差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しないと today が対象
print(result.to_dict())
```

- 特徴量構築（strategy.feature_engineering）
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, target_date=date(2025, 1, 15))
print(f"features upserted: {n}")
```

- シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals

count = generate_signals(conn, target_date=date(2025, 1, 15), threshold=0.6)
print(f"signals written: {count}")
```

- ニュース収集ジョブ（RSS から raw_news / news_symbols への保存）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使用する有効銘柄コードのセット
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: saved_count, ...}
```

- マーケットカレンダー判定
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2025, 1, 15)
print("is trading day:", is_trading_day(conn, d))
print("next trading day:", next_trading_day(conn, d))
```

---

## 自動環境読み込みの挙動

- パッケージ import 時、`kabusys.config` がプロジェクトルートを探索し `.env` と `.env.local` を自動読み込みします（OS 環境変数が優先、`.env.local` は優先上書き）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- プロジェクトルートの検出基準: 現在ファイルの親ディレクトリで `.git` または `pyproject.toml` が見つかった場所。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 下の主要ファイルと簡単な説明です。

- __init__.py
  - パッケージエクスポート定義（data, strategy, execution, monitoring）
- config.py
  - 環境変数 / .env ロード、Settings クラス
- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py      : ETL パイプライン（run_daily_etl 等）
  - schema.py        : DuckDB スキーマ定義と init_schema
  - stats.py         : 統計ユーティリティ（zscore_normalize）
  - features.py      : data.stats の公開ラッパ
  - news_collector.py: RSS 収集・整形・DB 保存
  - calendar_management.py : カレンダー管理（is_trading_day 等）
  - audit.py         : 監査ログ DDL と初期化ロジック
  - (他: quality モジュール参照箇所あり — 品質チェック）
- research/
  - __init__.py
  - factor_research.py    : 各種ファクター計算（momentum / volatility / value）
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py: 生ファクターの正規化・ユニバースフィルタ・features テーブルへの UPSERT
  - signal_generator.py    : features + ai_scores 統合 → final_score → signals 書き込み
- execution/
  - __init__.py
  - （execution 層は分離されており、ここにブローカー連携実装を追加する想定）
- research/ と strategy/ の間は明確に分離：research はデータ探索・ファクター計算、strategy は本番向け特徴量処理とシグナル生成。

（リポジトリルートの pyproject.toml / .git 等に応じて .env 自動読み込みが行われます）

---

## 開発に関する注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス対策: 特徴量・シグナル計算は target_date 時点で入手可能なデータのみを使用する設計。
- 冪等性: DB への挿入は可能な限り ON CONFLICT / UPSERT を用いて冪等性を確保。
- ETL は差分更新（最終取得日ベース）と backfill を組み合わせ、API の後出し修正に対応。
- ニュース収集: SSRF 対策、受信サイズ上限、XML パースの安全化（defusedxml）などを実装。
- J-Quants クライアント: レートリミット制御、リトライ（指数バックオフ）、401 時のトークン自動更新を備える。

---

## 付録：よくある操作

- スキーマ再初期化（注意：既存データは維持されますが、ファイルや外部ステートに依存する操作は慎重に）
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")  # テスト用にインメモリ DB
```

- ログレベル設定（環境変数）
```bash
export LOG_LEVEL=DEBUG
```

---

README はコードベースの主要な操作・設計を簡潔にまとめたものです。より詳細な API レファレンスや運用手順（cron / CI での ETL スケジュール、Slack 通知、発注フローの実装方針など）は別途ドキュメントとして追加することを推奨します。必要であれば、各モジュールの関数一覧や具体的な CLI スクリプト例も作成します。どの情報を優先して追加しますか？
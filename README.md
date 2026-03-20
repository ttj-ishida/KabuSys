# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査用スキーマなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引のバックエンド機能を集約したライブラリです。主な目的は以下です。

- J-Quants API からの市場データ・財務データ取得と DuckDB への永続化（差分更新・冪等保存）
- データ品質チェック、マーケットカレンダー管理
- 研究用ファクター計算（momentum / volatility / value）と特徴量正規化
- 戦略シグナルのスコア計算および BUY/SELL シグナルの生成（冪等）
- RSS ベースのニュース収集と記事→銘柄紐付け
- 発注／約定／監査のためのスキーマ定義（監査ログのトレーサビリティ）

設計の要点：
- ルックアヘッドバイアスを避けるために target_date 時点のデータのみ使用
- DuckDB を中心に SQL + Python で処理を完結
- 冪等性（ON CONFLICT / INSERT DO UPDATE 等）とトランザクションで原子性を保証
- 外部依存は最小限（標準ライブラリ、duckdb、defusedxml など）

---

## 機能一覧

- データ取得・保存
  - J-Quants クライアント（jquants_client）: 日足、財務、マーケットカレンダーの取得（ページネーション・リトライ・レート制御・トークン自動更新）
  - raw データ保存（raw_prices, raw_financials, market_calendar 等）および冪等保存関数

- ETL / パイプライン
  - 差分更新（バックフィル対応）と日次 ETL 実行 run_daily_etl
  - 品質チェック（quality モジュール）を実行するフロー

- スキーマ管理
  - DuckDB スキーマ初期化 / 接続（init_schema / get_connection）
  - Raw / Processed / Feature / Execution のテーブル定義

- 特徴量・研究
  - factor_research: momentum / volatility / value の計算
  - research.feature_exploration: 将来リターン計算、IC（Spearman）、統計サマリー
  - data.stats: zscore_normalize（クロスセクション Z スコア正規化）

- 戦略
  - feature_engineering.build_features: 生ファクターを正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナル生成・signals テーブル保存

- ニュース収集
  - news_collector.fetch_rss / save_raw_news / run_news_collection: RSS からの収集、前処理、raw_news 保存、銘柄抽出・紐付け
  - SSRF・XML攻撃対策、レスポンスサイズ制限、トラッキングパラメータ除去等を実装

- カレンダー管理
  - market_calendar の差分更新（calendar_update_job）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）

- 監査（audit）
  - signal_events / order_requests / executions など監査用テーブルの定義と初期化方針

---

## セットアップ手順

前提
- Python >= 3.10（PEP 604 の `X | Y` 型注釈等を使用）
- pip と仮想環境の利用を推奨

推奨パッケージ（最低限）:
- duckdb
- defusedxml

例: 仮想環境の作成とパッケージインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発中はパッケージを editable インストール（プロジェクトルートに setup.cfg/pyproject.toml がある場合）
pip install -e .
```

環境変数（.env）
- 自動的にプロジェクトルートの `.env` と `.env.local` を読み込みます（CWD ではなくパッケージ位置からプロジェクトルートを探索）。
- 自動ロードを無効化する場合:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

必須の主要環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知に使用する場合
- SLACK_CHANNEL_ID: Slack 送信先チャンネル
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）
- KABUSYS_ENV: one of development|paper_trading|live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

例 `.env`（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

---

## 使い方（主要ワークフロー・例）

1) スキーマ初期化 / DB 接続
```python
from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ作成してテーブルを作る
# 既存 DB に接続する場合:
# conn = get_connection("data/kabusys.duckdb")
```

2) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ファーチャー（features）構築
```python
from kabusys.strategy import build_features
from datetime import date
n = build_features(conn, date.today())
print(f"built features for {n} codes")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date
total_signals = generate_signals(conn, date.today(), threshold=0.6)
print(f"generated {total_signals} signals")
```

5) ニュース収集と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使う有効な銘柄コードの集合（例: set(['7203','6758',...])）
results = run_news_collection(conn, known_codes=set(), timeout=30)
print(results)  # {source_name: saved_count, ...}
```

6) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved {saved} calendar entries")
```

その他ユーティリティ：
- research モジュールの各種解析関数（calc_forward_returns, calc_ic, factor_summary, rank）
- data.stats.zscore_normalize を直接利用可能

注意点:
- J-Quants API のレート制限（120 req/min）に合わせて内部で制御しています。
- HTTP エラー（408/429/5xx）やネットワーク障害に対して指数バックオフでリトライします。401 はリフレッシュトークンを使って自動更新を試みます（一回のみ）。
- DuckDB への書き込みは冪等化（ON CONFLICT）とトランザクションで保護しています。

---

## ディレクトリ構成

主要ファイル / ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（J-Quants トークン、Kabu API 設定、DBパス、環境種別）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py      — RSS 収集・前処理・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py               — zscore_normalize 等統計ユーティリティ
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — market_calendar 管理・営業日判定・calendar_update_job
    - features.py            — data.stats の公開ラッパ
    - audit.py               — 監査ログ（signal_events / order_requests / executions 等）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクターから features テーブル構築
    - signal_generator.py    — features + ai_scores からシグナル生成
  - execution/
    - __init__.py
    - （発注・execution 層は将来的に実装の想定）
  - monitoring/
    - （監視・アラート用のモジュールが入る想定）

README と実装はモジュール毎にドキュメント文字列（docstring）を多用しており、各関数・クラスの役割はソース内コメントを参照してください。

---

## 知っておくべき運用上のポイント / トラブルシューティング

- 環境変数の自動ロードは `.git` または `pyproject.toml` の位置を起点にプロジェクトルートを探索します（テスト時に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。
- DuckDB ファイルパスの親ディレクトリが無い場合、init_schema が自動作成します。
- J-Quants のリフレッシュトークンは必須（get_id_token により ID トークンを取得）。API 呼び出しで 401 を受け取った場合は自動でリフレッシュを試みます。
- news_collector は外部 RSS を取得するためネットワーク・SSRF・XML 攻撃対策を実装しています。フィード側の不正データや大容量レスポンスは安全側でスキップされます。
- generate_signals は features / ai_scores / positions テーブルを参照します。想定されるデータが存在しないと、BUY シグナルが発生しない／SELL 判定のみ行われる挙動になります。
- 本リポジトリは発注 API（ブローカー接続）への直接送信を含めない設計です。execution 層の実装を追加して実運用に接続してください。

---

## 参考（簡易コードスニペット）

DB 初期化 & 日次 ETL を CLI 風に実行する簡単な例:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
res = run_daily_etl(conn)
print(res.to_dict())
```

features とシグナル生成を夕方バッチで実行する例:
```python
from datetime import date
from kabusys.strategy import build_features, generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
d = date.today()
build_features(conn, d)
generate_signals(conn, d)
```

---

必要に応じて README を拡張して、セットアップの CI 手順、デバッグ手順、より詳細な API 仕様（関数別の引数説明例）や運用マニュアルを追加できます。どの追加情報が欲しいか教えてください。
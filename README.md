# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォームのコアライブラリです。  
DuckDB をデータレイクとして用い、J-Quants API からのデータ取得、ETL、特徴量計算、シグナル生成、ニュース収集、監査ログなどをモジュール化しています。

主な目的は「研究 → 特徴量化 → シグナル生成 → 実行（発注）」というフローを安全かつ冪等に実行できる基盤を提供することです。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 依存ライブラリ
- 環境変数（設定）
- セットアップ手順
- 使い方（簡単なサンプル）
- ディレクトリ構成（主なファイル説明）
- 備考 / 注意点

---

## プロジェクト概要

- DuckDB をバックエンドに用いたデータレイヤー（raw / processed / feature / execution）を定義・初期化するスキーマを提供します。
- J-Quants API クライアント（レートリミット・リトライ・トークンリフレッシュ対応）で株価・財務・カレンダーを取得して DuckDB に保存します。
- 研究用モジュールでファクター（モメンタム/ボラティリティ/バリュー 等）を計算し、Zスコア正規化して特徴量テーブルに保存する機能を備えます。
- 正規化済み特徴量と AI スコアを統合して最終スコアを算出し、BUY/SELL シグナルを生成して signals テーブルへ格納します。
- RSS を使ったニュース収集モジュール（SSRF対策、トラッキングパラメータ除去、記事IDは正規化URLのSHA-256先頭32文字）を備えます。
- ETL パイプライン、カレンダー管理、監査ログ用テーブル等、運用に必要なユーティリティを備えています。

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB へ冪等に保存する save_* 関数
- ETL
  - 差分更新（backfill 対応）、日次 ETL ジョブ（run_daily_etl）
  - 市場カレンダー更新ジョブ（calendar_update_job）
- データスキーマ
  - raw_prices, raw_financials, prices_daily, features, ai_scores, signals, orders, trades, positions, など多数のテーブル定義
  - init_schema() による初期化
- 研究 / ファクター
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - Zスコア正規化ユーティリティ
  - 将来リターン計算、IC 計算、ファクターサマリー
- 特徴量構築・シグナル
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)
- ニュース収集
  - RSS フィード取得（SSRF対策、gzip対応、サイズ上限）
  - raw_news / news_symbols への保存（冪等）
- 監査ログ
  - signal_events / order_requests / executions 等の監査テーブル定義

---

## 前提条件 / 依存ライブラリ

最低限の動作に必要な Python パッケージ（例）:

- Python 3.8+（コードは型注釈に Optional/| を使用しているため 3.10+ が望ましい）
- duckdb
- defusedxml

インストール例:
pip install duckdb defusedxml

（実際の運用では logging、テスト、Slack 通知、HTTP クライアント等の追加パッケージが必要になる場合があります）

---

## 環境変数（主な設定）

アプリケーション設定は環境変数または .env ファイルから読み込むようになっています。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（無効化可）。

必須（runtime に必須）:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API パスワード
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV            — 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL              — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

自動 .env 読み込みの挙動:
- プロジェクトルートはこのパッケージのファイル位置から .git または pyproject.toml を探索して決定します。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時等）。

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置する
2. Python 環境を作成（推奨: venv / pyenv / conda）
   - python -m venv .venv
   - source .venv/bin/activate
3. 必要なパッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて logging/requests 等を追加）
4. 環境変数を設定（.env をプロジェクトルートに置くか OS 環境に設定）
5. DuckDB スキーマを初期化
   - 以下のサンプルを参照して init_schema を実行

---

## 使い方（簡単なサンプル）

以下は Python REPL からの簡単な利用例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は環境変数で上書き可能
```

2) 日次 ETL 実行（J-Quants からの差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定することも可
print(result.to_dict())
```

3) 特徴量のビルド
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date(2024, 1, 15))
print(f"features upserted: {count}")
```

4) シグナルの生成
```python
from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, target_date=date(2024, 1, 15))
print(f"signals written: {total}")
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(res)
```

注意:
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。運用ではコネクション管理（接続の寿命、排他制御）を適切に行ってください。
- J-Quants の API 利用にはトークンが必要です（settings.jquants_refresh_token）。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールと簡単な説明です。ソースは `src/kabusys` 以下にあります。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得/保存ユーティリティ）
    - schema.py                 — DuckDB スキーマ定義 & init_schema()
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - news_collector.py         — RSS 取得・記事保存・銘柄抽出
    - calendar_management.py    — カレンダー管理ユーティリティ
    - features.py               — data.stats の再エクスポート
    - audit.py                  — 監査ログ用スキーマ
    - ...（quality 等の補助モジュールが想定される）
  - research/
    - __init__.py
    - factor_research.py        — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py    — 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py    — build_features
    - signal_generator.py       — generate_signals
  - execution/                  — 発注 API との接続や実行ロジック用（空パッケージ）
  - monitoring/                 — 監視/監査系（別途実装想定）

（README は主要ファイルのみを抜粋しています。詳細は各モジュールの docstring を参照してください）

---

## 備考 / 注意点

- 自動の .env 読み込みはプロジェクトルート (.git または pyproject.toml を基準) を探索して行われます。テスト時などで自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を設定してください。
- J-Quants に対する API レート制限（120 req/min）やリトライポリシー、401 時のトークン自動リフレッシュ等を実装済みです。ただし運用環境ではネットワーク障害や API 仕様変更に注意してください。
- DuckDB スキーマは多数の制約やインデックスを含みます。運用で DuckDB バージョンや制約の互換性に注意してください（README 内のスキーマ定義は DuckDB 1.5.x 系で想定した記述が含まれます）。
- シグナル生成や発注ロジックは設計に注意が必要です。ルックアヘッドバイアス防止のため、すべて target_date 時点のデータのみを参照する方針が採られています。
- 実際の実運用で証券会社 API（kabuステーション等）へ接続する場合は、追加の安全対策（接続認証、テスト環境での十分な検証、注文の冪等性確認、監査ログの永続化）を行ってください。

---

もし README に追加したい内容（例: CI / テスト手順、より詳細な運用手順、サンプル .env.example、要求される Python バージョンの明記など）があれば教えてください。必要に応じて追記します。
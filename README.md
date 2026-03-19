# KabuSys

日本株向け自動売買プラットフォームのプロトタイプ実装です。  
データ取得（J-Quants）、ETL、データ品質チェック、特徴量生成、リサーチユーティリティ、ニュース収集、監査ログなどを含むモジュール群を含みます。発注やストラテジー実行のための基盤を提供することを目的としています。

---

## プロジェクト概要

KabuSys は、日本株のデータ収集と特徴量生成を中心に、戦略開発・検証・本番運用までの基礎機能を提供するライブラリ群です。主な設計方針は以下の通りです。

- DuckDB を中心にローカル DB にデータを永続化（冪等な保存を重視）
- J-Quants API からの差分取得（レート制御・リトライ・トークン自動更新対応）
- ETL は差分更新・バックフィル・品質チェックをサポート
- Research 用ユーティリティ（ファクター計算、IC 計算、統計サマリー）
- ニュース収集（RSS）および銘柄抽出、DB 保存
- 監査（audit）用テーブル群によりシグナル→発注→約定のトレーサビリティを保証

パッケージ名: `kabusys`  
現在のバージョン: 0.1.0

---

## 機能一覧

- 環境設定読み込み（`.env` / 環境変数、自動ロード機能）
- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得
  - レートリミット、リトライ、IDトークン自動更新対応
  - DuckDB への冪等保存ユーティリティ
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル
- ETL パイプライン
  - 日次差分 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別ジョブ（prices / financials / calendar）の実行補助
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- ニュース収集（RSS）
  - URL 正規化・トラッキングパラメータ除去・SSRF 対策・gzip 対応
  - raw_news / news_symbols への冪等保存
- Research ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算 / IC（Spearman） / ファクター統計サマリー
  - Z-score 正規化ユーティリティ
- 監査ログ（signal_events / order_requests / executions）初期化補助
- カレンダー管理（営業日判定・次/前営業日取得・カレンダー更新ジョブ）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の `X | None` 表記を使用）
- DuckDB が必要（python パッケージとして利用）

1. リポジトリをクローン / パッケージを設置
   - 開発中はプロジェクトルートで `pip install -e .` を使うと便利です。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 最低限:
     - duckdb
     - defusedxml
   - 例:
     pip install duckdb defusedxml

   （将来的に Slack 通知などを追加する場合は追加パッケージが必要になります）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（CWD ではなくソースファイル位置からプロジェクトルートを探索）。
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（Settings 経由で参照／未設定時は ValueError）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション等の API パスワード（使用モジュールによる）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID : Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV : development / paper_trading / live （default: development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL （default: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite のパス（default: data/monitoring.db）

例 .env:
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## 使い方（代表的なスニペット）

※ 下のサンプルは基本的な呼び出し例です。実運用ではログ設定や例外処理、認証トークン管理を適切に行ってください。

- DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルの親ディレクトリは自動作成されます
```

- 監査ログ DB 初期化（監査用に別 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

- 日次 ETL 実行

```python
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn)  # target_date を指定しないと今日を使います
print(res.to_dict())
```

- 個別 ETL ジョブ（例: 株価のみ）

```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl

fetched, saved = run_prices_etl(conn, target_date=date(2025, 1, 1))
```

- ニュース収集（RSS）

```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出でフィルタに使う既知コード集合
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- Research / ファクター計算（例: モメンタム）

```python
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

momentum = calc_momentum(conn, date(2025, 1, 1))
fwd = calc_forward_returns(conn, date(2025, 1, 1))
ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
print(ic)
```

- J-Quants からデータを直接取得して保存（テスト・開発用）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,10))
saved = save_daily_quotes(conn, records)
print("saved", saved)
```

- カレンダー関連ユーティリティ

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

print(is_trading_day(conn, date(2025,1,1)))
print(next_trading_day(conn, date(2025,1,1)))
```

---

## 知っておくべき仕様・挙動

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` / `.env.local` を読み込みます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants クライアントは 120 req/min のレート制御を組み込んでいます。大量取得時は時間がかかる点に注意してください。
- DuckDB への保存は各 save_* 関数で ON CONFLICT を利用した冪等な実装となっています。
- ニュース収集は RSS をパースして記事ID を URL 正規化→SHA256（先頭32文字）で生成し、重複挿入を防いでいます。SSRF 対策や受信サイズ制限が組み込まれています。
- Research モジュールは本番の発注 API にアクセスしません（DuckDB の prices_daily / raw_financials のみ参照）。
- Quality チェックは Fail-Fast ではなく全チェックを実行して問題一覧を返します。ETL は問題があっても継続する設計（呼び出し側で判断）。

---

## ディレクトリ構成

主要なファイル / モジュールは以下の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py               — RSS ニュース収集 / 保存 / 銘柄抽出
    - schema.py                       — DuckDB スキーマ定義・初期化
    - pipeline.py                     — ETL パイプライン（差分更新・日次ETL）
    - features.py                     — 特徴量ユーティリティ公開
    - calendar_management.py          — マーケットカレンダー管理・判定
    - audit.py                        — 監査ログ（signal/order/execution）初期化
    - etl.py                          — ETL 結果クラスの公開
    - quality.py                      — データ品質チェック
    - stats.py                        — 統計ユーティリティ（zscore 等）
  - research/
    - __init__.py
    - feature_exploration.py          — 将来リターン・IC・summary 等
    - factor_research.py              — Momentum/Volatility/Value 等ファクター計算
  - strategy/                          — 戦略層（雛形、拡張用）
  - execution/                         — 発注 / ブローカー連携用モジュール（雛形）
  - monitoring/                        — 監視・メトリクス関連（雛形）

---

## 開発・運用上の注意

- 本リポジトリはプロトタイプであり、本番運用前にリスク管理・例外ハンドリング・セキュリティ監査を行ってください。
- 実際の発注・約定処理を組み込む場合は、冪等性・二重発注防止・監査ログの完全性を最優先で実装してください。
- API トークンやパスワードは必ず安全に管理し、リポジトリやログに書き出さないでください。

---

必要があれば README に含めるサンプル `.env.example`、CI 用の初期化スクリプト、さらに詳細な API リファレンスやユースケース（データバックフィル、戦略検証フロー等）を追記します。どの項目を充実させたいか教えてください。
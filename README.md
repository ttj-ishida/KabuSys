# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB をデータレイクとして用い、J‑Quants API から市場データ・財務データ・マーケットカレンダーを取得・保存し、戦略向けの特徴量計算・ETL・品質チェック・ニュース収集・監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要な利用例）
- 環境変数（主要な設定）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J‑Quants API から市場データ・財務データ・カレンダーを安全に取得するクライアント
- DuckDB を用いたデータスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース（RSS）収集と記事 → 銘柄コード紐付け
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と IC / 統計サマリ
- 発注監査ログ用スキーマ（tracing 用テーブル群）

設計上のポイント:
- DuckDB を中心に SQL + Python で効率良く処理
- 外部 API 呼び出しは専用クライアントで一元化（レート制御・リトライ・トークン自動更新）
- ETL・収集処理は冪等（INSERT ... ON CONFLICT）を前提
- セキュリティ対策（RSS の SSRF 対策や XML 攻撃対策など）を実装

---

## 機能一覧

主要機能の抜粋:

- data/jquants_client
  - J‑Quants API クライアント（レートリミット・リトライ・token自動更新）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存ユーティリティ（save_*）
- data/schema
  - DuckDB 用スキーマ定義（raw_prices, prices_daily, features, orders, executions, audit 系など）
  - init_schema(db_path) で DB 初期化
- data/pipeline
  - 日次 ETL 実行 run_daily_etl（差分取得、バックフィル、品質チェック）
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
- data/quality
  - 欠損・スパイク・重複・日付不整合などの品質チェック（run_all_checks）
- data/news_collector
  - RSS 取得（gzip 対応、XML パース保護、SSRF 対策）
  - raw_news 保存、news_symbols の紐付け
  - run_news_collection で複数ソース一括収集
- research/*
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary, rank（研究用）
- data/stats
  - zscore_normalize（クロスセクション Z スコア正規化）
- data/calendar_management
  - market_calendar を元にした営業日判定・next/prev_trading_day 等
- data/audit
  - 監査ログのためのテーブル群・初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提: Python 3.9+（typing の | 型表記が使われているため）、および以下のパッケージが必要です。

必須パッケージ例:
- duckdb
- defusedxml

インストール例（仮にパッケージをローカルで開発する場合）:

```
pip install duckdb defusedxml
# パッケージをローカルにインストールする場合
pip install -e .
```

.env の準備:
- プロジェクトルート（.git または pyproject.toml を置いたディレクトリ）に `.env` / `.env.local` を置くことで環境変数を自動読み込みします（コード内で自動ロード処理あり）。  
- テスト等で自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

データベース初期化の例（DuckDB ファイルを作成）:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

監査用 DB を別途作る場合:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方

以下は主要な利用例です。すべて Python API を通して呼びます。

1) 設定（必須の環境変数を .env に設定）

必須の主要環境変数（後述のセクションも参照）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

2) DB 初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

db_path = settings.duckdb_path  # デフォルト: data/kabusys.duckdb
conn = init_schema(db_path)
```

3) 日次 ETL 実行（J‑Quants から差分取得して保存、品質チェックまで）

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

4) ニュース収集（RSS）

```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードの集合（抽出用）
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count}
```

5) 研究用ファクター計算

```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

d = date(2024, 1, 4)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# 例: zscore 正規化
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

6) カレンダー操作（営業日判定）

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_trade = is_trading_day(conn, date(2024, 1, 4))
next_trade = next_trading_day(conn, date(2024, 1, 4))
```

注意点:
- J‑Quants API 呼び出しはレート制限（120 req/min）やリトライが内部で適用されます。
- fetch 関数はページネーションに対応しています。
- 保存関数は冪等性を考慮し ON CONFLICT / DO UPDATE を利用します。

---

## 環境変数（主要）

自動読み込みの挙動:
- パッケージ起点で `.git` もしくは `pyproject.toml` のある親ディレクトリを探索し、`.env` と `.env.local` を読み込みます（OS 環境変数 > .env.local > .env の優先度）。
- 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン

- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)

- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)

- データベース
  - DUCKDB_PATH (省略可, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (省略可, デフォルト: data/monitoring.db)

- システム
  - KABUSYS_ENV (development | paper_trading | live) — 動作モード
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

その他:
- .env.example を参考に .env を作成してください（未設定で必須項目がない場合、Settings プロパティ呼び出しで ValueError が発生します）。

---

## ディレクトリ構成

リポジトリ内の主要なファイル／モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py      — J‑Quants API クライアント / 保存ユーティリティ
    - news_collector.py      — RSS 取得・前処理・DB 保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py               — zscore_normalize 等
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — features 公開インターフェース（再エクスポート）
    - calendar_management.py — market_calendar 関連ユーティリティ・バッチ
    - audit.py               — 監査ログ用スキーマ（signal_events / order_requests / executions）
    - etl.py                 — ETLResult 再エクスポート
    - quality.py             — データ品質チェック
  - research/
    - __init__.py            — 研究用 API の公開（calc_momentum 等）
    - feature_exploration.py — forward returns / IC / summary
    - factor_research.py     — momentum / volatility / value 計算
  - strategy/                — 戦略関連（未実装ファイル群の入口）
  - execution/               — 発注関連（未実装ファイル群の入口）
  - monitoring/              — 監視関連（入口だけ）

（上記は現行コードベースの主要ファイル群です）

---

## 開発・運用上の注意

- DuckDB バイナリは pip で提供されますが、OS による差異がある場合があるため CI や実環境での確認を推奨します。
- news_collector は外部ネットワークアクセスを行うため、運用環境ではプロキシ・ネットワークポリシーに注意してください。SSRF 対策・受信サイズ制限・defusedxml による XML 攻撃対策が組み込まれています。
- ETL は差分更新を行いますが、初回は過去分を一括で取得する設計です（_MIN_DATA_DATE = 2017-01-01 がデフォルトの起点）。
- 監査ログ（audit）スキーマは UTC タイムゾーンを前提としています（init_audit_schema 実行時に SET TimeZone='UTC' が行われます）。
- 本コードベースは発注 API と直接やりとりするコンポーネントは分離されています（execution パッケージなど）。本番発注（live）運用では安全冗長・フェイルセーフの設計が必要です。

---

## サンプル: よく使うワークフロー

1. 環境変数を .env に用意（JQUANTS_REFRESH_TOKEN 等）
2. DB 初期化
3. 日次 ETL を実行（スケジューラで毎晩）
4. ETL 結果を確認後、特徴量計算 → シグナル生成 → 発注（監査ログに記録）

短い例:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
res = run_daily_etl(conn)
print(res.to_dict())
```

---

必要に応じて README にサンプル .env.example、より詳細な API ドキュメント、CI / テストの手順、パッケージング（pyproject.toml）やリリース手順を追加できます。追加して欲しいセクションがあれば教えてください。
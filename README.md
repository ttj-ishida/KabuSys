# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
DuckDB をデータレイクとして用い、J-Quants API などからのデータ収集（ETL）、品質チェック、特徴量計算、ニュース収集、監査ログなどを提供します。戦略／発注層との接続ポイントを想定したモジュール設計です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要な例）
- 環境変数（設定項目）
- 自動 .env ロードについて
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

KabuSys は以下を目的とする Python パッケージです。

- J-Quants からの株価日足・財務・カレンダー取得と DuckDB への保存（冪等保存）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース（RSS）収集と記事→銘柄紐付け
- ファクター（モメンタム／ボラティリティ／バリュー等）計算や IC・統計サマリーなどの研究ユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ定義
- マーケットカレンダー管理、取引日の判定ユーティリティ

設計方針として、DuckDB による SQL ベースの処理を基本とし、外部依存を最小化（pandas 等には依存しない）しています。API 呼び出しはレート制限・リトライ・トークン自動リフレッシュなど耐障害性を考慮しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - 環境変数管理・自動 .env 読み込み・必須キー取得
- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション、レート制御、リトライ、ID トークン管理）
  - schema: DuckDB スキーマ定義 / init_schema
  - pipeline / etl: ETL 実行（run_daily_etl 等）
  - news_collector: RSS 取得・前処理・冪等保存・銘柄抽出
  - calendar_management: JPX カレンダー更新、取引日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用スキーマ初期化（signal_events, order_requests, executions）
  - stats: z-score 正規化ユーティリティ
- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー ファクター計算
  - feature_exploration: 将来リターン計算(calc_forward_returns)、IC(calc_ic)、統計サマリー
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - 発注やモニタリング用の名前空間（実装拡張前提）

---

## セットアップ手順

前提
- Python 3.10 以上（| 型注釈などを使用）
- Git（ソース管理）

推奨パッケージ（最低限）
- duckdb
- defusedxml

例: 仮想環境を作って依存をインストールする
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# ローカル開発ならパッケージを editable インストール
pip install -e .
```

（requirements.txt / pyproject.toml があればそちらに従ってください）

---

## 環境変数（必須／任意）

Settings クラスで参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（発注層で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルト有り）:
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")、デフォルト "development"
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)、デフォルト "INFO"
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると自動 .env ロードを無効化
- KABUSYS_ENV
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite 等のパス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabuapi のベース URL（デフォルト: http://localhost:18080/kabusapi）

例 .env（プロジェクトルートに置く）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動読み込み: .env, .env.local（OS 環境変数が優先）。プロジェクトルートは .git または pyproject.toml を基準に探索します。

---

## 使い方（主要な例）

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

2) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_dateを与えなければ今日
print(result.to_dict())
```

3) 個別 ETL（差分更新）例
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
from datetime import date

d = date(2026, 3, 1)
fetched, saved = run_prices_etl(conn, d)
```

4) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄コードセット（抽出に使用）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # sourceごとの新規保存件数
```

5) ファクター計算 / 研究ユーティリティ
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

from datetime import date
d = date(2026, 3, 1)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# 将来リターンの計算
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])

# IC の計算（例）
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

6) J-Quants API を直接叩いてデータ取得・保存
```python
from kabusys.data import jquants_client as jq
from datetime import date

# データ取得
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
# 保存（raw_prices テーブルに冪等で保存）
saved = jq.save_daily_quotes(conn, records)
```

7) 監査ログ用スキーマの初期化
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

---

## 自動 .env ロードについて

- デフォルトでプロジェクトルート（.git もしくは pyproject.toml のあるディレクトリ）を起点に `.env` と `.env.local` を読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local (override=True) > .env
- テスト等で自動ロードを抑制したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパース挙動:
- export VAR=val 形式に対応
- クォート付き文字列のエスケープ対応
- 行末コメントやトラッキングなどを考慮した実装

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージ宣言 / __version__

- src/kabusys/config.py
  - 環境変数読み込み・Settings（必須キー取得・env/log レベル判定）

- src/kabusys/data/
  - jquants_client.py — J-Quants API クライアント（fetch/save 関数・レート制御・リトライ）
  - news_collector.py — RSS 取得・前処理・raw_news 保存・銘柄抽出・run_news_collection
  - schema.py — DuckDB のスキーマ定義と init_schema/get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl, ...）
  - etl.py — ETLResult の公開インターフェース
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management.py — カレンダー更新ジョブ、取引日判定ユーティリティ
  - audit.py — 監査ログ（signal_events, order_requests, executions）スキーマ初期化
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - features.py — data.stats の再エクスポート

- src/kabusys/research/
  - feature_exploration.py — 将来リターン、IC、要約統計
  - factor_research.py — momentum / volatility / value の計算
  - __init__.py — 主要ユーティリティの再エクスポート

- src/kabusys/strategy/ (空の __init__ あり)
- src/kabusys/execution/ (空の __init__ あり)
- src/kabusys/monitoring/ (空の __init__ あり)

---

## 注意事項 / 実運用上のポイント

- J-Quants API レート制限（120 req/min）に従う実装がありますが、運用では API の利用制限や認証情報の保護に注意してください。
- DuckDB のバージョンによってサポートされる機能（外部キーの ON DELETE オプションなど）が異なるため、DDL コメントに注意して下さい。
- ETL は Fail-Fast ではなく「問題を収集して報告する」設計です。quality チェックの結果は ETLResult.quality_issues で参照できます。
- production（本番）での発注・約定処理を行う場合は、KABUSYS_ENV を適切に設定し（例えば "live"）、発注層（execution モジュール）を実装・テストした上で運用してください。

---

必要な追加ドキュメントや「strategy の実装例」「運用ガイド（cron/airflow 用）」などがあれば続けて作成します。どの部分を詳しく書いてほしいか教えてください。
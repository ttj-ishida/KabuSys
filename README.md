# KabuSys

日本株向けの自動売買 / データ平台ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、特徴量計算、研究用ユーティリティ、監査ログなどを備え、戦略開発から発注監査まで一貫してサポートします。

---

## プロジェクト概要

KabuSys は以下の機能群を持つモジュール群で構成されています。

- データ取得・保存（J-Quants API クライアント、RSS ニュース収集）
- DuckDB スキーマ定義と初期化、ETL パイプライン
- データ品質チェック（欠損、重複、スパイク、日付不整合 等）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ 等）と特徴量探索（IC、前方リターンなど）
- 統計ユーティリティ（Z スコア正規化など）
- 監査ログ（シグナル→発注→約定までのトレーサビリティ）
- 環境変数管理（.env 自動読み込み、必須変数チェック）

本コードベースは本番の発注処理を含む層（execution / strategy / monitoring）を想定しつつも、データ層・研究層は本番 API を実行せずに安全に使える設計になっています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API との通信（レート制限、リトライ、ID トークン自動リフレッシュ、ページネーション対応）
  - データ保存（raw_prices / raw_financials / market_calendar など）を冪等に保存（ON CONFLICT）
- data/news_collector.py
  - RSS からニュースを収集、前処理、DuckDB に冪等保存、銘柄抽出と紐付け
  - SSRF 対策、受信サイズ制限、XML セキュリティ対策を実装
- data/schema.py / data/audit.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - 初期化ユーティリティ（init_schema, init_audit_db 等）
- data/pipeline.py / data/etl.py
  - 差分取得に基づく ETL（run_daily_etl、個別 ETL ジョブ）
  - 品質チェックの実行と結果集約（ETLResult）
- data/quality.py
  - 欠損検出・重複・スパイク・日付不整合チェック
- data/stats.py / data/features.py
  - zscore_normalize 等の汎用統計ユーティリティ
- research/factor_research.py / research/feature_exploration.py
  - ファクター計算（モメンタム・ボラティリティ・バリュー）と IC / forward returns / summary
- config.py
  - 環境変数の読み込み (.env / .env.local 自動ロード) と必須設定チェック
  - settings オブジェクト経由で設定取得
- monitoring / strategy / execution
  - パッケージインターフェースを分離（実装は別途追加）

---

## セットアップ手順

前提: Python 3.9+（typing の union 等を利用）を想定しています。必要に応じて環境を調整してください。

1. リポジトリをクローン / コピー

   git clone <repo-url>
   cd <repo>

2. Python 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）

4. 環境変数の設定

   以下の主要な環境変数を設定してください（.env ファイルをプロジェクトルートに置くと自動読み込みされます）。

   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
   - KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
   - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
   - SLACK_CHANNEL_ID (必須) — 通知先チャンネル ID
   - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
   - KABUSYS_ENV (任意) — 値: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   自動 .env ロードの仕様:
   - プロジェクトルートは .git または pyproject.toml を基準に探索
   - 自動ロードは OS 環境変数（優先） > .env.local > .env の順で行われます
   - テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

5. DuckDB スキーマ初期化（例）

   以下は Python REPL またはスクリプトで実行します：

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

   監査ログ専用 DB を初期化する場合:

   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（代表的な例）

設定参照:

from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト

DuckDB スキーマ初期化:

from kabusys.data import schema
conn = schema.init_schema(settings.duckdb_path)

日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）:

from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を渡せばその日を対象に実行
print(result.to_dict())

ニュース収集ジョブ（RSS 取り込み）:

from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758"}  # 例: 有効銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)

研究用途のファクター計算（例: モメンタムと IC）:

from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
conn = duckdb.connect(str(settings.duckdb_path))
target = date(2025, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
print(ic, summary)

J-Quants API からの直接フェッチ（ページネーション・トークン自動リフレッシュ対応）:

from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
# 保存は save_daily_quotes を使う

品質チェックを個別に実行:

from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=target)
for i in issues:
    print(i)

注意点 / 実装挙動のリマインド:
- jquants_client は 120 req/min のレート制限を意識しており、モジュール内でスロットリングとリトライを行います。
- 401 を受けた場合、refresh token を使って id_token の再取得を試み、1 回だけ再トライします。
- ニュース収集は SSRF、XML Bomb、gzip 展開上限などのセキュリティ保護を実装しています。
- ETL の保存は ON CONFLICT（冪等）で処理します。

---

## ディレクトリ構成

以下は主要ファイルと役割の一覧（簡略化）:

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込みと settings オブジェクト
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存）
  - news_collector.py — RSS ニュース収集・前処理・保存
  - schema.py — DuckDB スキーマ定義と init_schema
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETL 公開インターフェース（ETLResult 再エクスポート）
  - quality.py — データ品質チェック
  - stats.py — 統計ユーティリティ（zscore_normalize 等）
  - features.py — 特徴量関連の公開インターフェース
  - calendar_management.py — カレンダー管理/判定/更新ジョブ
  - audit.py — 監査ログ用スキーマと初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — 将来リターン計算・IC 計算・サマリー
- strategy/
  - __init__.py  （戦略実装プレースホルダ）
- execution/
  - __init__.py  （発注実装プレースホルダ）
- monitoring/
  - __init__.py  （監視実装プレースホルダ）

各モジュールの詳細は該当ファイルの docstring（冒頭コメント）に設計方針や注意点が記載されています。まずは data/schema.init_schema で DB を初期化してから、pipeline.run_daily_etl や news_collector.run_news_collection を順に実行するのが基本的な利用フローです。

---

## 開発・拡張のヒント

- settings はプロパティベースで必須値のチェックを行うため、起動前に必要な環境変数を設定してください。
- DuckDB のパスを変えれば環境（本番 / ステージング / テスト）ごとに分離できます（設定: DUCKDB_PATH）。
- research モジュールは標準ライブラリと duckdb のみで動くよう設計されており、外部依存を最小化しています。高速化や大規模化する場合は pandas 等の導入を検討してください。
- 発注・監視ロジック（kabu API 等）は execution / strategy 配下に実装していく想定です。監査ログ（audit）との整合を意識して実装してください。

---

もし README に追記したい「コマンドラインツール」「CI 設定」「デプロイ手順」「単体テスト例」などがあれば、その要件を教えてください。具体的な利用例（cron ジョブ、Dockerfile、systemd ユニットなど）も必要であれば作成します。
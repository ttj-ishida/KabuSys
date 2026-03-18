# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）のリポジトリ向け README。  
本ドキュメントはソースコード（src/kabusys 以下）に基づき、プロジェクト概要、機能、セットアップ、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・データ基盤を目的としたライブラリ群です。  
主に以下の領域に機能を提供します。

- J-Quants 等の外部 API からのデータ取得（株価日足、財務データ、マーケットカレンダー）
- DuckDB を用いたデータスキーマと永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策、サイズ制限、トラッキング除去）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリューなど）と評価（IC）
- 発注・監査ログ領域のスキーマ（発注要求・約定・監査トレース）

設計方針として、本番発注 API に直接アクセスしないモジュール（data/research 等）は外部 API に依存せずに DuckDB と標準ライブラリで解析できるようにしています。ETL / API クライアントはレート制限・リトライ・トークンリフレッシュ等を組み込み、冪等性を考慮した保存処理を提供します。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
- Data レイヤ
  - J-Quants クライアント（fetch/save: prices, financials, market calendar）
  - DuckDB スキーマ定義と初期化 (`data.schema.init_schema`)
  - ETL パイプライン（日次 ETL, 差分取得、バックフィル、品質チェック）
  - ニュース収集（RSS→raw_news、記事ID正規化、SSRF対策、銘柄抽出）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- Research（調査・特徴量）
  - momentum / volatility / value のファクター計算
  - 将来リターン計算（forward returns）と IC（Spearman ρ）
  - z-score 正規化ユーティリティ
- Execution / Audit（スキーマ）
  - シグナル・発注要求・約定・ポジション・パフォーマンスなどのテーブル定義
  - 監査ログテーブル（signal_events / order_requests / executions）初期化ユーティリティ
- News collector
  - トラッキングパラメータの除去、URL正規化、記事ID生成、銘柄抽出

---

## 前提・依存関係

最小限の依存パッケージ（コード参照）：

- duckdb
- defusedxml

（その他は標準ライブラリのみで実装されている箇所が多いですが、実行環境により追加ライブラリが必要になる場合があります。）

インストール例（仮に pyproject.toml または setup がある前提）:

- 開発環境（推奨）
  - python 3.9+（ソース内アノテーション等に依存）
  - 仮想環境作成:
    - python -m venv .venv
    - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
  - 必要パッケージのインストール:
    - pip install duckdb defusedxml
  - （プロジェクト全体を editable インストールできる場合）
    - pip install -e .

---

## 環境変数（主なもの）

プロジェクトは .env / .env.local をプロジェクトルートから自動読み込みします（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。

重要な環境変数（一部）:

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注関連で使用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。不正値は例外。
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

.env 例（.env.example を参照して作成）:
KEY=VALUE の形式で定義してください。export 前置やクォートされた値にも対応しています。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに pyproject.toml がある場合は pip install -e . で開発インストール）

4. 環境変数を準備
   - プロジェクトルートに .env または .env.local を作成（.env.example を参考）
   - 必須変数を設定（JQUANTS_REFRESH_TOKEN 等）

5. DuckDB スキーマ初期化
   - Python REPL / スクリプトから init_schema を実行（下記参照）

---

## 使い方（代表的な例）

※ 各コードスニペットは実行例です。実運用では十分なログ/例外処理を追加してください。

1) DuckDB スキーマ初期化（初回）

Python スクリプト/REPL で:

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn を以降の処理で使う

2) 日次 ETL を実行（カレンダー・株価・財務・品質チェック）

from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())

3) ニュース収集を実行（RSS → raw_news、銘柄紐付け）

from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "6501"}  # 既知銘柄セット（実運用では全銘柄セット）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count}

4) J-Quants から特定銘柄の日足を取得して保存（直接利用）

from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,12,31))
saved = jq.save_daily_quotes(conn, records)
print(f"fetched={len(records)} saved={saved}")

5) ファクター計算（Research）

from kabusys.data.schema import get_connection, init_schema
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = init_schema("data/kabusys.duckdb")
# 例: ある営業日を target_date にしてモメンタムを計算
from datetime import date
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 将来リターンを計算し IC を出す例
fwd = calc_forward_returns(conn, target, horizons=[1,5])
# calc_ic は factor_records, forward_records を code キーで結合して Spearman ρ を計算
# 例: factor_col="mom_1m", return_col="fwd_1d"
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

---

## 設定の自動ロード挙動

- kabusys.config モジュールは .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動的にロードします。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定値取得のために、`from kabusys.config import settings` のようにして各種プロパティ（settings.jquants_refresh_token など）を参照できます。
- 必須項目が未設定の場合は settings のプロパティアクセス時に ValueError が送出されます。

---

## よく使う API（抜粋）

- data.schema.init_schema(db_path) -> DuckDB 接続を作成・テーブル作成
- data.schema.get_connection(db_path) -> 既存 DB への接続（スキーマ初期化は行わない）
- data.jquants_client.fetch_daily_quotes(...)
- data.jquants_client.fetch_financial_statements(...)
- data.jquants_client.save_daily_quotes(conn, records)
- data.pipeline.run_daily_etl(conn, target_date=None, ...)
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- research.calc_momentum(conn, target_date)
- research.calc_volatility(conn, target_date)
- research.calc_value(conn, target_date)
- research.calc_forward_returns(conn, target_date, horizons=[1,5,21])
- research.calc_ic(factor_records, forward_records, factor_col, return_col)
- data.stats.zscore_normalize(records, columns)

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                           — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py                  — J-Quants API クライアント（fetch/save）
  - news_collector.py                  — RSS ニュース収集・DB 保存
  - schema.py                          — DuckDB スキーマ定義 / init_schema
  - pipeline.py                        — ETL パイプライン（run_daily_etl 等）
  - features.py                        — 特徴量公開インターフェース（zscore）
  - stats.py                           — 統計ユーティリティ（z-score 等）
  - calendar_management.py             — マーケットカレンダー管理（営業日判定 etc）
  - audit.py                           — 監査ログテーブル初期化ユーティリティ
  - etl.py                             — ETL 公開インターフェース（ETLResult 再エクスポート）
  - quality.py                         — データ品質チェック
- research/
  - __init__.py
  - factor_research.py                 — ファクター計算（momentum, volatility, value）
  - feature_exploration.py             — 将来リターン・IC・統計サマリー
- strategy/
  - __init__.py                        — 戦略関連モジュール配置場所（実装は各自）
- execution/
  - __init__.py                        — 発注関連モジュール配置場所（実装は各自）
- monitoring/
  - __init__.py                        — 監視・モニタリング関連（実装は各自）

（上記は本コードベースで定義されている主要モジュールの抜粋です）

---

## 注意点 / 運用上のガイド

- J-Quants API のレート制限やリトライ・401トークン更新処理は jquants_client に組み込まれていますが、API キー管理・シークレット保護は運用者側で行ってください。
- DuckDB ファイルはデフォルト data/kabusys.duckdb に作成されます。バックアップや永続化ポリシーは運用で定めてください。
- ニュース収集では外部 URL を取得するため SSRF 対策が行われていますが、プロキシやネットワーク構成次第で追加対策が必要になる場合があります。
- ETL は「Fail-Fast」ではなく各ステップを独立して実行し、品質チェックで問題を検出・報告する設計です。品質問題の扱い（停止/警告）は運用方針に従ってください。
- 実際の発注処理（証券会社への送信）を組み込む場合は execution 層を実装し、冪等キー・監査ログを適切に連携してください。

---

## 貢献・バグ報告

この README はコードベースの概要ドキュメントです。バグ報告や機能追加は Issue を立てるか、Pull Request を送ってください。README の改善提案も歓迎します。

---

必要であれば、README にサンプルスクリプト、.env.example のサンプル、あるいは具体的な CLI / systemd ジョブの設定例などを追加できます。どの情報を優先的に追記したいか教えてください。
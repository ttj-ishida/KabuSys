# KabuSys

KabuSys は日本株を対象とした自動売買 / データプラットフォームのライブラリです。  
DuckDB をデータレイクとして用い、J-Quants など外部データソースからの ETL、データ品質チェック、特徴量計算、ニュース収集、監査ログ構築までを含む設計になっています。

---

## 概要

主な設計思想・特徴：

- DuckDB をコア DB として「Raw / Processed / Feature / Execution / Audit」の層でデータを整理
- J-Quants API からの差分取得（レート制限遵守 / リトライ / トークン自動更新）
- ニュース（RSS）収集時の SSRF 対策・サイズ制限・トラッキング除去などの堅牢な処理
- ETL（差分取得、保存、品質チェック）の一貫した実装（日次 ETL のエントリポイントあり）
- ファクター（モメンタム・バリュー・ボラティリティ等）計算および IC / 統計サマリー
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマを提供
- 外部に重い依存を置かず標準ライブラリ中心の実装（ただし DuckDB, defusedxml 等は必須）

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（レート制限、リトライ、トークン刷新対応）
  - schema: DuckDB 用スキーマ定義 & 初期化（raw/processed/feature/execution 層）
  - pipeline / etl: 差分 ETL（prices/financials/calendar）の実装と日次 ETL 実行
  - news_collector: RSS 取得・前処理・DB 保存（SSRF 対策、トラッキング除去、記事ID は SHA256）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合など）
  - audit: 監査ログテーブル（signal / order_request / executions）
  - stats: 汎用統計（zscore_normalize 等）
- research
  - factor_research: momentum/volatility/value 等のファクター計算
  - feature_exploration: 将来リターン計算（forward returns）、IC（Spearman ρ）、統計サマリーなど
- strategy / execution / monitoring: 各層用のパッケージプレースホルダ（実装はパッケージ構成参照）

---

## 必要要件

- Python 3.10+
  - （ソース内での型注釈に `X | Y` を使用しているため）
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮）:
```bash
python -m pip install duckdb defusedxml
# 必要に応じてプロジェクトを editable install
# python -m pip install -e .
```

---

## 環境変数 / 設定

設定は環境変数もしくはプロジェクトルートの `.env` / `.env.local` ファイルから読み込まれます（自動ロード。無効化可）。自動ロードの挙動：

- プロジェクトルートは `__file__` を基点に上位ディレクトリを探索して `.git` または `pyproject.toml` の存在で判定します。
- 読み込み優先順: OS 環境変数 > .env.local（override=True）> .env（override=False）
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用など）。

主要な環境変数（Settings クラスで参照）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルトは http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト data/monitoring.db
- KABUSYS_ENV (任意) — development | paper_trading | live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

設定が欠けている必須キーを参照すると ValueError が発生します（早期発見のため）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 必要パッケージをインストール（duckdb / defusedxml など）
3. プロジェクトルートに `.env` を作成（`.env.example` を参考に）
4. DuckDB スキーマを初期化

サンプル:
```python
from kabusys.data import schema

# ディレクトリが存在しなければ自動で作られます
conn = schema.init_schema("data/kabusys.duckdb")
# 監査ログ専用 DB を別に用意する場合:
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（代表的ワークフロー）

### 日次 ETL を実行する

日次 ETL はカレンダー → 株価 → 財務 → 品質チェックの順に実行されます。エラーがあっても可能な限り処理を継続し、結果を ETLResult で返します。

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

run_daily_etl の主な引数:
- target_date: ETL 対象日（省略時は当日）
- id_token: J-Quants の id token を外部注入してテスト可
- run_quality_checks: 品質チェックを実行するか

### ニュース収集（RSS）

RSS を取得して raw_news に保存し、銘柄紐付けを行う典型的な実行例:

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 有効な銘柄コードのセット（抽出に使用）
known_codes = {"7203", "6758", "9984"}  # など

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

news_collector は以下の安全策を採用しています：
- HTTP(S) スキームのみ許可（SSRF 対応）
- リダイレクト先の検査（プライベート IP などを拒否）
- レスポンスサイズ上限（デフォルト 10MB）
- トラッキングクエリ除去と記事 ID の SHA-256 ハッシュ化

### ファクター / 研究ツール

DuckDB 接続を与えてファクター計算・解析を行えます。外部依存は避け標準ライブラリで実装されています。

例: モメンタム計算、将来リターン、IC 計算、Z スコア正規化

```python
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
# calc_ic 等は code をキーにマージして使用
# zscore_normalize は列名リストを与えてクロスセクション正規化
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
summary = factor_summary(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

### J-Quants クライアント（fetch / save）

jquants_client はページネーション対応、レート制限（120 req/min）、最大 3 回の指数バックオフリトライ、401 時の自動トークンリフレッシュを備えます。

例：株価取得と保存（内部的にはページネーションしつつ save_daily_quotes を使って冪等保存）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = save_daily_quotes(conn, records)
print(f"fetched={len(records)} saved={saved}")
```

注意: トークンは Settings で指定された `JQUANTS_REFRESH_TOKEN` を用いて自動的に取得されますが、テストで外部トークン注入することも可能です。

---

## ディレクトリ構成（主要ファイルの説明）

（リポジトリ内 src/kabusys 以下の主要ファイル/モジュール）

- __init__.py
  - パッケージ定義、バージョン情報
- config.py
  - 環境変数 / .env 読み込み、Settings API（設定の型安全な取得）
- data/
  - jquants_client.py: J-Quants API クライアント（fetch/save）
  - news_collector.py: RSS 取得 → raw_news 保存、銘柄抽出・紐付け
  - schema.py: DuckDB スキーマ（DDL）定義と init_schema()
  - pipeline.py: ETL パイプライン（差分取得、run_daily_etl 等）
  - features.py: 特徴量ユーティリティの公開（zscore_normalize の再エクスポート）
  - calendar_management.py: 市場カレンダー管理、営業日判定ユーティリティ
  - quality.py: 品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py: 監査ログ DDL と初期化（init_audit_db）
  - stats.py: 汎用統計（zscore_normalize）
  - etl.py: 公開インターフェース（ETLResult の再エクスポート）
- research/
  - feature_exploration.py: 将来リターン計算、IC、factor_summary、rank
  - factor_research.py: momentum / volatility / value ファクター計算
  - __init__.py: 研究系 API の再エクスポート
- strategy/, execution/, monitoring/:
  - 各層のパッケージ（エントリポイント／実装は今後拡張想定）

---

## 注意点・トラブルシューティング

- Python バージョンは 3.10 以上を推奨（ソースに union 型注釈を使用）
- DuckDB のファイルパス（DUCKDB_PATH）は書き込み権限がある場所を指定してください
- .env はプロジェクトルート（.git または pyproject.toml がある場所）で自動読み込みされます。テスト時や別環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自力で環境を注入してください
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかのみ許容されます
- LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかで、Settings のチェックにより不正値は例外になります
- ニュース収集や外部 API 呼び出しはネットワークに依存します。プロキシやファイアウォールによる影響に注意してください
- jquants_client は API レート制限・401 トークン更新・リトライを実装していますが、実際の運用では API 側の仕様変更やレート変更に応じて調整が必要です

---

## 開発 / 貢献

- コードの拡張やバグ修正は PR で受け付けます。CI やテスト整備がある場合はそれに従ってください。
- 新しいテーブル・インデックスを追加する場合は schema.py の DDL 配列に追記し、init_schema を通じて適用してください（冪等設計）。

---

この README はコードベースの現状に基づく概要と利用方法の抜粋です。各モジュールの詳細な使い方・引数仕様はソースコードの docstring を参照してください。質問や具体的な実行例（例: ETL スケジュール、Slack 通知の実装例など）が必要であれば追って提供します。
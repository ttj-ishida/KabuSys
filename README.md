# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants API からデータを収集して DuckDB に格納し、特徴量計算・戦略リサーチ・監査ログ・ETL パイプライン等を提供します。

主な設計方針：
- DuckDB を中心としたローカルデータレイク（冪等な INSERT / ON CONFLICT を使用）
- J-Quants API のレート制限・リトライ・トークン自動リフレッシュ対応
- Research / Data 層は本番発注 API にアクセスしない（安全）
- XML / RSS 収集時の SSRF・XML Bomb 対策等、安全性を考慮

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（無効化可）
  - 必須環境変数の取得と検証（settings オブジェクト）

- データ収集・保存（kabusys.data）
  - J-Quants API クライアント（jquants_client）
    - 日足（OHLCV）、財務データ、JPX カレンダーの取得（ページネーション対応）
    - レートリミット、リトライ、401時のトークン自動リフレッシュ
    - DuckDB への冪等保存ユーティリティ（save_*）
  - RSS ニュース収集（news_collector）
    - RSS 取得、前処理、記事ID生成（正規化URL→SHA256）、DB保存、銘柄抽出
    - SSRF 対策、受信サイズ上限、defusedxml による安全パース
  - スキーマ定義 / 初期化（schema）
    - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
    - init_schema(), init_audit_db() 等
  - ETL パイプライン（pipeline）
    - 差分更新、バックフィル、品質チェックの統合（run_daily_etl）
  - カレンダー管理（calendar_management）
    - 営業日判定、前後営業日取得、カレンダー更新バッチ

- 品質管理（data.quality）
  - 欠損、スパイク、重複、日付不整合のチェック（QualityIssue 出力）

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
  - z-score 正規化ユーティリティ（data.stats 経由）

- 監査（audit）
  - シグナル→発注→約定のトレーサビリティテーブル（監査ログ用）

---

## 必要条件

- Python 3.10 以降（typing の | 演算子を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発インストール（プロジェクトルートに setup/pyproject があれば）
# pip install -e .
```

※ 他にロギングや Slack 連携等を行う場合は追加パッケージを用意してください（本コードベースでは直接の依存は記載されていません）。

---

## 環境変数 / 設定

config.Settings で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード（発注機能利用時）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 用パス（モニタリング等、デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` を自動で読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- テスト時等で自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セットアップ手順（概要）

1. リポジトリをクローンして仮想環境を用意
2. 必要パッケージをインストール（duckdb, defusedxml 等）
3. プロジェクトルートに `.env` を作成し、必須環境変数を設定
   - .env.example がある場合はそれを参照
4. DuckDB スキーマを初期化
   - Python REPL やスクリプトから schema.init_schema() を実行
5. ETL を実行してデータ取得

例:

```python
from pathlib import Path
import duckdb
from kabusys.data import schema, pipeline

# 1) DuckDB の初期化（ファイルを指定）
db_path = Path("data/kabusys.duckdb")
conn = schema.init_schema(db_path)

# 2) 日次 ETL を実行（今日分）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

監査DBの初期化（監査ログ専用 DB を別に用いる場合）:

```python
from pathlib import Path
from kabusys.data import audit

audit_conn = audit.init_audit_db(Path("data/kabusys_audit.duckdb"))
```

RSS ニュース収集の実行例:

```python
from kabusys.data import news_collector, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
# 既に schema.init_schema() を行っておくこと
results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

研究用（ファクター計算）の例:

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2025, 1, 31)

momentum = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target)

# IC の例
ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
print(summary)
```

---

## 使い方（主要ワークフロー）

1. スキーマ初期化
   - data.schema.init_schema(db_path) を実行して DuckDB を作成・テーブル定義を適用

2. 日次 ETL（データ収集）
   - data.pipeline.run_daily_etl(conn, ...) を実行
   - 取得（J-Quants）→ 保存（raw_prices/raw_financials/market_calendar）→ 品質チェック の順で実行

3. 特徴量・リサーチ
   - research パッケージの関数で特徴量や将来リターンを計算
   - data.stats.zscore_normalize でクロスセクション正規化

4. ニュース収集
   - data.news_collector.run_news_collection で RSS を取得し raw_news / news_symbols に保存

5. 監査ログ
   - audit.init_audit_db() / init_audit_schema() を用いて監査用テーブルを初期化
   - 発注・約定のライフサイクルを監査テーブルに記録（トレーサビリティ確保）

注意点:
- research / data の多くは DuckDB 接続を引数で受け取ります。呼び出し元で接続管理（トランザクション等）を行ってください。
- run_daily_etl 等は各ステップで例外をハンドルして続行する設計ですが、Result オブジェクトの errors/quality_issues を確認して運用判断を行ってください。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定読み込み
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - news_collector.py — RSS ニュース収集・DB保存
  - schema.py — DuckDB スキーマ定義と init_schema / get_connection
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - features.py — features の公開インターフェース（再エクスポート）
  - calendar_management.py — マーケットカレンダー管理・バッチ
  - audit.py — 監査ログ用テーブル定義 / 初期化
  - quality.py — データ品質チェック（欠損・スパイク等）
  - etl.py — ETLResult の公開再エクスポート
- research/
  - __init__.py — 主要関数の再エクスポート
  - feature_exploration.py — 将来リターン計算 / IC / summary / rank
  - factor_research.py — momentum / volatility / value ファクター計算
- strategy/ (空のパッケージ枠)
- execution/ (空のパッケージ枠)
- monitoring/ (空のパッケージ枠)

---

## 開発 / テストのヒント

- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテストを行うと環境依存を避けられます。
- DuckDB のテスト用途には ":memory:" を db_path として渡すとインメモリ DB が使えます。
- news_collector._urlopen や jquants_client._request などは内部で切り替え／モック可能な設計になっており、ユニットテストがしやすく作られています。

---

必要であれば、README に実行スクリプトのサンプル（cron 用ラッパー、systemd ユニット例、Dockerfile、CI 用ワークフロー）や、より詳しい `.env.example`、DuckDB スキーマの ER 図などを追加できます。どの情報を追加したいか教えてください。
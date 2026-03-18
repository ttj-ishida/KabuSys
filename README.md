# KabuSys

日本株向けの自動売買 / データプラットフォーム実験用ライブラリです。  
DuckDB を用いたデータ基盤、J-Quants API とのデータ取得クライアント、RSS ベースのニュース収集、特徴量計算・リサーチユーティリティ、ETL パイプライン、データ品質チェック、監査ログスキーマなどを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- データ保存 / スキーマ
  - DuckDB 用のスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
  - 冪等保存（ON CONFLICT / DO UPDATE）を考慮
- ETL パイプライン
  - 差分取得（最終取得日ベース）、バックフィル、品質チェックの実行
  - run_daily_etl による一括実行
- ニュース収集
  - RSS フィードの取得・前処理・記事保存（SSRF 対策、サイズ上限、トラッキング除去）
  - 銘柄コード抽出と記事 ↔ 銘柄の紐付け
- リサーチ / 特徴量
  - Momentum / Volatility / Value などのファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- 品質チェック
  - 欠損・重複・スパイク（急騰/急落）・日付不整合の検出
- 監査ログ
  - signal -> order_request -> executions までトレース可能な監査スキーマ

---

## 前提 / 必要環境

- Python 3.10 以上（型注釈に Python 3.10 の union 演算子 `|` を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

（プロジェクトの実際の requirements は別途管理してください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトします。

2. 仮想環境を作成して有効化し、必要パッケージをインストールします（例）:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   # またはプロジェクトで requirements.txt / pyproject.toml を用意している場合はそれに従う
   ```

3. 環境変数を設定します（下記参照）。開発時はプロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みを無効化する方法も下に記載）。

---

## 環境変数

主要な環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

自動 .env ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、パッケージ起動時の自動 .env 読み込みを無効化できます。
- 自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に `.env` → `.env.local` の順で読み込みます。既存の OS 環境変数は保護されます。

簡単な .env の例（実際の値は安全に管理してください）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期化（DuckDB スキーマ作成）

DuckDB のスキーマを初期化して接続を取得する例:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照します
conn = init_schema(settings.duckdb_path)

# メモリDB を使う場合
# conn = init_schema(":memory:")
```

監査ログ専用 DB を初期化する場合:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## ETL（データパイプライン）の使い方

日次 ETL を実行する簡単な例:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# 当日分の ETL（デフォルト）
result = run_daily_etl(conn)

# 特定日を指定する場合
result = run_daily_etl(conn, target_date=date(2024, 1, 5))
```

戻り値は ETLResult オブジェクトで、取得/保存件数や検出された品質問題・エラー情報を保持します。

個別ジョブ（株価/財務/カレンダー）の実行も可能:
- run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline 内）

---

## ニュース収集の使い方

RSS フィードを取得して DuckDB に保存する例:

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")

# known_codes を与えると記事に含まれる銘柄コードを抽出して news_symbols に紐付ける
known_codes = {"7203", "6758", "9984"}  # 実運用では有効銘柄リストを用意する

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
# results: {source_name: saved_count}
```

RSS 取得は SSRF / gzip 膨張 / 大容量レスポンス対策、XMLパースの堅牢化が組み込まれています。

---

## リサーチ / ファクター計算の使い方

リサーチ用ユーティリティ（例: モメンタム計算、IC 計算）:

```python
from kabusys.data.schema import init_schema
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = init_schema(":memory:")  # または既存 DB 接続

# 例: ある基準日のモメンタムを計算
records = calc_momentum(conn, target_date=date(2024, 1, 5))

# 将来リターンを計算して IC を求める
fwd = calc_forward_returns(conn, target_date=date(2024, 1, 5), horizons=[1,5])
ic = calc_ic(factor_records=records, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
```

Z スコア正規化ユーティリティ:
- kabusys.data.stats.zscore_normalize / kabusys.data.features.zscore_normalize

注意:
- これらの関数は DuckDB 内のテーブル（prices_daily や raw_financials 等）を参照します。
- 本コードベースのリサーチ関数は本番口座や発注 API にアクセスしません（Read-only）。

---

## 品質チェック

ETL 後に自動で実行される品質チェック（run_daily_etl の引数 run_quality_checks=True がデフォルト）に加え、個別に実行可能です:

```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2024,1,5))
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

主要チェック:
- 欠損データ（OHLC 欠損）
- 主キー重複
- 前日比スパイク（デフォルト 50%）
- 将来日付 / 非営業日データの検出

---

## 開発メモ / 注意点

- 自動 .env 読み込みはパッケージインポート時に行われます（設定はプロジェクトルートの .env / .env.local）。テストや明示的な設定が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限（デフォルト 120 req/min）に合わせた内部 RateLimiter、リトライ、バックオフを実装しています。大量取得の際は API 制限を確認してください。
- DuckDB のバージョン差異による機能差（たとえば ON DELETE CASCADE のサポート）に注意してください（コード中に注釈あり）。
- 監査ログテーブルは UTC タイムゾーンでの保存を前提としています（init_audit_schema が SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS ニュース収集／保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL パイプライン（差分取得・品質チェック）
    - features.py             — 特徴量ユーティリティエクスポート
    - calendar_management.py  — 市場カレンダー管理（営業日判定等）
    - audit.py                — 監査ログスキーマ初期化
    - etl.py                  — ETL 公開型（ETLResult 等）
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - feature_exploration.py  — 将来リターン・IC・summary
    - factor_research.py      — momentum / volatility / value の計算
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は主要モジュールの一覧です。細かなユーティリティや補助関数は各ファイル内を参照してください）

---

## 例: よく使うワークフロー（まとめ）

1. .env を準備して環境変数を設定
2. DuckDB スキーマを初期化
   - init_schema(settings.duckdb_path)
3. 日次 ETL を実行
   - run_daily_etl(conn)
4. 必要に応じてニュース収集やリサーチ関数を実行
   - run_news_collection、calc_momentum 等
5. 品質チェック結果や ETLResult を確認してアラート/手動対応

---

問題報告や実装に関する質問があれば、どの機能について知りたいかを指定して質問してください。README の内容をプロジェクト用に調整（依存関係の明示、実行スクリプト追加等）することも可能です。
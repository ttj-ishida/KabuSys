# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（研究・データパイプライン・監査・発注基盤の骨組み）。

このリポジトリは、J-Quants からの市場データ取得、DuckDB を用いたデータ格納・スキーマ管理、ニュース収集、研究（ファクター計算 / IC 計算）や ETL パイプライン、監査ログ構築までをカバーするモジュール群を提供します。

バージョン: 0.1.0

---

## 主要機能（概要）

- 環境設定管理
  - .env ファイル自動読み込み（プロジェクトルート検出ベース）
  - 必須環境変数のラッパー（kabusys.config.settings）
- データ取得 / 保存
  - J-Quants API クライアント（レートリミット・リトライ・トークンリフレッシュ対応）
  - DuckDB への冪等保存ユーティリティ（raw / processed / feature / execution 層のDDL）
- ETL / パイプライン
  - 差分更新（backfill 対応）、カレンダー先読み、品質チェック組み込みの日次 ETL（run_daily_etl）
- ニュース収集
  - RSS フィード取得、前処理、記事ID生成（SHA-256 ベース）、DuckDB への冪等保存、銘柄抽出
  - SSRF / XML BOM / gzip サイズ対策などの安全設計
- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティの提供
- 監査ログ（Audit）
  - signal → order_request → execution に至る監査テーブルの定義・初期化
- データ品質チェック
  - 欠損、重複、スパイク、日付整合性チェック

---

## 必要な環境変数

以下は本ライブラリが参照する代表的な環境変数です。`.env` ファイルをプロジェクトルートに置くと自動で読み込まれます（自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（Settings._require により取得されるもの）
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション等の API パスワード（発注系と連携する場合）
- SLACK_BOT_TOKEN        — Slack 通知用トークン（必要な場合）
- SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID

任意（デフォルトあり）
- KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例（`.env`）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.9+）
2. 依存パッケージをインストール
   - 最低限必要なライブラリ（例）:
     - duckdb
     - defusedxml
   - pip でインストール:
     ```
     pip install duckdb defusedxml
     ```
   - 追加で HTTP / Slack 等の実装を導入する場合は適宜ライブラリを追加してください。

3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマ初期化（次セクション参照）

---

## 初期化・基本的な使い方

以下は Python からの簡単な利用例です。duckdb 接続を作成してスキーマを初期化し、ETL を実行する流れを示します。

- DuckDB スキーマ初期化
```python
from pathlib import Path
from kabusys.data.schema import init_schema

db_path = Path("data/kabusys.duckdb")
conn = init_schema(db_path)  # ファイルがなければ親ディレクトリを自動作成
```

- 監査ログスキーマ初期化（audit 用 DB を別に作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL 実行（市場データ・財務データ・カレンダーの差分取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())  # ETLResult のサマリ表示
```

- ニュース収集の実行例
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes に有効な銘柄コードの集合を渡すと銘柄との紐付けが行われる
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(res)
```

- 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary

conn = duckdb.connect("data/kabusys.duckdb")
t = date(2024, 1, 31)
mom = calc_momentum(conn, t)
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m","mom_3m","ma200_dev"])
```

- Zスコア正規化（data.stats）
```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m"])
```

---

## よく使う API / 関数一覧（抜粋）

- kabusys.config.settings — 環境変数ラッパー
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.schema
  - init_schema(db_path) — DuckDB スキーマの初期化
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(...) — 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
- kabusys.data.news_collector
  - fetch_rss(url, source) — RSS 取得と記事変換
  - save_raw_news(conn, articles) — raw_news への保存
  - run_news_collection(conn, sources, known_codes)
- kabusys.data.quality
  - run_all_checks(conn, target_date, reference_date)
- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.stats
  - zscore_normalize

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - news_collector.py — RSS 収集・保存
    - schema.py — DuckDB スキーマ定義・初期化
    - stats.py — 汎用統計（zscore_normalize）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - features.py — 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py — 市場カレンダー管理ユーティリティ
    - audit.py — 監査ログスキーマの初期化
    - etl.py — ETLResult 再エクスポート
    - quality.py — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン / IC / summary
    - factor_research.py — momentum/value/volatility 計算
  - strategy/ — 戦略関連（雛形）
  - execution/ — 発注 / ブローカー連携（雛形）
  - monitoring/ — 監視用モジュール（雛形）

---

## セキュリティ・設計上の注意点（実運用時のポイント）

- J-Quants のレート制限（120 req/min）を遵守する仕組みを実装済み（_RateLimiter）。
- API リトライ（指数バックオフ）・401 時のトークンリフレッシュを実装。
- RSS 取得では SSRF 対策、gzip サイズチェック、defusedxml による XML インジェクション対策を実施。
- DuckDB への保存は冪等（ON CONFLICT）で二重保存を防止。
- audit モジュールはタイムゾーンを UTC に固定するなどトレーサビリティを重視。

---

## テスト / デバッグ

- 自動で .env を読み込みますが、テスト時は自動ロードを無効化できます:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- モジュールは標準ライブラリでの処理を多用し、外部依存を最小限にしています。ユニットテストを書く際は duckdb のインメモリ DB（":memory:"）を使うと便利です。

---

## 今後の拡張候補（参考）

- 発注実行（execution）部分のブローカーラッパー実装（kabuステーション等）
- Slack / メトリクス送信の統合（通知用クライアント）
- 战略実装のサンプル（ポートフォリオ最適化・リスク管理）
- Docker イメージ化 / GitHub Actions で ETL スケジュール CI 化

---

この README はコードベースの主要機能と利用手順の概要を示したものです。各モジュール内の docstring に詳細な挙動・引数仕様・設計意図が記載されていますので、具体的な利用時は当該モジュールのドキュメントを参照してください。必要であれば、README に含める追加の使用例や運用手順（systemd / crontab / k8s CronJob での運用例など）を作成します。
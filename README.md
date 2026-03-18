# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB をデータレイクとして用い、J-Quants からの市場データ取得、RSS ニュース収集、特徴量計算、ETL パイプライン、監査ログ、品質チェックなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買基盤を構成するための内部ライブラリ群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダーの差分取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB によるデータ保存（冪等保存、スキーマ定義）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策やトラッキングパラメータ除去）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 特徴量（モメンタム・ボラティリティ・バリュー等）計算および正規化ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- マーケットカレンダー管理、品質チェック（欠損・スパイク・重複・日付不整合）

設計方針として、本番発注 API には直接アクセスしないリサーチ/データ処理の分離、標準ライブラリ優先の実装、冪等性とトレーサビリティを重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、レート制限、リトライ、トークン自動更新）
  - news_collector: RSS 収集・正規化・保存（SSRF対策、gzip/サイズチェック、記事IDのSHA-256ベース生成）
  - schema: DuckDB のスキーマ定義と初期化（Raw/Processed/Feature/Execution 層）
  - pipeline / etl: 差分 ETL（prices / financials / market calendar）とメイン run_daily_etl
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダーの管理と営業日判定ユーティリティ
  - audit: 監査ログテーブル（signal_events / order_requests / executions）初期化
  - stats: z-score 正規化等の統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value などのファクター計算
  - feature_exploration: 将来リターン計算、IC（情報係数）計算、要約統計
- config: 環境変数管理（.env 自動ロード、必須変数チェック）

---

## 必要条件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

（その他は標準ライブラリで実装されていますが、実行環境や追加機能により必要なパッケージが増える可能性があります。）

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクトをパッケージとして使う場合は setup / pyproject のセットアップに従ってインストールしてください（src レイアウト）。

---

## 環境変数 / 設定

KabuSys は環境変数およびプロジェクトルートの `.env` / `.env.local` を読み込みます（優先順位: OS 環境変数 > .env.local > .env）。プロジェクトルートは `.git` または `pyproject.toml` を起点に自動検出します。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

主要な環境変数（例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（省略時: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

.env の書式は一般的な KEY=VALUE をサポートし、クォートやコメント、export プレフィックスに対応しています。

---

## セットアップ手順 (簡易)

1. Python 環境準備（3.10+ 推奨）
2. 依存パッケージをインストール
   - 例: pip install duckdb defusedxml
3. 環境変数を設定
   - プロジェクトルートに `.env` を作成（.env.example を参考に）
   - あるいは OS 環境変数で設定
4. DuckDB スキーマ初期化
   - 以下のようにして DuckDB を初期化します（デフォルトパスは settings.duckdb_path）。
   - Python 例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```
5. 監査ログ DB を別で初期化する場合（オプション）:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（代表的な例）

- 日次 ETL（市場カレンダー・株価・財務・品質チェック）を実行する:
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別の ETL ジョブを実行する:
```python
# 株価差分 ETL
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- RSS ニュース収集（既知銘柄セットを渡して銘柄紐付けを行う）:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は検出に使用する有効な銘柄コードの集合（例: {"7203","6758"})
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(res)  # {source_name: 保存件数, ...}
```

- ファクター計算 / リサーチ:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 例: momentum の一部カラムを z-score 正規化
normalized = zscore_normalize(mom, columns=["mom_1m","mom_3m","mom_6m","ma200_dev"])
```

- 品質チェックだけ実行する:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## よく使う API (抜粋)

- kabusys.config.settings: 設定（環境変数）アクセス
- kabusys.data.schema.init_schema(db_path): DuckDB スキーマ初期化（返り値は接続）
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.pipeline.run_daily_etl: 日次ETL のエントリポイント
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.data.stats.zscore_normalize

---

## ディレクトリ構成

（主要ファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック、レート制限、リトライ、トークン管理）
    - news_collector.py
      - RSS 収集、前処理、保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - etl.py
      - ETLResult の公開
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - 特徴量ユーティリティの公開インターフェース
    - audit.py
      - 監査ログテーブル初期化（signal_events / order_requests / executions）
    - calendar_management.py
      - market_calendar の更新、営業日判定ユーティリティ
    - pipeline.py (ETL 主処理)
  - research/
    - __init__.py
      - 研究用関数の再エクスポート
    - feature_exploration.py
      - 将来リターン、IC、要約統計
    - factor_research.py
      - momentum / volatility / value ファクター計算
  - strategy/
    - __init__.py
    - （戦略関連モジュールを配置）
  - execution/
    - __init__.py
    - （発注/ポジション管理関連を配置）
  - monitoring/
    - __init__.py
    - （監視・メトリクス関連を配置）

---

## 注意点 / 運用メモ

- .env 自動ロードはプロジェクトルート（.git/pyproject.toml を基準）から行われます。CI やテストで無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限（120 req/min）を尊重するため、jquants_client は固定間隔のレートリミッタを実装しています。
- DuckDB に対する INSERT は基本的に ON CONFLICT DO UPDATE / DO NOTHING を利用し冪等性を確保しています。
- news_collector は SSRF/サイズ爆弾対策、XML の安全パーサ（defusedxml）を使用しています。
- 本リポジトリの research / data モジュールは本番の発注・口座情報にアクセスしないよう設計されています（安全なリサーチ環境を目的）。

---

## 貢献 / 拡張案

- Strategy 層（strategy/）に実際のポートフォリオ構築・リスク管理ロジックを追加
- execution 層で複数ブローカーのアダプタを実装
- Slack 通知や監視ダッシュボードの統合（monitoring）
- 更なる品質チェックや自動修復ルールの追加

---

README はここまでです。必要ならインストール手順の詳細（requirements.txt / pyproject.toml の例）、ユニットテストの実行方法、CI 設定テンプレートなども追記できます。どの情報を優先して追記しますか？
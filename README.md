# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
主に J-Quants API からのデータ取得、DuckDB によるデータ保管・スキーマ管理、ETL パイプライン、ニュース収集、ファクター計算（リサーチ用）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システムの基盤ライブラリ群です。設計方針として以下を重視しています。

- DuckDB を中心としたローカルデータベースでの Raw → Processed → Feature 層の管理
- J-Quants API からの安全かつレート制限を守ったデータ取得（ID トークン自動リフレッシュ、指数バックオフ）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・圧縮/サイズ上限・トラッキングパラメータ除去）
- ETL の差分更新（バックフィル対応）とデータ品質チェック
- 研究用（Research）モジュールによるファクター計算・IC 計算・正規化ユーティリティ
- 監査用スキーマ（signal → order → execution トレース）を備えた監査ログ機能

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数を明示的に取得する Settings API
- データ取得（kabusys.data.jquants_client）
  - 株価日足、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レートリミッタ、リトライ、401 リフレッシュ対応
  - DuckDB への冪等保存関数（save_*）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義
  - init_schema, get_connection
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新・バックフィル対応
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、正規化、記事ID生成、raw_news 保存、銘柄抽出、紐付け
  - SSRF 対策、サイズ制限、XML パース安全化
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合検出
- 研究モジュール（kabusys.research）
  - モメンタム / ボラティリティ / バリュー計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）
  - IC（スピアマン）計算（calc_ic）、ファクター統計要約（factor_summary）
  - Z スコア正規化ユーティリティ（zscore_normalize）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の初期化と管理

---

## 要件

- Python 3.10+
- duckdb
- defusedxml
- 標準ライブラリの urllib 等

（実行環境に応じて追加の依存が必要になる場合があります）

---

## セットアップ手順

1. リポジトリをクローンしてインストール（開発インストール例）

   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 環境変数を準備

   - プロジェクトルートに `.env` と（任意で）`.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   重要な環境変数（Settings で必須/参照されるもの）:

   - JQUANTS_REFRESH_TOKEN （必須） — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD （必須） — kabuステーション API パスワード
   - KABU_API_BASE_URL （任意、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN （必須） — Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID （必須） — Slack チャンネル ID
   - DUCKDB_PATH （任意、デフォルト: data/kabusys.duckdb） — DuckDB ファイルパス
   - SQLITE_PATH （任意、デフォルト: data/monitoring.db）
   - KABUSYS_ENV （任意、default: development） — 有効値: development, paper_trading, live
   - LOG_LEVEL （任意、default: INFO） — DEBUG/INFO/WARNING/ERROR/CRITICAL

3. DuckDB スキーマ初期化

   - メインスキーマを初期化（ファイルパスを指定）

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   - 監査ログ専用 DB を初期化する場合（または同一接続に追加）

   ```python
   from kabusys.data.audit import init_audit_db, init_audit_schema
   # 別 DB を作る場合
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   # 既存 conn に追加したい場合
   from kabusys.data.schema import get_connection
   conn = get_connection("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（代表的な例）

以下はライブラリ使用例の抜粋です。詳細はモジュールの docstring を参照してください。

- 設定取得

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

- 日次 ETL 実行

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- J-Quants から直接データ取得（テスト用途など）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
financials = fetch_financial_statements(date_from=date(2023,1,1), date_to=date(2023,12,31))
```

- ニュース収集ジョブ実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コード集合
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- リサーチ用ファクター計算（例: モメンタム）

```python
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)
momentum = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
```

- DuckDB への保存関数（冪等）

  jquants_client.save_* 関数は ON CONFLICT DO UPDATE 等で冪等に保存します。ETL や手動保存で使用できます。

---

## 環境変数の自動読み込み挙動

- パッケージは import 時に実行中のファイル位置からプロジェクトルート（.git または pyproject.toml を探索）を検出し、プロジェクトルートにある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - .env.local は override=True のため既存 OS 環境変数（protected）を上書きしません。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利です）。

---

## ディレクトリ構成

主要ファイルとモジュール（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/
    - __init__.py
  - strategy/
    - __init__.py
  - monitoring/
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント、fetch/save 関数
    - news_collector.py        — RSS ベースのニュース収集・正規化・DB 保存
    - schema.py                — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py                 — zscore_normalize 等の統計ユーティリティ
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - features.py              — features の公開インターフェース（再エクスポート）
    - calendar_management.py   — market_calendar 管理（営業日判定等）
    - etl.py                   — ETLResult の再エクスポート
    - quality.py               — データ品質チェック
    - audit.py                 — 監査ログスキーマの初期化
  - research/
    - __init__.py
    - feature_exploration.py   — 将来リターン / IC / サマリ
    - factor_research.py       — momentum / volatility / value ファクター計算

各モジュールは docstring に設計方針や注意点が記載されています。実装の詳細はコードの docstring を参照してください。

---

## 注意事項 / ベストプラクティス

- J-Quants API にはレート制限があるため、API 呼び出しには内蔵のレートリミッタとリトライを利用してください。直接大量のループで叩くことは避けてください。
- DuckDB の初期化は init_schema を使い、初回のみ実行することを推奨します。既存 DB に対しては get_connection を利用してください。
- ETL の差分取得では過去数日分を再取得（backfill）する設計になっており、API の後出し修正を吸収します。
- NewsCollector は外部 URL を処理するため SSRF 対策や受信サイズチェックを行っていますが、運用時は信頼できるフィードソースを選んでください。
- 本リポジトリは「本番口座・発注 API にはアクセスしない」ことを前提に設計されているモジュールが多くあります（research / data 等）。発注ロジックを実装する際は execution / strategy 層の実装方針に従ってください。

---

必要であれば README にサンプル .env.example、CI / テストの説明、拡張ポイント（戦略実装ガイド）なども追記できます。追加で載せたい情報があれば教えてください。
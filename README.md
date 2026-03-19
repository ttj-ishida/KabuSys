# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリ。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API からの市場データ・財務データ取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いたデータレイヤ（Raw → Processed → Feature → Execution）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算・特徴量エンジニアリング
- 戦略のスコアリングと売買シグナル生成（冪等性を考慮）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策等を実装）
- 発注・約定・監査ログ管理のためのスキーマ定義

設計方針は「ルックアヘッドバイアスの排除」「冪等処理」「外部サービスへの最小限の依存」「監査可能性」です。

---

## 主な機能一覧

- data/
  - jquants_client：J-Quants API クライアント（ページネーション・リトライ・トークンリフレッシュ・保存用ユーティリティ）
  - pipeline：差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - schema：DuckDB スキーマ定義と初期化（init_schema）
  - news_collector：RSS 取得・正規化・DB 保存（SSRF 対策・記事 ID ハッシュ化）
  - calendar_management：営業日判定・更新ジョブ
  - stats：Z スコア正規化などの統計ユーティリティ
  - features：公開インターフェース（zscore_normalize の再エクスポート）
  - audit：監査用テーブル定義・初期化
- research/
  - factor_research：モメンタム / ボラティリティ / バリューなどのファクター計算
  - feature_exploration：将来リターン・IC・統計サマリー等の研究用ユーティリティ
- strategy/
  - feature_engineering：research で作成した raw ファクターを正規化・合成して features テーブルへ保存
  - signal_generator：features と ai_scores を統合して final_score を算出し signals テーブルへ書き込む
- config.py：.env の自動読み込み、環境変数取得ラッパー（Settings）
- execution/ monitoring/ 等の将来的な発注・監視レイヤ

---

## セットアップ手順

前提
- Python 3.10 以上（typing の "X | Y" 構文を使用）
- 推奨: 仮想環境を使用すること

1. レポジトリをクローンしてソースを editable インストール（例）
   ```
   git clone <repo_url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```
   ※ requirements.txt があれば `pip install -r requirements.txt` を使ってください。
   - 必要な主なパッケージ: duckdb, defusedxml
   - 実行環境によっては追加で requests 等が必要になる場合があります。

2. 環境変数設定
   - ルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を配置できます。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にすると無効化）。
   - 読み込み順:
     1. OS 環境変数
     2. .env（プロジェクトルート）
     3. .env.local（上書き）
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知用
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DB スキーマ初期化（DuckDB）
   - Python REPL やスクリプトで以下を実行してスキーマを作成します。
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # ファイルパス（デフォルト data/kabusys.duckdb）
   ```

---

## 使い方（主な操作例）

- 日次 ETL の実行（市場カレンダー / 株価 / 財務）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 研究ファクターの計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum

conn = duckdb.connect(str("data/kabusys.duckdb"))
records = calc_momentum(conn, date(2025, 1, 31))
print(len(records))
```

- 特徴量の作成（feature_engineering → features テーブルに UPSERT）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
count = build_features(conn, date(2025, 1, 31))
print(f"features upserted: {count}")
```

- シグナル生成（features / ai_scores / positions を参照）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection(settings.duckdb_path)
total_signals = generate_signals(conn, date(2025, 1, 31))
print(f"signals generated: {total_signals}")
```

- ニュース収集ジョブ（RSS から raw_news へ保存、銘柄紐付け）
```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection(settings.duckdb_path)
# known_codes は prices_daily 等から取得した有効銘柄コードのセット
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- J-Quants から日足データを直接取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
saved = save_daily_quotes(conn, recs)
print(saved)
```

---

## 設計上の注意点 / 運用メモ

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テストや CI で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限（120 req/min）をモジュール側で一定間隔スロットリングにより順守します。
- DuckDB への挿入は可能な限り UPSERT（ON CONFLICT）やトランザクションで冪等化しています。
- ニュース収集では SSRF 対策、XML パースの安全化（defusedxml）、レスポンスサイズ上限、URL 正規化（utm 等除去）などを実装しています。
- 環境（KABUSYS_ENV）は development / paper_trading / live のいずれかを設定してください。live 環境では発注等に対する追加の安全対策が必要です（本コードベースでは発注ロジックは分離されています）。

---

## ディレクトリ構成

主要ファイル・モジュールの一覧（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - schema.py
    - stats.py
    - features.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/
    - (監視用モジュールを配置予定)

各モジュールの責務はファイル冒頭の docstring に詳細が記載されています。まずは `data/schema.init_schema` で DB を作成し、`data.pipeline.run_daily_etl` を定期実行（cron / Airflow 等）する運用が基本フローです。

---

必要に応じて README に追記します（例: CI 実行方法、デプロイ手順、Slack 通知連携、発注ブローカー統合方法など）。何を追加したいか教えてください。
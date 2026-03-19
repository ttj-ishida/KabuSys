# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、ファクター計算、ニュース収集、監査ログなど、投資戦略開発・研究・運用に必要な基盤機能をまとめて提供します。

## 主な特徴（プロジェクト概要）
- J-Quants API から株価・財務・カレンダーを取得して DuckDB に格納する ETL パイプライン
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ファクター計算（モメンタム・ボラティリティ・バリュー）と IC/サマリー解析（研究用途）
- RSS ベースのニュース収集と銘柄抽出（SSRF/サイズ/トラッキング除去対策あり）
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数ベースの設定管理（.env 自動ロード、必要なシークレットは env にて管理）
- 本番（live）／ペーパー（paper_trading）／開発（development）モード対応

---

## 機能一覧（抜粋）
- data/jquants_client.py
  - J-Quants からのデータ取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - レート制御、リトライ、トークン自動リフレッシュ、DuckDB への保存（save_*）を含む
- data/schema.py
  - DuckDB 用のスキーマ定義と init_schema()
- data/pipeline.py
  - 差分ETL（run_prices_etl / run_financials_etl / run_calendar_etl）と統合 run_daily_etl()
- data/quality.py
  - check_missing_data / check_duplicates / check_spike / check_date_consistency / run_all_checks()
- data/news_collector.py
  - RSS 取得（fetch_rss）、記事保存（save_raw_news）、銘柄抽出（extract_stock_codes）、統合収集 run_news_collection()
- data/calendar_management.py
  - 営業日判定・前後営業日取得・カレンダー更新ジョブ
- research/factor_research.py
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
- research/feature_exploration.py
  - calc_forward_returns, calc_ic, factor_summary, rank
- data/stats.py / data/features.py
  - zscore_normalize（クロスセクション正規化）
- audit.py
  - 監査テーブル定義、init_audit_schema / init_audit_db

---

## 必要条件（推奨）
- Python 3.9+
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml
- その他：標準ライブラリ（urllib, datetime, logging 等）

requirements.txt を用意していない場合は最低限次のようにインストールしてください:
```
pip install duckdb defusedxml
```

---

## 環境変数（主なもの）
アプリ設定は環境変数から読み取ります（プロジェクトルートの `.env` / `.env.local` を自動読み込み）。必須のものは以下。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注系利用時）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化
- KABUSYS_DB_PATH 環境変数はコード上で DUCKDB_PATH にマッピング（実装で DUCKDB_PATH 環境変数を参照）

デフォルト DB パス:
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)

`.env.example` に合わせて `.env` を作成してください（プロジェクトルートに置くと自動読み込みされます）。

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール
   ```
   pip install -e .        # パッケージ化されている場合
   pip install duckdb defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（`.env.example` を参照）
   - もしくは OS 環境変数として設定

   例（.env の最小例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ初期化
   Python REPL やスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

6. 監査ログ用 DB 初期化（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要ユースケースの例）

- 日次 ETL（市場カレンダー→価格→財務→品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 個別 ETL ジョブ
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄コードセット（抽出のために事前に取得）
known_codes = {"7203","6758", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 研究用（ファクター計算・IC 計算）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m","mom_3m","mom_6m","ma200_dev"])
normalized = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m"])
```

- J-Quants からの直接データ取得（テストやバッチ）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
from kabusys.data.jquants_client import save_daily_quotes, save_financial_statements
from kabusys.config import settings
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
save_daily_quotes(conn, records)
```

- データ品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## 重要な実装・設計上の注意点
- J-Quants リクエストは内部でレートリミッター（120 req/min）とリトライを行います。401 は自動でリフレッシュして再試行します（1 回）。
- DuckDB 保存関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を利用して二重投入を防止します。
- ニュース収集は SSRF 対策（リダイレクト検査、プライベートIPの検出）、XML の防御（defusedxml）、レスポンスサイズ制限を実装しています。
- カレンダーが存在しない場合は曜日ベースのフォールバック（平日を営業日とみなす）を行います。
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を順に読み込みます。テスト等で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかで、これにより is_live/is_paper/is_dev のフラグが切り替わります。

---

## ディレクトリ構成（概要）
以下はリポジトリの主要ファイル・モジュール概観です（抜粋）。

- src/kabusys/
  - __init__.py                 -- パッケージエントリ（__version__ 等）
  - config.py                   -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py         -- J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py         -- RSS ニュース収集 / 保存 / 銘柄抽出
    - schema.py                 -- DuckDB スキーマ定義 / init_schema
    - pipeline.py               -- ETL パイプライン（run_daily_etl 等）
    - quality.py                -- データ品質チェック
    - stats.py                  -- zscore_normalize 等統計ユーティリティ
    - features.py               -- data/features インターフェース
    - calendar_management.py    -- カレンダー管理ユーティリティ
    - audit.py                  -- 監査ログテーブル初期化ユーティリティ
    - etl.py                    -- ETLResult 型などの公開インターフェース
  - research/
    - __init__.py
    - factor_research.py        -- mom/vol/value 等ファクター計算
    - feature_exploration.py    -- forward returns / IC / summary / rank
  - strategy/                    -- 戦略・モデル実装置き場（空の __init__）
  - execution/                   -- 発注実装置き場（空の __init__）
  - monitoring/                  -- 監視・メトリクス用（空の __init__）

（上記以外にもテスト・ドキュメント・ツール等が存在する場合があります）

---

## 開発・貢献
- コードはモジュール単位で分離されており、ユニットテストやモック注入がしやすい設計を意図しています（例: news_collector._urlopen をテストで差し替えるなど）。
- PR の際は DuckDB スキーマや既存の API 挙動に影響がないかを確認してください。
- 外部 API を呼ぶ部分（jquants_client 等）は id_token 注入や mock が可能なので、CI では実際の API 呼び出しを行わずにテスト可能です。

---

README に記載のない使い方のサンプルや、CI / デプロイ用の手順が必要であれば、用途（ETL バッチ化、Cron/Cloud Run、監視通知など）を教えてください。必要に応じて具体的なデプロイ手順やサンプルスクリプトを追記します。
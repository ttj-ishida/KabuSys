# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、DuckDB ベースのスキーマ、特徴量計算、ニュース収集、監査ログなどを含み、研究（Research）と本番（Execution）両方のワークフローを支援します。

バージョン: 0.1.0

---

## 概要

主な設計方針と特徴：

- DuckDB をデータ層に採用し、Raw / Processed / Feature / Execution の 3 層（＋監査層）でデータを管理。
- J-Quants API クライアントを提供（レート制御、リトライ、トークン自動更新、ページネーション対応）。
- ETL（差分取得、バックフィル、品質チェック）パイプラインを提供。
- ニュース RSS を安全に取得して前処理・DB に保存する仕組み（SSRF / XML 攻撃対策、トラッキングパラメータ除去）。
- 研究用のファクター計算（モメンタム、バリュー、ボラティリティ）と評価ユーティリティ（将来リターン計算、IC、統計サマリー、Zスコア正規化）。
- 監査ログ（信号→発注→約定のトレーサビリティ）用スキーマを提供。
- 自動的にプロジェクトルートの `.env` / `.env.local` を読み込む設定管理（無効化可能）。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（OS 環境変数を保護）
  - 必須環境変数の取得・バリデーション（Settings クラス）

- データ取得（J-Quants）
  - 株価日足（OHLCV）フェッチ + ページネーション対応
  - 財務データ（四半期 BS/PL）フェッチ
  - マーケットカレンダー（JPX）取得
  - レートリミット、リトライ、401 自動リフレッシュ、fetched_at 記録

- DuckDB スキーマ
  - raw_prices / raw_financials / raw_news / prices_daily / features / signals / orders / trades / positions / portfolio_performance など多数テーブルを定義
  - インデックス定義付き、初期化ユーティリティ（init_schema）

- ETL パイプライン
  - 差分取得（最終取得日からの差分 or 指定範囲）
  - backfill による直近再取得（API 後出し修正吸収）
  - 品質チェック（欠損 / スパイク / 重複 / 日付不整合）

- ニュース収集
  - RSS 取得、XML 安全パース、URL 正規化、トラッキング除去
  - 記事 ID を SHA-256 先頭で生成し冪等に保存
  - 銘柄コード抽出（テキスト内の 4 桁数字と known_codes の照合）

- 研究ユーティリティ
  - calc_momentum, calc_volatility, calc_value（prices_daily/raw_financials 参照）
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（クロスセクション正規化）

- 監査 & トレーサビリティ
  - signal_events, order_requests, executions テーブル
  - すべて UTC 保存、監査向け初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで `|` を利用しているため）。
- システムに DuckDB をインストールするパッケージ（Python 用 `duckdb`）。
- RSS XML パースに `defusedxml`。

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト配送形態に応じて）ローカル開発インストール:
     - pip install -e .

3. 環境変数の設定
   - プロジェクトルートに `.env` および任意で `.env.local` を配置できます。
   - 自動ロードの挙動:
     - OS 環境変数（既存） > .env.local > .env の順で適用されます。
     - テスト時などに自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須の環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - 任意/デフォルト:
     - KABUS_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）

4. データベース初期化（例: DuckDB）
   - Python REPL やスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - 監査ログ専用 DB を別に作る場合:
     - from kabusys.data.audit import init_audit_db
     - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡易例）

以下は主要なユースケースの最小実例です。

- DuckDB スキーマ初期化と日次 ETL 実行
```
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ（RSS をデフォルトソースで実行）
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
stats = run_news_collection(conn, known_codes=known_codes)
print(stats)
```

- J-Quants から株価を個別取得して保存
```
from kabusys.data import jquants_client as jq
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

- 研究（ファクター）計算の例
```
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
t = date(2024, 1, 31)
mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)

# Z スコア正規化
all_features = zscore_normalize(mom + vol + val, ["mom_1m", "ma200_dev", "atr_pct"])
```

- 設定アクセス（Settings）
```
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)
```

---

## 主要モジュール / API の簡単説明

- kabusys.config
  - Settings クラスを通じて環境変数を取得・検証します。
  - .env 自動ロード機能付き。

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar

- kabusys.data.schema
  - init_schema(db_path) : DuckDB スキーマ初期化

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...) : 日次 ETL（カレンダー・株価・財務・品質チェック）

- kabusys.data.news_collector
  - fetch_rss(url, source) / save_raw_news(conn, articles) / run_news_collection(...)

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

- kabusys.data.quality
  - run_all_checks(conn, ...) : 欠損・スパイク・重複・日付不整合チェック

- kabusys.data.audit
  - init_audit_schema(conn) / init_audit_db(path) : 監査ログテーブルの初期化

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 にすると .env 自動ロードを無効化)

注意: Settings のプロパティは未設定時に ValueError を出すものがあります（必須項目）。

---

## ディレクトリ構成

リポジトリの主要ファイル構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - etl.py
    - audit.py
    - quality.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各モジュールは責務ごとに分離されており、DuckDB 接続を受け渡して操作する設計です。

---

## 開発・運用上の注意

- DuckDB のファイルはデフォルトで `data/kabusys.duckdb` に作られます。データ保存先は環境変数 `DUCKDB_PATH` で変更可能です。
- ニュース収集は外部 HTTP を行うため、社内ネットワークやプロキシ環境では SSRF 対策などを考慮してください（既にリダイレクト時の検査やプライベート IP 検査を実装しています）。
- ETL は Fail-Fast ではなく、品質チェックは問題を収集して結果を返す設計です。呼び出し側での判断が必要です（停止するかログ警告で済ませるか等）。
- 本番発注や証券会社 API を利用する際は、十分なテストとリスク管理（paper_trading 環境の活用、KABUSYS_ENV の設定）を行ってください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索します。CI やテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使って明示的に制御できます。

---

## ライセンス / 貢献

（ここにはプロジェクトのライセンスや貢献方法等を記載してください。）

---

README は以上です。必要であれば、各モジュールの API サンプルやユニットテストの実行方法、CI/CD の設定例（ワークフロー）などの追加章を作成します。どの情報を優先して追加しますか？
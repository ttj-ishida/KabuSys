# KabuSys

日本株自動売買プラットフォーム用の軽量ライブラリ群です。データ収集（J-Quants）、DuckDB ベースのスキーマ定義・ETL、ニュース収集、ファクター計算（リサーチ）や監査ログ等を含みます。運用環境（実口座 / ペーパートレード / 開発）に合わせた設定管理も備えています。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution / Audit）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・サイズ制限・正規化）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）および統計ユーティリティ
- 監査ログ（シグナル → 発注 → 約定 のトレース）用スキーマ

設計上のポイント：
- DuckDB を中心に SQL と Python を併用して効率的に処理
- 外部依存は最小化（ただし DuckDB / defusedxml など必須ライブラリあり）
- ETL は冪等（ON CONFLICT）・差分更新・バックフィルを考慮
- セキュリティ（SSRF 防止、XML パース安全化など）に配慮

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レートリミット制御、リトライ、トークンリフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）

- data/schema.py
  - DuckDB 用スキーマ定義（RAW / PROCESSED / FEATURE / EXECUTION）
  - init_schema(db_path) でテーブル・インデックスを作成

- data/pipeline.py
  - 差分 ETL（run_daily_etl: calendar → prices → financials → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl

- data/news_collector.py
  - RSS フィード取得・前処理・正規化・DB 保存（raw_news, news_symbols）
  - SSRF 対策、XML の安全パース、受信サイズ制限

- data/quality.py
  - 欠損・重複・スパイク・日付不整合の検出（QualityIssue を返す）
  - run_all_checks でまとめて実行

- data/audit.py
  - シグナル・発注・約定の監査スキーマと初期化ユーティリティ
  - init_audit_schema / init_audit_db

- research/*.py
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats から再エクスポート）
  - DuckDB 上の prices_daily / raw_financials を参照して計算（本番発注は行わない）

- config.py
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクト経由の環境変数アクセス
  - 必須変数未設定時はエラーを投げる

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型ヒントや一部記法のため）
- DuckDB と defusedxml が必要

手順（例）:

1. リポジトリをクローン／配置して、仮想環境を作成：

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 必要パッケージをインストール（最低限）：

   ```bash
   pip install duckdb defusedxml
   ```

   ※ プロジェクトで配布される requirements.txt / pyproject.toml があればそちらを使用してください。

3. パッケージとしてインストール（開発モード）:

   プロジェクトルートに pyproject.toml あるいは setup.py がある想定で:

   ```bash
   pip install -e .
   ```

4. 環境変数（.env）を設定:

   プロジェクトルートに `.env` を置くと自動読み込みされます（*.env.local があれば優先して上書き）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）:

   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development / paper_trading / live)
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

   .env の例（最小）:

   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（基本例）

以下はライブラリを使った典型的なワークフロー例です。

1) DuckDB スキーマの初期化（1回だけ実行）

```python
from kabusys.config import settings
from kabusys.data import schema

# settings.duckdb_path は Path を返します
conn = schema.init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

2) 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）

```python
from datetime import date
from kabusys.data import pipeline
# conn は上で作成した接続
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブの実行

```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出に用いる既知のコード集合（optional）
# 例えば prices_daily から一意のコードを取得して set にするなど
# results は {source_name: saved_count}
results = run_news_collection(conn, sources=None, known_codes=None, timeout=30)
print(results)
```

4) 研究用ファクター計算（例：モメンタム）

```python
from datetime import date
from kabusys.research import calc_momentum

records = calc_momentum(conn, target_date=date(2024, 1, 31))
# records は [{"date": ..., "code": "7203", "mom_1m": ..., ...}, ...]
```

5) 将来リターンと IC 計算の組合せ

```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1,5,21])
factors = calc_momentum(conn, target_date=date(2024,1,31))
ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC (mom_1m -> fwd_1d):", ic)
```

6) 監査ログスキーマの初期化（監査専用 DB を使う場合）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点：
- research 関数群は DuckDB の prices_daily / raw_financials 等を参照します。init_schema→run_daily_etl によりテーブルが埋まることが前提です。
- jquants_client は内部で自動的に ID トークンを取得・リフレッシュします。API呼び出し時のレート制御やリトライは組み込まれています。

---

## 環境変数（まとめ）

必須：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルトを持つ）：
- KABUSYS_ENV (development|paper_trading|live) — default: development
- LOG_LEVEL — default: INFO
- KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — set to "1" to disable automatic .env loading

config.Settings 経由でアクセスできます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - features.py
  - calendar_management.py
  - stats.py
  - quality.py
  - audit.py
  - etl.py
- research/
  - __init__.py
  - feature_exploration.py
  - factor_research.py
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

注: 上記は本リポジトリに含まれる主要モジュールです。戦略や実行周りは拡張ポイントとなっています。

---

## 開発／拡張ポイント

- strategy パッケージに戦略ロジックを実装し、signals/ordering と連携させることで自動売買フローを繋げられます。
- execution パッケージでは実際の発注ロジック（kabuステーション等）を実装してください。現在 config には KABU_API_BASE_URL / KABU_API_PASSWORD を扱う準備があります。
- features テーブルや AI スコアの生成は research と連携して実装することを想定しています。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます。

---

## ライセンス・貢献

（ここにライセンスや貢献ルールを記載してください。現状 README には未記載のため、プロジェクトポリシーに従って追加してください。）

---

README は以上です。必要があれば、インストール用の requirements.txt サンプル、より詳細なコード例（ETL スケジューリング、Slack 通知、kabu ステーションとの接続例）やテストガイドを追記します。どのトピックを優先して追加しますか？
# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
データ収集（J-Quants）、DuckDB によるデータレイヤ設計、ETL パイプライン、ニュース収集、ファクター計算、監査ログ用スキーマなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の定量投資パイプラインおよび自動売買システムの基盤ライブラリです。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等の取得
- DuckDB を用いた Raw / Processed / Feature / Execution 層のスキーマ定義と初期化
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄紐付け
- 研究用のファクター計算（モメンタム、バリュー、ボラティリティ等）と評価ツール（IC 計算、統計サマリ）
- 発注監査ログ（監査テーブル群）の初期化ユーティリティ

設計上、本ライブラリは「本番の発注 API への直接アクセス」を最小限に抑え、データ取得や特徴量計算は安全に DuckDB / ローカル環境内で完結するよう配慮されています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準）
  - 必須環境変数のラッパー（`kabusys.config.settings`）

- データ取得と保存（J-Quants）
  - 安全な HTTP 呼び出し、トークン自動リフレッシュ、レートリミット、リトライロジック（指数バックオフ）
  - 日足・財務・マーケットカレンダーのフェッチ & DuckDB への冪等保存（ON CONFLICT）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化 (`kabusys.data.schema.init_schema`)

- ETL パイプライン
  - 差分更新（最終取得日ベース）・バックフィル・品質チェック統合 (`kabusys.data.pipeline.run_daily_etl`)
  - 個別ジョブ: 株価 / 財務 / カレンダー ETL（差分取得）

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などを検出 (`kabusys.data.quality`)

- ニュース収集
  - RSS フィード取得、XML の安全パース、サイズ制限、SSRF 対策
  - raw_news / news_symbols への保存（冪等） (`kabusys.data.news_collector`)

- 研究ユーティリティ
  - ファクター計算（モメンタム・バリュー・ボラティリティ） (`kabusys.research.factor_research`)
  - 将来リターン計算、IC（Spearman ρ）計算、統計サマリ (`kabusys.research.feature_exploration`)
  - Zスコア正規化ユーティリティ (`kabusys.data.stats.zscore_normalize`)

- 監査ログスキーマ
  - signal_events / order_requests / executions 等の監査テーブル初期化 (`kabusys.data.audit`)

---

## セットアップ手順（開発用）

1. Python 環境（推奨: 3.10+）を用意し、仮想環境を作る:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要なパッケージをインストール（最低限）:

   - duckdb
   - defusedxml

   例:

   ```bash
   pip install duckdb defusedxml
   ```

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを利用してください）

3. （開発時）パッケージを編集可能インストール:

   ```bash
   pip install -e .
   ```

4. 環境変数の設定:
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を作成すると自動読み込みを行います。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（.env に設定例）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token

# kabuステーション（発注を行う場合）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（オプション）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下は典型的なワークフロー例です。Python スクリプト内で実行します。

1. DuckDB スキーマの初期化（初回のみ）:

```python
from kabusys.data import schema

# ファイルパスまたは ":memory:"
conn = schema.init_schema("data/kabusys.duckdb")
# または
# conn = schema.init_schema(":memory:")
```

2. 日次 ETL の実行（J-Quants の認証トークンは settings から自動取得されます）:

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3. ニュース収集ジョブの実行:

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に用いる有効コードの集合（任意）
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

4. 研究用ファクター計算（例: モメンタム）:

```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

d = date(2024, 1, 31)
mom = calc_momentum(conn, d)        # prices_daily を参照
vol = calc_volatility(conn, d)
val = calc_value(conn, d)           # raw_financials と prices_daily を参照
```

5. 将来リターンの計算、および IC（Spearman）:

```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, date(2024, 1, 31), horizons=[1,5,21])
# factor_records は任意のファクター一覧（calc_momentum 等の戻り値）
ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

6. J-Quants の生データ取得（直接使う場合）:

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

# 明示的に id_token を渡すことも可能
token = get_id_token()
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
# 取得したレコードを保存するには save_daily_quotes を使う
from kabusys.data.jquants_client import save_daily_quotes
n = save_daily_quotes(conn, records)
```

---

## 主要 API / エントリポイント一覧

- 環境設定
  - kabusys.config.settings

- DB スキーマ
  - kabusys.data.schema.init_schema(db_path)
  - kabusys.data.schema.get_connection(db_path)

- ETL / パイプライン
  - kabusys.data.pipeline.run_daily_etl(...)
  - run_prices_etl / run_financials_etl / run_calendar_etl (個別)

- J-Quants クライアント
  - kabusys.data.jquants_client.get_id_token(...)
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar

- ニュース収集
  - kabusys.data.news_collector.fetch_rss(...)
  - run_news_collection(...)
  - save_raw_news / save_news_symbols

- 品質チェック
  - kabusys.data.quality.run_all_checks(...)

- 研究ユーティリティ
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.data.stats.zscore_normalize

- 監査ログ初期化
  - kabusys.data.audit.init_audit_schema(conn)
  - kabusys.data.audit.init_audit_db(db_path)

---

## 設定と挙動に関する補足

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に `.env` と `.env.local` を順にロードします。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB のデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb（settings.duckdb_path）
  - SQLITE_PATH: data/monitoring.db（settings.sqlite_path）

- 環境変数検証:
  - settings.env は "development" / "paper_trading" / "live" のいずれかを期待します。
  - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかを期待します。

- J-Quants クライアント:
  - 120 req/min のレート制限を内部で尊重します（固定間隔スロットリング）。
  - HTTP 408/429/5xx はリトライ、401 はトークン自動リフレッシュ（1 回）を試行します。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルとモジュールの構成（src/kabusys 配下）です。実際のプロジェクトではさらにドキュメントやスクリプト等が存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                          # 環境変数・設定
  - data/
    - __init__.py
    - jquants_client.py                 # J-Quants API クライアント
    - news_collector.py                 # RSS ニュース収集
    - schema.py                         # DuckDB スキーマ定義と初期化
    - stats.py                          # zscore_normalize 等
    - pipeline.py                       # ETL パイプライン
    - quality.py                        # データ品質チェック
    - calendar_management.py            # カレンダー管理ジョブ
    - audit.py                          # 監査ログスキーマ初期化
    - etl.py                            # ETL の公開型エイリアス
    - features.py                       # 特徴量ユーティリティ公開
  - research/
    - __init__.py
    - feature_exploration.py            # 将来リターン・IC・summary 等
    - factor_research.py                # モメンタム/バリュー/ボラティリティ
  - strategy/
    - __init__.py                       # 戦略層（実装置き場）
  - execution/
    - __init__.py                       # 発注・ブローカー連携（実装置き場）
  - monitoring/
    - __init__.py                       # 監視用（実装置き場）

---

## 開発者向け注意事項・設計意図

- DuckDB を中心としたローカル DB 設計により、データ再現性・監査性を確保しています。
- ETL / データ品質チェックは Fail-Fast を避け、全チェック結果を収集して上位で対応を判断する設計です。
- ニュース収集では SSRF や XML 弱点（XML bomb）対策を講じています（defusedxml の利用、レスポンス長制限、リダイレクト先検査等）。
- J-Quants クライアントは冪等性を重視し、保存処理は ON CONFLICT による更新を行います。

---

## 今後の拡張ポイント（例）

- strategy / execution 層の具体的なブローカー連携・注文実行ロジックの実装
- モデル学習パイプライン（AI スコア生成）
- モニタリングダッシュボード・アラート連携（Slack 通知等）
- テストカバレッジの拡充（ユニット・統合テスト）

---

## ライセンス・貢献

（ライセンス情報や貢献ルールがある場合はここに記載してください）

---

その他、README に含めたいサンプルや詳細手順があれば教えてください。README を用途（開発用、運用マニュアル、API ドキュメント）に合わせてさらに調整できます。
# KabuSys

日本株向け自動売買プラットフォームのモジュール群（ライブラリ）です。  
本リポジトリはデータ収集・ETL、特徴量生成、ファクター調査、ニュース収集、監査ログスキーマなど、量的運用に必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の層をサポートする Python モジュール群です。

- データ取得（J-Quants API）：株価日足、財務データ、マーケットカレンダー
- ETL パイプライン：差分取得、保存、品質チェック
- DuckDB ベースのスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit）
- ニュース収集（RSS）と記事→銘柄の紐付け
- 研究用ユーティリティ：ファクター計算（モメンタム / ボラティリティ / バリュー）、IC 計算、Z スコア正規化
- 監査ログ（signal → order → execution のトレーサビリティ）
- マーケットカレンダー管理（営業日判定、次/前営業日探索）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針として、本ライブラリは本番発注APIや外部ブローカーへ直接アクセスしないパーツ（データ取得・研究・ETL 等）と、監査・発注／実行を管理するスキーマ類を分離して提供します。外部依存を極力限定し、DuckDB と標準ライブラリベースでの実装を行っています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レートリミット、リトライ、トークンリフレッシュ対応）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - 保存用関数: save_daily_quotes / save_financial_statements / save_market_calendar
- data/schema.py
  - DuckDB スキーマの全DDL（raw / processed / feature / execution 層）を作成する init_schema()
- data/pipeline.py
  - 差分ETL（run_daily_etl）・個別ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果を表す ETLResult
- data/news_collector.py
  - RSS フィード取得、記事前処理、raw_news 保存、銘柄抽出・紐付け
  - SSRF 対策、サイズ制限、XML の安全パースなどを実装
- data/quality.py
  - 欠損・スパイク・重複・日付不整合チェック。run_all_checks で一括実行
- data/calendar_management.py
  - カレンダーの差分更新ジョブ（calendar_update_job）と営業日ユーティリティ（is_trading_day 等）
- research/
  - factor_research.py: calc_momentum, calc_volatility, calc_value
  - feature_exploration.py: calc_forward_returns, calc_ic, factor_summary, rank
- data/stats.py
  - zscore_normalize（クロスセクションでのZスコア正規化）
- audit.py
  - 監査ログ用DDL と init_audit_schema / init_audit_db

---

## 前提・依存

- Python 3.10 以上（型アノテーションで `|` を使用）
- 主要外部パッケージ（インストール必須）：
  - duckdb
  - defusedxml

pip での最低インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# パッケージとしてインストールする場合（setup.py/pyproject があれば）:
# pip install -e .
```

※プロジェクトによっては追加パッケージ（例: requests 等）を導入する可能性があります。必要に応じて pyproject.toml / requirements ファイルを参照してください。

---

## 環境変数（設定）

自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（ただしテスト等で無効化可能）。
必須となる環境変数（Settings クラス参照）:

- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN       — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      — Slack チャンネル ID（必須）

オプション:

- KABUSYS_ENV           — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL             — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
- KABU_API_BASE_URL     — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env 読み込みを無効化

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```

   ※プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを利用してください。

4. 環境変数（.env）を作成
   - 上記の必須環境変数を .env または .env.local に設定してください。

5. DuckDB スキーマ初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
   ```

6. 監査DBが必要な場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 基本的な使い方（例）

- 日次 ETL を実行する（J-Quants から差分取得して DuckDB に保存し、品質チェックを実行）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集を実行する:
  ```python
  from kabusys.data.news_collector import run_news_collection
  # conn は DuckDB 接続、known_codes は有効な銘柄コードの set
  stats = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(stats)  # {source_name: inserted_count}
  ```

- 研究（ファクター）計算例:
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 1, 5)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  # zscore_normalize の例
  mom_norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

- J-Quants API から任意期間の株価をフェッチ:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  ```

- 管理用ユーティリティ
  - calendar_update_job でカレンダーを先読みして更新
  - data.quality.run_all_checks で品質チェック（ETL 後の検査）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py  — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント
  - news_collector.py  — RSS ニュース収集
  - schema.py  — DuckDB スキーマ定義と init_schema
  - pipeline.py  — ETL パイプライン（run_daily_etl 等）
  - quality.py  — データ品質チェック
  - stats.py  — zscore_normalize など
  - features.py
  - calendar_management.py
  - audit.py  — 監査ログスキーマ初期化
  - etl.py
- research/
  - __init__.py
  - factor_research.py  — calc_momentum / calc_volatility / calc_value
  - feature_exploration.py  — calc_forward_returns / calc_ic / factor_summary
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

（上記は主要ファイルの抜粋です。詳しい実装は src/kabusys 以下の各ファイルを参照してください。）

---

## 開発・テスト時の注意

- 自動的に .env をロードしますが、テスト中にこれを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の接続はスレッドセーフではない点に注意してください。複数スレッドから同一接続を使う場合は適切に排他を行ってください。
- J-Quants API 呼び出しはレート制限（120 req/min）とリトライロジックを組み込んでいます。大量取得時は API の制約を尊重してください。
- news_collector は外部の RSS をダウンロードします。SSRF 対策や受信サイズ制限が組み込まれていますが、運用時は取得先の信頼性を確認してください。

---

## 参考・今後の拡張予定（例）

- strategy / execution 層の発注ロジック、ブローカーラッパーの実装
- Slack 通知やモニタリングの実装（monitoring パッケージ）
- AI スコア生成パイプラインの統合
- テストカバレッジ強化（ユニット/統合テスト）

---

必要であれば README にサンプル .env.example、より詳細な API 使用例、運用手順（cron / CI での ETL 実行例）、あるいは設計ドキュメント（DataPlatform.md / StrategyModel.md）への参照を追記します。どの情報を優先して追加しましょうか？
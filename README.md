# KabuSys

日本株のデータプラットフォーム／リサーチ／自動売買補助ライブラリです。  
DuckDB をデータストアに利用し、J-Quants API からのデータ取得・ETL、ニュースの収集と LLM を用いたニュースセンチメント分析、ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

## 概要

KabuSys は次の用途を想定した Python モジュール群です。

- J-Quants API から株価・財務・カレンダー等の差分取得（ETL）
- ニュースの収集（RSS）と LLM による銘柄単位のセンチメントスコアリング
- 市場レジーム判定（ETF の MA とマクロニュースの LLM スコアを組合せ）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と探索的解析
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース用テーブル）初期化ユーティリティ

設計上のポイント:
- Look-ahead bias を避けるため、内部で datetime.today()/date.today() を不用意に参照しない設計
- DuckDB を中心とした SQL ベースの処理（外部ライブラリ最小化）
- 冪等性（ON CONFLICT / DELETE→INSERT 等）を意識した保存ロジック
- ネットワーク/API 呼び出しはリトライ・バックオフ・レート制御を備える

---

## 機能一覧

主な機能（モジュール）：

- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）／環境変数ラッパー（settings）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline / etl: 日次 ETL パイプラインと個別 ETL ジョブ（prices / financials / calendar）
  - news_collector: RSS 取得・記事正規化・raw_news への保存処理（SSRF対策・サイズ制限）
  - calendar_management: 市場カレンダー／営業日判定ユーティリティ（next/prev/is_trading_day 等）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログ用スキーマ初期化・DB作成ユーティリティ（init_audit_schema / init_audit_db）
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを LLM（gpt-4o-mini, JSON mode）で評価し ai_scores に格納
  - regime_detector.score_regime: ETF(1321) の 200日MA乖離 + マクロニュースの LLM スコアを合成して market_regime に格納
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 必要条件（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

インストール例（仮）:
```bash
pip install duckdb openai defusedxml
# あるいはプロジェクトの requirements.txt がある場合:
# pip install -r requirements.txt
```

（プロジェクト配布形態に応じて pip install . や poetry を利用してください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. Python 環境（仮想環境）を準備
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定
   - 必須（アプリの実行・一部機能に必要）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）
     - KABU_API_PASSWORD : kabuステーション API のパスワード（発注関連）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : 通知用（必要なら）
   - 任意
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL
     - DUCKDB_PATH, SQLITE_PATH など

   推奨: プロジェクトルートに `.env` または `.env.local` を作成してください。`kabusys.config` は自動的にプロジェクトルート（.git または pyproject.toml）を探索して `.env` を読み込みます。テスト等で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   .env のサンプル:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-xxxxxx
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB 用ディレクトリを作成（必要なら）
   ```bash
   mkdir -p data
   ```

5. 監査ログ用 DB（任意）の初期化（Python 実行例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（代表的な例）

- 日次 ETL を実行（J-Quants からデータ取得・保存・品質チェック）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（ai_scores へ書込）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（market_regime に記録）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算・探索
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  t = date(2026, 3, 20)

  mom = calc_momentum(conn, t)
  val = calc_value(conn, t)
  vol = calc_volatility(conn, t)

  fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- 市場カレンダー操作
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026,3,20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 監査テーブルの初期化（既存 DB に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

---

## 環境変数・設定（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用、必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注用）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 用の監視 DB（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます。

kabusys.config.Settings を通じてこれらの値にアクセスできます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - stats.py
  - quality.py
  - audit.py
  - (その他サブモジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/、strategy/、execution/ などはパッケージ外部インターフェースとして __all__ に含められているが、実装は該当ファイルに依存します。

（README に列挙したものは主要モジュールです。詳細は各モジュール内の docstring を参照してください。）

---

## 注意点 / 運用上のヒント

- OpenAI 呼び出しは料金が発生します。バッチ/レートに注意して運用してください。
- ETL は Look-ahead バイアスを避けるために日付処理を厳格に行っています。バックテスト等で使用する際は ETL の取得時刻・fetched_at を考慮してください。
- news_collector は SSRF 対策・受信サイズ上限・XML パースの安全対策（defusedxml）を実装していますが、公開環境での運用時はさらに監視を強化してください。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョンがあります（回避コードあり）。運用中の DuckDB バージョンに依存する挙動に注意してください。

---

## さらに詳しく

各モジュールの関数や設計意図はソースコード内の docstring に詳細に記載しています。特に ETL・品質チェック・AI スコアリング周りは設計上の制約（ルックアヘッド回避、リトライ方針、フェイルセーフ動作）が明記されていますので、運用や拡張時は該当モジュールの docstring を参照してください。

---

質問や README の補足（例: 実行例の追加、依存関係ファイルの作成、CI向け設定など）を希望される場合は教えてください。必要に応じてサンプル .env.example や簡単なデプロイスクリプトも用意できます。